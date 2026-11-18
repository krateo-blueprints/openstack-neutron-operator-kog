---
type: Log
title: openstack-neutron-operator-kog — log
description: Curated chronological history of the OpenStack Neutron KOG blueprint — notable changes and decisions, not a generated changelog.
resource: oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog
tags: [kog, openstack, neutron, log, history]
timestamp: 2026-11-18T00:00:00Z
---

# Log

Curated history of notable changes and decisions. Newest first.

## Unreleased — create reachability rests on evidence, not on a declared 404

Same `hack/validate-findby-identifiers.py` as keystone-kog's. rest-dynamic-controller decides absence
from the wire status, so a 404 declared in the OAS is not evidence. Only `notFoundBody` and
`notFoundCodes` pass automatically; anything else needs a `kog.openstack.krateo.io/get-absent-evidence`
citation. A get that tolerates 404 is warned about. `hack/README.md` names each declaration's
consuming file:line. Neutron has no create-reach candidate, and the summary line says so.

## Unreleased — findby gate: reachability, its oasgen floor, the inert findby+create shape

`hack/validate-findby-identifiers.py` is the same script as keystone-kog's. It refuses a findby that a
spec-buildable get makes unreachable, and reports create reachability. It states the oasgen-provider
floor its verdicts assume (0.52.0, #421) and reads the repository's minimum from the README, now
stated as `oasgen-provider >= 0.52.0`. A findby + get + create kind whose get declares no absence gets
its own "inert" verdict. `NeutronRouterInterface` has no get, so its findby stays reachable.

## Unreleased — status-field gate models a mapping's source removal

`hack/validate-status-fields.py` now knows that a response fieldMapping removes its source unless
the source is itself a destination (rest-dynamic-controller `fieldmapping.NormalizeResponseBody`).
So a status field read from a moved source is reported as staying empty. It also reads only the
observe verb's mappings. This is the same model as glance-kog's copy, whose `main()` is now
identical. The current definitions pass either way.

## Unreleased — findby gate: per-verb policy, both mapping lists, declared action-only kinds

`hack/validate-findby-identifiers.py` gets the same update as keystone-kog's. It reads
`identifiersMatchPolicy` from the findby verb (OR by default) and requires identifiers to exist in the
generated CR spec as well, reading request mappings from both lists. A never-matching findby passes
only with a declared `kog.openstack.krateo.io/findby-action-only` reason. `NeutronRouterInterface`
still passes: `router_id` comes from `device_id` and is a path parameter.

## Unreleased — the Neutron Kinds are `v2-0`, not `v1alpha1`; findby gate

- oasgen-provider serves each Neutron Kind at the version it derives from the OAS `info.version`. That
  is `"2.0"`, which becomes `v2-0` (oasgen-provider `internal/tools/render/render.go` `TargetVersion`,
  using plumbing `crdgen.NormalizeVersionName`). The README, docs, `values.schema.json` and samples said
  `v1alpha1`, which is only the `<Kind>Configuration` version, so applying a sample failed with "no matches
  for kind". That included the `NeutronRouterInterface` sample added in 0.1.2. Measured on keystone-kog
  (`"3.0"` → `v3-0`) with oasgen-provider 0.80.0; the rule is the same.
- New CI gate `hack/validate-findby-identifiers.py`, the same check keystone-kog 0.4.2 introduced: every
  findby identifier must be a key of the declared list item. `NeutronRouterInterface` passes, matching
  `router_id` lifted from `device_id`.

## 0.1.2 — `NeutronRouterInterface`; three status fields that never fill in

- New Kind **`NeutronRouterInterface`**: attaches a subnet to a router
  (`PUT /v2.0/routers/{router_id}/add_router_interface`) and detaches it on delete
  (`remove_router_interface`). Until now no Kind could do this — `NeutronRouter`'s update can set the
  external gateway but not internal interfaces. Toggle: `restdefinitions.router_interface.enabled`.
- It is observed with a **findby** over `GET /v2.0/ports` that genuinely matches an existing
  attachment, because Neutron answers a second attach with a permanent 400. The subnet is matched by
  Neutron's `fixed_ips=subnet_id=` filter; the router client-side, after a transform that keeps only
  router-interface ports. Rationale in [api.md](api.md#neutronrouterinterface--a-subnet-attached-to-a-router).
  **Not yet exercised against a live Neutron.**
- Found while auditing status fields: `NeutronSubnet`, `NeutronSecurityGroup` and
  `NeutronSecurityGroupRule` declare `<envelope>.status`, which Neutron's objects do not have, so those
  columns were always empty. They stay (oasgen-provider makes `additionalStatusFields` append-only), now
  documented, and a new failing CI job (`status-fields`) rejects any further status field its observe
  response cannot carry.

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
