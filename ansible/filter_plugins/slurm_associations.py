"""Small, testable helpers for the Slurm association Ansible role."""

from __future__ import annotations

from collections import Counter


def _association_key(association: dict) -> tuple[str, str, str]:
    return (
        association["account"],
        association["user"],
        association["partition"],
    )


def _normalize_fairshare(value: str | int) -> int | str:
    text = str(value).strip()
    return int(text) if text.isdigit() else text


def _tres_names(value: str) -> set[str]:
    return {
        assignment.split("=", maxsplit=1)[0]
        for assignment in value.split(",")
        if "=" in assignment
    }


def _tres_update(desired: str, current: str) -> str:
    """Set desired TRES values and explicitly clear undeclared old values."""

    desired_names = _tres_names(desired)
    stale_names = sorted(_tres_names(current) - desired_names)
    assignments = [assignment for assignment in desired.split(",") if assignment]
    assignments.extend(f"{name}=-1" for name in stale_names)
    return ",".join(assignments)


def slurm_partition_argument(partition: str) -> str:
    """Build an unambiguous sacctmgr partition selector."""

    return f"Partition={partition}" if partition else 'Partition=""'


def _parse_association_rows(rows: list[str], cluster_name: str) -> list[dict]:
    associations = []

    for row in rows:
        # sacctmgr preserves hierarchy indentation in Account even with
        # --parsable2, so normalize field edges before comparing names.
        columns = [column.strip() for column in row.split("|")]
        if len(columns) < 6 or columns[0] != cluster_name:
            continue

        associations.append(
            {
                "account": columns[1],
                "user": columns[2],
                "partition": columns[3],
                "fairshare": _normalize_fairshare(columns[4]),
                "group_tres": columns[5],
            }
        )

    return associations


def build_desired_state(
    users: list[dict], accounts: list[dict], partitions: list[dict]
) -> dict:
    """Build the complete declared account and partition-association state."""

    account_names = {account["name"] for account in accounts}
    member_counts = Counter(user["slurm_account"] for user in users)
    users_by_name = {user["name"]: user for user in users}
    associations = []
    authorization_matrix = {}

    desired_accounts = []
    for account in accounts:
        desired_accounts.append(
            {
                "name": account["name"],
                "description": account["description"],
                "organization": account.get("organization", account["name"]),
                "fairshare": member_counts[account["name"]],
                "group_tres": account.get("group_tres", ""),
            }
        )
        associations.append(
            {
                "account": account["name"],
                "user": "",
                "partition": "",
                "fairshare": member_counts[account["name"]],
                "group_tres": account.get("group_tres", ""),
            }
        )

    for partition in partitions:
        allowed_accounts = set(partition.get("allowed_accounts", []))
        allowed_users = set(partition.get("allowed_users", []))
        denied_users = set(partition.get("denied_users", []))
        authorized_users = sorted(
            user["name"]
            for user in users
            if (
                user["slurm_account"] in allowed_accounts
                or user["name"] in allowed_users
            )
            and user["name"] not in denied_users
        )
        authorization_matrix[partition["name"]] = authorized_users

        for user_name in authorized_users:
            user = users_by_name[user_name]
            associations.append(
                {
                    "account": user["slurm_account"],
                    "user": user_name,
                    "partition": partition["name"],
                    "fairshare": 1,
                    "group_tres": "",
                }
            )

    associations.sort(key=_association_key)

    return {
        "accounts": desired_accounts,
        "users": [
            {"name": user["name"], "default_account": user["slurm_account"]}
            for user in users
        ],
        "associations": associations,
        "authorization_matrix": authorization_matrix,
        "managed_accounts": sorted(account_names),
        "managed_users": sorted(users_by_name),
        "managed_partitions": sorted(authorization_matrix),
    }


def plan_association_changes(
    desired_state: dict, current_rows: list[str], cluster_name: str
) -> dict:
    """Compare declared partition Associations with SlurmDBD state."""

    desired = {
        _association_key(association): association
        for association in desired_state["associations"]
        if association["user"]
    }
    managed_users = set(desired_state["managed_users"])
    managed_partitions = set(desired_state["managed_partitions"])
    current = {}

    for association in _parse_association_rows(current_rows, cluster_name):
        # Slurm owns the root hierarchy; this role only manages lab identities.
        if association["account"] == "root" or association["user"] == "root":
            continue

        is_managed_user = association["user"] in managed_users
        is_managed_partition = association["partition"] in managed_partitions
        if is_managed_user or (association["user"] and is_managed_partition):
            current[_association_key(association)] = association

    additions = [desired[key] for key in sorted(desired.keys() - current.keys())]
    updates = []
    for key in sorted(desired.keys() & current.keys()):
        if (
            desired[key]["fairshare"] != current[key]["fairshare"]
            or desired[key]["group_tres"] != current[key]["group_tres"]
        ):
            update = desired[key].copy()
            update["group_tres_update"] = _tres_update(
                desired[key]["group_tres"], current[key]["group_tres"]
            )
            updates.append(update)
    keep = [
        desired[key]
        for key in sorted(desired.keys() & current.keys())
        if desired[key]["fairshare"] == current[key]["fairshare"]
        and desired[key]["group_tres"] == current[key]["group_tres"]
    ]

    # Account Associations are managed by plan_account_changes. This planner
    # owns only user Associations, including stale global user Associations.
    removals = [
        current[key]
        for key in sorted(current.keys() - desired.keys())
        if current[key]["user"]
    ]

    return {
        "add_associations": additions,
        "update_associations": updates,
        "remove_associations": removals,
        "keep_associations": keep,
    }


def plan_account_changes(
    desired_state: dict,
    current_account_rows: list[str],
    current_association_rows: list[str],
    cluster_name: str,
) -> dict:
    """Plan Account entities and their cluster-level Associations."""

    current_accounts = {}
    for row in current_account_rows:
        columns = [column.strip() for column in row.split("|")]
        if len(columns) >= 3:
            current_accounts[columns[0]] = {
                "description": columns[1],
                "organization": columns[2],
            }

    current_cluster_associations = {
        association["account"]: association
        for association in _parse_association_rows(
            current_association_rows,
            cluster_name,
        )
        if not association["user"] and not association["partition"]
    }

    add_accounts = []
    update_accounts = []
    add_cluster_associations = []
    update_cluster_associations = []

    for account in desired_state["accounts"]:
        account_name = account["name"]

        if account_name not in current_accounts:
            # Adding an Account with Cluster= also creates this Association.
            add_accounts.append(account)
            continue

        current_account = current_accounts[account_name]
        current_metadata = (
            current_account["description"].casefold(),
            current_account["organization"].casefold(),
        )
        desired_metadata = (
            account["description"].casefold(),
            account["organization"].casefold(),
        )
        if current_metadata != desired_metadata:
            update_accounts.append(account)

        desired_association = {
            "account": account_name,
            "fairshare": account["fairshare"],
            "group_tres": account["group_tres"],
        }
        current_association = current_cluster_associations.get(account_name)

        if current_association is None:
            add_cluster_associations.append(desired_association)
        elif (
            current_association["fairshare"] != account["fairshare"]
            or current_association["group_tres"] != account["group_tres"]
        ):
            update = desired_association.copy()
            update["group_tres_update"] = _tres_update(
                account["group_tres"],
                current_association["group_tres"],
            )
            update_cluster_associations.append(update)

    return {
        "add_accounts": add_accounts,
        "update_accounts": update_accounts,
        "add_cluster_associations": add_cluster_associations,
        "update_cluster_associations": update_cluster_associations,
    }


def plan_user_default_changes(desired_state: dict, current_rows: list[str]) -> list[dict]:
    """Return users missing from SlurmDBD or carrying a wrong default Account."""

    current = {}
    for row in current_rows:
        columns = row.split("|")
        if len(columns) >= 2:
            current[columns[0]] = columns[1]

    return [
        user
        for user in desired_state["users"]
        if current.get(user["name"]) != user["default_account"]
    ]


def find_jobs_blocking_removals(removals: list[dict], job_rows: list[str]) -> list[dict]:
    """Match running or pending jobs to associations scheduled for removal."""

    blockers = []
    for row in job_rows:
        columns = row.split("|")
        if len(columns) < 5:
            continue

        user, account, partition, job_id, state = columns[:5]
        for association in removals:
            user_matches = not association["user"] or association["user"] == user
            partition_matches = (
                not association["partition"]
                or association["partition"] == partition
            )
            if (
                user_matches
                and association["account"] == account
                and partition_matches
                and state in {"PENDING", "RUNNING"}
            ):
                blockers.append(
                    {
                        "job_id": job_id,
                        "state": state,
                        "user": user,
                        "account": account,
                        "partition": partition,
                    }
                )

    return blockers


class FilterModule:
    """Expose helpers as ordinary Ansible filters."""

    def filters(self) -> dict:
        return {
            "slurm_desired_state": build_desired_state,
            "slurm_association_plan": plan_association_changes,
            "slurm_account_plan": plan_account_changes,
            "slurm_user_default_plan": plan_user_default_changes,
            "slurm_blocking_jobs": find_jobs_blocking_removals,
            "slurm_partition_argument": slurm_partition_argument,
        }
