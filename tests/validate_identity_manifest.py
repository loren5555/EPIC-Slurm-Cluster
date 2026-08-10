#!/usr/bin/env python3
"""Validate the EPIC Ansible identity source of truth."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ALLOWED_SSH_TARGETS = {"controller", "a100", "rtx4070"}
EXPECTED_ANCHORS = {
    "liuhongbo": 10000,
    "huodongkun": 10004,
    "wanghao": 13007,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_manifest(path: Path) -> dict:
    require(path.is_file(), f"manifest does not exist: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "manifest root must be a mapping")
    return data


def validate_manifest(data: dict) -> None:
    users = data.get("epic_users")
    project_groups = data.get("epic_project_groups")
    require(isinstance(users, list) and users, "epic_users must be a non-empty list")
    require(
        isinstance(project_groups, list) and project_groups,
        "epic_project_groups must be a non-empty list",
    )

    users_by_name: dict[str, dict] = {}
    users_by_uid: dict[int, str] = {}
    for user in users:
        require(isinstance(user, dict), "each user must be a mapping")
        name = user.get("name")
        uid = user.get("uid")
        gid = user.get("gid")
        require(isinstance(name, str) and name, "each user needs a name")
        require(isinstance(uid, int), f"{name}: uid must be an integer")
        require(isinstance(gid, int), f"{name}: gid must be an integer")
        require(10000 <= uid < 20000, f"{name}: uid {uid} is outside the managed range")
        require(uid == gid, f"{name}: private UID and GID must match")
        require(name not in users_by_name, f"duplicate user name: {name}")
        require(uid not in users_by_uid, f"duplicate UID {uid}: {users_by_uid.get(uid)} and {name}")
        require(user.get("home") == f"/home/{name}", f"{name}: unexpected home")
        require(user.get("shell") in {"/bin/bash", "/bin/sh"}, f"{name}: unsupported shell")

        ssh_access = user.get("ssh_access")
        require(isinstance(ssh_access, list), f"{name}: ssh_access must be a list")
        require("controller" in ssh_access, f"{name}: controller SSH access is required")
        require(
            set(ssh_access) <= ALLOWED_SSH_TARGETS,
            f"{name}: unknown SSH target in {ssh_access}",
        )

        memberships = user.get("project_groups")
        require(isinstance(memberships, list), f"{name}: project_groups must be a list")
        users_by_name[name] = user
        users_by_uid[uid] = name

    groups_by_name: dict[str, dict] = {}
    groups_by_gid: dict[int, str] = {}
    for group in project_groups:
        require(isinstance(group, dict), "each project group must be a mapping")
        name = group.get("name")
        gid = group.get("gid")
        members = group.get("members")
        require(isinstance(name, str) and name, "each project group needs a name")
        require(isinstance(gid, int), f"{name}: gid must be an integer")
        require(20000 <= gid <= 20004, f"{name}: project GID is outside 20000-20004")
        require(isinstance(members, list), f"{name}: members must be a list")
        require(name not in groups_by_name, f"duplicate project group name: {name}")
        require(gid not in groups_by_gid, f"duplicate project GID: {gid}")
        require(len(members) == len(set(members)), f"{name}: duplicate member")
        for member in members:
            require(member in users_by_name, f"{name}: unknown member {member}")
        groups_by_name[name] = group
        groups_by_gid[gid] = name

    require(groups_by_gid.get(20003) == "3dv", "project GID 20003 must be 3dv")

    for username, user in users_by_name.items():
        declared = set(user["project_groups"])
        require(declared <= groups_by_name.keys(), f"{username}: unknown project group")
        actual = {
            group_name
            for group_name, group in groups_by_name.items()
            if username in group["members"]
        }
        require(declared == actual, f"{username}: project membership differs: {declared} != {actual}")

    for username, expected_uid in EXPECTED_ANCHORS.items():
        require(username in users_by_name, f"missing anchor user: {username}")
        require(users_by_name[username]["uid"] == expected_uid, f"{username}: wrong anchor UID")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} MANIFEST", file=sys.stderr)
        return 2
    try:
        validate_manifest(load_manifest(Path(sys.argv[1])))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"identity manifest invalid: {error}", file=sys.stderr)
        return 1
    print("identity manifest valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
