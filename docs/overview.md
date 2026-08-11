---
type: Architecture
title: openstack-neutron-operator-kog — overview
description: What the blueprint does and how it is built — the KOG generation model (oasgen-provider + rest-dynamic-controller), the per-resource OpenAPI subsets, the Neutron envelope/Kind naming convention, and the auth-bridge Keystone proxy.
resource: oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog
tags: [kog, openstack, neutron, oasgen-provider, rest-dynamic-controller, auth-bridge]
timestamp: 2026-08-11T00:00:00Z
---

# Overview

`openstack-neutron-operator-kog` is a **Krateo Operator Generator (KOG)** blueprint.
Instead of a hand-written controller, it ships a curated OpenAPI 3.0 subset for each
OpenStack Neutron resource and lets the Krateo KOG stack generate the CRDs and drive
reconciliation. The result: OpenStack **Neutron networking v2.0** is managed as native
Kubernetes custom resources.

## The generation model

Two Krateo components do the work; this blueprint only supplies inputs.

- **[`oasgen-provider`](https://github.com/krateo-platformops/oasgen-provider)** consumes
  a `RestDefinition` (one per Neutron resource, see [`chart/templates/rd-*.yaml`](../chart/templates)).
  Each `RestDefinition` points at an OpenAPI subset (mounted from a ConfigMap) and declares the
  resource Kind, its identifiers, the extra status fields, and the verb-to-HTTP mapping. From this,
  `oasgen-provider` generates the CRD and a `<Kind>Configuration` CRD (which carries auth).
- **[`rest-dynamic-controller`](https://github.com/krateo-platformops/rest-dynamic-controller)** is
  the generic controller that reconciles each generated CR by calling the Neutron REST API using the
  verb mapping from the `RestDefinition`.

```
chart (this blueprint)
  assets/<resource>.yaml   ── ConfigMap ──▶ RestDefinition ──▶ oasgen-provider ──▶ CRD + <Kind>Configuration CRD
                                                                                     │
                    NeutronNetwork CR  ─────────────────────────────────────────────┤
                                                                                     ▼
                                                          rest-dynamic-controller ──▶ auth-bridge ──▶ Neutron v2.0 API
```

## Per-resource OpenAPI subsets

Each file under [`chart/assets/`](../chart/assets) is a hand-crafted OpenAPI 3.0 subset of one
Neutron resource, KOG-friendly on purpose (only the fields the CR needs, envelope-shaped bodies).
The chart bundles each subset into a ConfigMap ([`chart/templates/configmap-*.yaml`](../chart/templates))
and references it from the matching `RestDefinition` via a `configmap://` `oasPath`.

The seven resources and their Neutron API paths:

| Resource | Neutron API | CR Kind |
|----------|-------------|---------|
| network | `/v2.0/networks` | `NeutronNetwork` |
| subnet | `/v2.0/subnets` | `NeutronSubnet` |
| router | `/v2.0/routers` | `NeutronRouter` |
| port | `/v2.0/ports` | `NeutronPort` |
| security group | `/v2.0/security-groups` | `NeutronSecurityGroup` |
| security-group rule | `/v2.0/security-group-rules` | `NeutronSecurityGroupRule` |
| floating IP | `/v2.0/floatingips` | `NeutronFloatingIP` |

## The envelope / `Neutron*` naming convention

Neutron wraps every payload in a single-key envelope: `{"network": {…}}`, `{"subnet": {…}}`, and
so on. The CR mirrors this — the spec is `spec.network.*`, `spec.subnet.*`, etc. — and the created
object's id and status land under `status.<envelope>.*` (for example `status.network.id`).

Because the envelope key (`network`) would collide with the CRD Kind in `crdgen`, every Kind is
prefixed `Neutron*` (`NeutronNetwork`, `NeutronSubnet`, …). This is the same reason Nova's `Server`
becomes `Instance` in the Nova KOG. All Kinds share the API group `network.openstack.krateo.io`.

## Verbs

Neutron updates are a `PUT` with a partial body (the Neutron convention), so the CRUD resources
carry a `create / get / update / delete` verb set. **Security-group rules are immutable** — there is
no update verb; change a rule by deleting and recreating the CR.

Cross-resource references are by OpenStack UUID, not by Kubernetes object name. For example
`NeutronSubnet.spec.subnet.network_id` and `NeutronPort.spec.port.network_id` take the UUID read from
the referenced CR's `status.<envelope>.id`. Sequence dependent resources by hand, or wire them with a
Krateo Composition.

## The auth-bridge (Keystone token exchange)

The generated controller speaks plain HTTP and cannot perform Keystone token exchange. This blueprint
ships a small **auth-bridge** — an openstacksdk reverse proxy
([`chart/scripts/openstack-auth-proxy.py`](../chart/scripts/openstack-auth-proxy.py), run inside the
`openstack-client` image). It:

1. authenticates using an admin `clouds.yaml` supplied in a Secret,
2. discovers the `network` service endpoint from the Keystone catalog (or uses a pinned
   `upstreamEndpoint`),
3. injects a **fresh** `X-Auth-Token` on every forwarded call.

The token never expires from the controller's point of view, and it works in-cluster (no public-DNS
resolver trap). The RestDefinitions point their OpenAPI `servers[0].url` at the in-cluster auth-bridge
Service, so all controller traffic flows through the proxy. The auth-bridge runs as a
`Deployment` + `Service` ([`chart/templates/auth-bridge-*.yaml`](../chart/templates)) and is enabled by
default.

## Two ways to install

- **Chart directly** (`helm upgrade --install`) — installs the operator layer straight from the chart.
- **Composition** — apply the [`compositiondefinition.yaml`](../compositiondefinition.yaml) so Krateo
  registers the chart, then create the generated Composition CR (see
  [`examples/neutron-operator/composition.yaml`](../examples/neutron-operator/composition.yaml)).

Either way, the blueprint installs the **operator** (auth-bridge + RestDefinitions + CRDs). It does not
create any Neutron object itself — you do that by applying `Neutron*` CRs afterward.
