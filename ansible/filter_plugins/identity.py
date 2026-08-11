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
            "epic_identity_conflicts": identity_conflicts,
        }
