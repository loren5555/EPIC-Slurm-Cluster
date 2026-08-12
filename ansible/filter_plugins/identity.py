#!/usr/bin/env python3
"""Ansible filters for EPIC cluster identity validation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def access_group_members(
    cluster_users: Sequence[Mapping[str, Any]],
    group_name: str,
) -> list[str]:
    """Return manifest users assigned to one access group."""

    return [
        str(user["name"])
        for user in cluster_users
        if group_name in user.get("groups", [])
    ]


def ssh_authorized_users(
    cluster_users: Sequence[Mapping[str, Any]],
    host_name: str,
    controller_hosts: Sequence[str],
) -> list[str]:
    """Return users whose managed cluster key belongs on one host."""

    is_controller = host_name in controller_hosts
    return [
        str(user["name"])
        for user in cluster_users
        if is_controller or host_name in user.get("ssh_access", [])
    ]


def _group_members(fields: Sequence[Any], record: str) -> set[str]:
    members: set[str] = set()
    for entry in _entry_records(fields, record):
        try:
            member_field = str(entry[2])
        except IndexError as error:
            raise ValueError(f"invalid getent record for {record}: {fields!r}") from error
        members.update(member for member in member_field.split(",") if member)
    return members


def identity_change_plan(
    cluster_users: Sequence[Mapping[str, Any]],
    access_groups: Sequence[Mapping[str, Any]],
    passwd_entries: Mapping[str, Sequence[Any]],
    group_entries: Mapping[str, Sequence[Any]],
    home_checks: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Describe every identity change the convergence tasks will request."""

    changes: list[str] = []
    home_exists = {
        str(result["item"]["name"]): bool(result.get("stat", {}).get("exists"))
        for result in home_checks
    }

    for user in cluster_users:
        name = str(user["name"])
        if name not in group_entries:
            changes.append(f"CREATE PRIVATE GROUP {name} gid={int(user['gid'])}")

    for group in access_groups:
        name = str(group["name"])
        if name not in group_entries:
            changes.append(f"CREATE ACCESS GROUP {name} gid={int(group['gid'])}")

    for user in cluster_users:
        name = str(user["name"])
        expected_home = str(user["home"])
        expected_shell = str(user["shell"])

        if name not in passwd_entries:
            changes.append(
                f"CREATE USER {name} uid={int(user['uid'])} "
                f"gid={int(user['gid'])} home={expected_home} shell={expected_shell}"
            )
            continue

        fields = _entry_records(passwd_entries[name], f"passwd:{name}")[0]
        field_changes: list[str] = []
        actual_home = str(fields[4])
        actual_shell = str(fields[5])
        if actual_home != expected_home:
            field_changes.append(f"home={actual_home} -> {expected_home}")
        if actual_shell != expected_shell:
            field_changes.append(f"shell={actual_shell} -> {expected_shell}")
        if field_changes:
            changes.append(f"UPDATE USER {name} {'; '.join(field_changes)}")

        if name not in home_exists:
            raise ValueError(f"missing home-directory check for user {name}")
        if not home_exists[name]:
            changes.append(f"CREATE HOME {name} path={expected_home}")

    for group in access_groups:
        name = str(group["name"])
        desired = set(access_group_members(cluster_users, name))
        if name not in group_entries:
            if desired:
                changes.append(
                    f"SET ACCESS GROUP {name} members=[{','.join(sorted(desired))}]"
                )
            continue

        current = _group_members(group_entries[name], f"group:{name}")
        added = sorted(desired - current)
        removed = sorted(current - desired)
        if added or removed:
            changes.append(
                f"UPDATE ACCESS GROUP {name} "
                f"add=[{','.join(added)}] remove=[{','.join(removed)}]"
            )

    return changes


def format_identity_change_plan(hostname: str, changes: Sequence[str]) -> list[str]:
    """Format a change plan as callback-friendly separate list items."""

    return [
        f"Identity change plan for {hostname}:",
        *(changes if changes else ["No identity changes required."]),
    ]


def _entry_records(fields: Sequence[Any], record: str) -> list[Sequence[Any]]:
    """Normalize one getent record or duplicate same-name NSS records."""

    if not fields:
        raise ValueError(f"invalid getent record for {record}: {fields!r}")

    first_field = fields[0]
    if isinstance(first_field, Sequence) and not isinstance(first_field, (str, bytes)):
        records = list(fields)
    else:
        records = [fields]

    if any(
        not isinstance(entry, Sequence) or isinstance(entry, (str, bytes))
        for entry in records
    ):
        raise ValueError(f"invalid getent record for {record}: {fields!r}")

    return records


def _integer_field(fields: Sequence[Any], index: int, record: str) -> int:
    try:
        return int(fields[index])
    except (IndexError, TypeError, ValueError) as error:
        raise ValueError(f"invalid getent record for {record}: {fields!r}") from error


def identity_conflicts(
    cluster_users: Sequence[Mapping[str, Any]],
    access_groups: Sequence[Mapping[str, Any]],
    passwd_entries: Mapping[str, Sequence[Any]],
    group_entries: Mapping[str, Sequence[Any]],
) -> list[str]:
    """Return every incompatible existing user or group identity."""

    conflicts: list[str] = []
    users_by_uid: dict[int, set[str]] = {}
    for name, fields in passwd_entries.items():
        for entry in _entry_records(fields, f"passwd:{name}"):
            uid = _integer_field(entry, 1, f"passwd:{name}")
            users_by_uid.setdefault(uid, set()).add(name)

    groups_by_gid: dict[int, set[str]] = {}
    for name, fields in group_entries.items():
        for entry in _entry_records(fields, f"group:{name}"):
            gid = _integer_field(entry, 1, f"group:{name}")
            groups_by_gid.setdefault(gid, set()).add(name)

    for user in cluster_users:
        name = str(user["name"])
        expected_uid = int(user["uid"])
        expected_gid = int(user["gid"])

        if name in passwd_entries:
            actual_ids = {
                (
                    _integer_field(entry, 1, f"passwd:{name}"),
                    _integer_field(entry, 2, f"passwd:{name}"),
                )
                for entry in _entry_records(passwd_entries[name], f"passwd:{name}")
            }
            if actual_ids != {(expected_uid, expected_gid)}:
                actual = ", ".join(
                    f"{actual_uid}:{actual_gid}"
                    for actual_uid, actual_gid in sorted(actual_ids)
                )
                conflicts.append(
                    f"user {name} has UID:GID {actual}; "
                    f"expected {expected_uid}:{expected_gid}"
                )

        unexpected_uid_owners = users_by_uid.get(expected_uid, set()) - {name}
        for uid_owner in sorted(unexpected_uid_owners):
            conflicts.append(
                f"UID {expected_uid} is owned by user {uid_owner}; expected user {name}"
            )

    desired_groups = [
        {"name": user["name"], "gid": user["gid"]}
        for user in cluster_users
    ] + list(access_groups)

    for group in desired_groups:
        name = str(group["name"])
        expected_gid = int(group["gid"])

        if name in group_entries:
            actual_gids = {
                _integer_field(entry, 1, f"group:{name}")
                for entry in _entry_records(group_entries[name], f"group:{name}")
            }
            if actual_gids != {expected_gid}:
                actual = ", ".join(str(gid) for gid in sorted(actual_gids))
                conflicts.append(
                    f"group {name} has GID {actual}; expected GID {expected_gid}"
                )

        unexpected_gid_owners = groups_by_gid.get(expected_gid, set()) - {name}
        for gid_owner in sorted(unexpected_gid_owners):
            conflicts.append(
                f"GID {expected_gid} is owned by group {gid_owner}; expected group {name}"
            )

    return conflicts


class FilterModule:
    """Expose filters to Ansible/Jinja."""

    def filters(self) -> dict[str, Any]:
        return {
            "epic_access_group_members": access_group_members,
            "epic_format_identity_change_plan": format_identity_change_plan,
            "epic_identity_change_plan": identity_change_plan,
            "epic_identity_conflicts": identity_conflicts,
            "epic_ssh_authorized_users": ssh_authorized_users,
        }
