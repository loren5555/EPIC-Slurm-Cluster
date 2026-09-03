# Open OnDemand Campus IP Access Design

## Goal

Allow users to open the existing Open OnDemand portal through the fixed campus
IP address `222.20.99.125` while preserving
`epic-cluster-controller-01` as the canonical portal hostname.

## Configuration

Declare the accepted campus IP addresses once in
`ansible/inventory/group_vars/all/ood.yml` as
`ood_server_ip_addresses`. Keep `ood_server_address` unchanged so existing
hostname-based links and clients continue to use the stable hostname.

The controller role consumes the IP list in two places:

- `ood_portal.yml.j2` renders every address as an Open OnDemand
  `server_aliases` entry, allowing Apache to accept the address without
  redirecting it to the canonical hostname.
- `openssl.cnf.j2` renders every address as an `IP.N` subject alternative name,
  allowing the generated HTTPS certificate to identify the IP address.

The existing `host_regex` remains unchanged because it restricts reverse-proxy
targets for interactive applications, not the address used to reach the portal.

## Deployment Behavior

Changing the OpenSSL request configuration regenerates the self-signed portal
certificate. The existing controller handler then regenerates the Open OnDemand
Apache configuration and restarts Apache. Clients that explicitly trusted the
old self-signed certificate must trust the replacement certificate.

Hostname-based Grafana and Prometheus links remain unchanged and may still
require hostname resolution when the portal itself was opened by IP. This is an
accepted limitation and is outside this change.

## Verification

Contract tests verify that:

- the inventory declares `222.20.99.125` in `ood_server_ip_addresses`;
- the portal template renders the declared addresses as `server_aliases`;
- the certificate template renders the declared addresses as IP SAN entries;
- the canonical hostname and interactive-application proxy restrictions remain
  unchanged.

After deployment, Apache should accept
`https://222.20.99.125:8443/`, and the served certificate should contain
`IP Address:222.20.99.125` in its subject alternative names.
