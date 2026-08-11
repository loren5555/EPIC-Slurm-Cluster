#!/usr/bin/env python3
"""Validate the EPIC Ansible identity source of truth."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


EXPECTED_ANCHORS = {
    "liuhongbo": 10000,
    "huodongkun": 10004,
    "wanghao": 13007,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def valid_group_name(name: str) -> bool:
    """Return whether a group follows the cluster's portable naming rule."""

    return bool(
        len(name) <= 32
        and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", name)
    )


def load_manifest(path: Path) -> dict:
    require(path.is_file(), f"manifest does not exist: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "manifest root must be a mapping")
    return data


def compute_hostnames(inventory: dict) -> set[str]:
    children = inventory.get("all", {}).get("children", {})
    hostnames: set[str] = set()
    for group_name in ("controlled_compute_nodes", "free_compute_nodes"):
        hosts = children.get(group_name, {}).get("hosts", {})
        require(isinstance(hosts, dict), f"inventory group {group_name} must define hosts")
        hostnames.update(hosts)
    require(hostnames, "inventory must contain at least one compute host")
    return hostnames


def validate_manifest(data: dict, allowed_ssh_hosts: set[str]) -> None:
    users = data.get("cluster_users")
    access_groups = data.get("access_groups")
    require(isinstance(users, list) and users, "cluster_users must be a non-empty list")
    require(
        isinstance(access_groups, list) and access_groups,
        "access_groups must be a non-empty list",
    )

    users_by_name: dict[str, dict] = {}
    users_by_uid: dict[int, str] = {}
    for user in users:
        require(isinstance(user, dict), "each user must be a mapping")
        name = user.get("name")
        uid = user.get("uid")
        gid = user.get("gid")
        require(isinstance(name, str) and name, "each user needs a name")
        require(
            valid_group_name(name),
            f"{name}: user names, and therefore private group names, must "
            "follow the portable group naming rule",
        )
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
        require(
            set(ssh_access) <= allowed_ssh_hosts,
            f"{name}: unknown compute hostname in ssh_access: {ssh_access}",
        )

        memberships = user.get("groups")
        require(isinstance(memberships, list), f"{name}: groups must be a list")
        users_by_name[name] = user
        users_by_uid[uid] = name

    groups_by_name: dict[str, dict] = {}
    groups_by_gid: dict[int, str] = {}
    for group in access_groups:
        require(isinstance(group, dict), "each access group must be a mapping")
        name = group.get("name")
        gid = group.get("gid")
        require(isinstance(name, str) and name, "each access group needs a name")
        require(
            valid_group_name(name),
            f"{name}: group names must start with a letter or underscore and "
            "contain only letters, digits, underscores, or hyphens",
        )
        require(isinstance(gid, int), f"{name}: gid must be an integer")
        require(20000 <= gid <= 20004, f"{name}: access GID is outside 20000-20004")
        require("members" not in group, f"{name}: members must be derived from cluster_users")
        require(name not in groups_by_name, f"duplicate access group name: {name}")
        require(gid not in groups_by_gid, f"duplicate access GID: {gid}")
        groups_by_name[name] = group
        groups_by_gid[gid] = name

    require(groups_by_gid.get(20003) == "CV3D", "access GID 20003 must be CV3D")

    for username, user in users_by_name.items():
        declared = set(user["groups"])
        require(declared <= groups_by_name.keys(), f"{username}: unknown access group")

    for username, expected_uid in EXPECTED_ANCHORS.items():
        require(username in users_by_name, f"missing anchor user: {username}")
        require(users_by_name[username]["uid"] == expected_uid, f"{username}: wrong anchor UID")


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {Path(sys.argv[0]).name} MANIFEST INVENTORY", file=sys.stderr)
        return 2
    try:
        manifest = load_manifest(Path(sys.argv[1]))
        inventory = load_manifest(Path(sys.argv[2]))
        validate_manifest(manifest, compute_hostnames(inventory))
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"identity manifest invalid: {error}", file=sys.stderr)
        return 1
    print("identity manifest valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
