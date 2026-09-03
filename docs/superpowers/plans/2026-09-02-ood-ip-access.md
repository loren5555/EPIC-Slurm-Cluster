# Open OnDemand Campus IP Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the Open OnDemand portal to accept HTTPS requests addressed to the fixed campus IP `222.20.99.125` while retaining its canonical hostname.

**Architecture:** Declare portal IP aliases once in the shared OOD group variables. Render that list into both the OOD portal's Apache aliases and the self-signed certificate's IP subject alternative names, leaving reverse-proxy target restrictions unchanged.

**Tech Stack:** Ansible variables, Jinja2 templates, Open OnDemand 4.2 portal generator, OpenSSL, Python `unittest`

---

### Task 1: Add the IP-access contract test

**Files:**
- Create: `tests/test_ood_ip_access.py`
- Test: `tests/test_ood_ip_access.py`

- [ ] **Step 1: Write the failing contract test**

```python
#!/usr/bin/env python3
"""Contract tests for Open OnDemand portal IP access."""

from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class OodIpAccessTests(unittest.TestCase):
    def test_campus_ip_is_declared_once_and_consumed_by_portal_and_tls(self) -> None:
        inventory = (
            REPOSITORY_ROOT / "ansible/inventory/group_vars/all/ood.yml"
        ).read_text(encoding="utf-8")
        portal = (
            REPOSITORY_ROOT
            / "ansible/roles/ood_controller/templates/ood_portal.yml.j2"
        ).read_text(encoding="utf-8")
        openssl = (
            REPOSITORY_ROOT
            / "ansible/roles/ood_controller/templates/openssl.cnf.j2"
        ).read_text(encoding="utf-8")

        self.assertIn("ood_server_address: epic-cluster-controller-01", inventory)
        self.assertIn("ood_server_ip_addresses:", inventory)
        self.assertIn('  - "222.20.99.125"', inventory)
        self.assertIn("server_aliases:", portal)
        self.assertIn("for address in ood_server_ip_addresses", portal)
        self.assertIn("for address in ood_server_ip_addresses", openssl)
        self.assertIn("IP.{{ loop.index }} = {{ address }}", openssl)
        self.assertIn(
            'host_regex: "epic-cluster-(controller|compute)-[a-z0-9-]+"',
            portal,
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python -m unittest tests.test_ood_ip_access -v`

Expected: FAIL because `ood_server_ip_addresses` and `server_aliases` do not yet exist.

### Task 2: Render the campus IP in the portal and certificate

**Files:**
- Modify: `ansible/inventory/group_vars/all/ood.yml`
- Modify: `ansible/roles/ood_controller/templates/ood_portal.yml.j2`
- Modify: `ansible/roles/ood_controller/templates/openssl.cnf.j2`
- Test: `tests/test_ood_ip_access.py`

- [ ] **Step 1: Declare the campus IP beside the canonical hostname**

```yaml
ood_server_address: epic-cluster-controller-01
ood_server_ip_addresses:
  - "222.20.99.125"
ood_https_port: 8443
```

- [ ] **Step 2: Render Apache server aliases**

```yaml
servername: "{{ ood_server_address }}"
server_aliases:
{% for address in ood_server_ip_addresses %}
  - "{{ address }}"
{% endfor %}
listen_addr_port: "{{ ood_https_port }}"
```

- [ ] **Step 3: Render IP subject alternative names**

```ini
[alternative_names]
DNS.1 = {{ ood_server_address }}
{% for address in ood_server_ip_addresses %}
IP.{{ loop.index }} = {{ address }}
{% endfor %}
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `python -m unittest tests.test_ood_ip_access -v`

Expected: PASS.

- [ ] **Step 5: Run the complete test suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests PASS.

### Task 3: Review and create the single requested commit

**Files:**
- Add all files directly related to OOD campus IP access, including the already updated quick-start address and historical OOD plan address.
- Exclude unrelated working-tree changes, if any.

- [ ] **Step 1: Inspect the final diff**

Run: `git diff --check`

Expected: no whitespace errors.

Run: `git diff -- ansible/inventory/group_vars/all/ood.yml ansible/roles/ood_controller/templates/ood_portal.yml.j2 ansible/roles/ood_controller/templates/openssl.cnf.j2 tests/test_ood_ip_access.py docs/superpowers/specs/2026-09-02-ood-ip-access-design.md docs/superpowers/plans/2026-09-02-ood-ip-access.md docs/user/01-quick-start.md docs/superpowers/plans/2026-08-18-open-ondemand.md`

Expected: only the confirmed IP-access design, implementation, tests, and documentation changes.

- [ ] **Step 2: Commit all related changes once**

```bash
git add -- ansible/inventory/group_vars/all/ood.yml ansible/roles/ood_controller/templates/ood_portal.yml.j2 ansible/roles/ood_controller/templates/openssl.cnf.j2 tests/test_ood_ip_access.py docs/superpowers/specs/2026-09-02-ood-ip-access-design.md docs/superpowers/plans/2026-09-02-ood-ip-access.md docs/user/01-quick-start.md docs/superpowers/plans/2026-08-18-open-ondemand.md
git commit -m "feat(ood): allow campus IP access"
```
