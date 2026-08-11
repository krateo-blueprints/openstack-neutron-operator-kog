---
type: Log
title: openstack-neutron-operator-kog — log
description: Curated chronological history of the OpenStack Neutron KOG blueprint — notable changes and decisions, not a generated changelog.
resource: oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog
tags: [kog, openstack, neutron, log, history]
timestamp: 2026-08-11T00:00:00Z
---

# Log

Curated history of notable changes and decisions. Newest first.

## 2026-08-11 — Adopt the OKF documentation standard

- Added the full OKF core doc set under [`docs/`](.): `index`, `overview`, `usage`, `configuration`,
  `api`, `examples`, `release`, `log`, plus [`llms.txt`](llms.txt).
- Gave the pre-existing [`quickstart.md`](quickstart.md) OKF frontmatter (`type: Runbook`).
- Moved the runnable example under a named directory, [`examples/neutron-operator/`](../examples/neutron-operator),
  with its own `README.md` (`type: Example`) and both manifests (operator Composition + sample CRs).
- Rewrote [`README.md`](../README.md) into the six standard sections.
- Wired the `lint-docs` CI job ([`.github/workflows/lint.yaml`](../.github/workflows/lint.yaml)).

## 0.1.0 — Initial release

- Krateo Operator Generator (KOG) packaging for **OpenStack Neutron networking v2.0**: networks,
  subnets, routers, ports, security groups, security-group rules and floating IPs as native
  Kubernetes CRs.
- One curated OpenAPI 3.0 subset per resource ([`chart/assets/`](../chart/assets)), bundled into a
  ConfigMap and referenced from a per-resource `RestDefinition` ([`chart/templates/rd-*.yaml`](../chart/templates)),
  reconciled by `oasgen-provider` + `rest-dynamic-controller`.
- Kinds prefixed `Neutron*` to avoid the crdgen Kind-vs-envelope-property collision; all under the
  `network.openstack.krateo.io` API group.
- Security-group rules modelled as immutable (create / get / delete only); CRUD resources carry an
  `update` verb (`PUT` with a partial body, the Neutron convention).
- Shipped the **auth-bridge**: a stateless openstacksdk Keystone-auth reverse proxy
  ([`chart/scripts/openstack-auth-proxy.py`](../chart/scripts/openstack-auth-proxy.py)) that discovers
  the `network` endpoint and injects a fresh `X-Auth-Token`, so the plain-HTTP controller works
  in-cluster without a public-DNS resolver trap.
- Per-resource `restdefinitions.<resource>.enabled` toggles and the `authBridge` config surface, typed
  by [`chart/values.schema.json`](../chart/values.schema.json).
