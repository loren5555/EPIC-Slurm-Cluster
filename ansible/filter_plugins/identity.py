#!/usr/bin/env python3
"""Ansible filters for EPIC cluster identity validation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


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
    users_by_uid = {
        _integer_field(fields, 1, f"passwd:{name}"): name
        for name, fields in passwd_entries.items()
    }
    groups_by_gid = {
        _integer_field(fields, 1, f"group:{name}"): name
        for name, fields in group_entries.items()
    }

    for user in cluster_users:
        name = str(user["name"])
        expected_uid = int(user["uid"])
        expected_gid = int(user["gid"])

        if name in passwd_entries:
            fields = passwd_entries[name]
            actual_uid = _integer_field(fields, 1, f"passwd:{name}")
            actual_gid = _integer_field(fields, 2, f"passwd:{name}")
            if (actual_uid, actual_gid) != (expected_uid, expected_gid):
                conflicts.append(
                    f"user {name} has UID:GID {actual_uid}:{actual_gid}; "
                    f"expected {expected_uid}:{expected_gid}"
                )

        uid_owner = users_by_uid.get(expected_uid)
        if uid_owner is not None and uid_owner != name:
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
            actual_gid = _integer_field(group_entries[name], 1, f"group:{name}")
            if actual_gid != expected_gid:
                conflicts.append(
                    f"group {name} has GID {actual_gid}; expected GID {expected_gid}"
                )

        gid_owner = groups_by_gid.get(expected_gid)
        if gid_owner is not None and gid_owner != name:
            conflicts.append(
                f"GID {expected_gid} is owned by group {gid_owner}; expected group {name}"
            )

    return conflicts


class FilterModule:
    """Expose filters to Ansible/Jinja."""

    def filters(self) -> dict[str, Any]:
        return {"epic_identity_conflicts": identity_conflicts}
