---
type: API
title: openstack-neutron-operator-kog — API
description: The CompositionDefinition CRD that registers this blueprint, the generated Composition CR, and the eight generated Neutron CRDs (Kinds, API group, envelope-shaped spec/status, and verb-to-HTTP mappings).
resource: oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog
tags: [kog, openstack, neutron, api, crd, compositiondefinition]
timestamp: 2026-11-18T00:00:00Z
---

# API

This component exposes two layers of API:

1. the **CompositionDefinition** that registers the chart as a Krateo Composition, and
2. the **generated Neutron CRDs** that `oasgen-provider` produces from the RestDefinitions.

## CompositionDefinition CRD

The registration lives in [`compositiondefinition.yaml`](../compositiondefinition.yaml):

```yaml
apiVersion: core.krateo.io/v1alpha1
kind: CompositionDefinition
metadata:
  name: openstack-neutron-operator-kog
  namespace: krateo-system
spec:
  chart:
    url: oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog
    version: "0.1.2"
```

In the repository `spec.chart.version` is the `CHART_VERSION` placeholder. The `release-tag` workflow
stamps it from the git tag and attaches the stamped file to the GitHub release; apply that one.

| Field | Type | Description |
|-------|------|-------------|
| `apiVersion` | string | `core.krateo.io/v1alpha1` — the Krateo CompositionDefinition CRD. |
| `kind` | string | `CompositionDefinition`. |
| `metadata.name` | string | Name of the definition; drives the generated Composition Kind. |
| `metadata.namespace` | string | Namespace the definition (and its Composition) live in. |
| `spec.chart.url` | string | OCI reference to the published chart artifact. |
| `spec.chart.version` | string | Chart version to install (matches `Chart.yaml` `version`). |

### The generated Composition CR

Applying the CompositionDefinition makes Krateo generate a Composition CRD via `crdgen`:

- **group** = `composition.krateo.io`
- **version** = chart version `0.1.2` → `v0-1-2`
- **Kind** = PascalCase of the definition name (hyphens removed):
  `openstack-neutron-operator-kog` → `OpenstackNeutronOperatorKog`

So the Composition CR is `composition.krateo.io/v0-1-2`, Kind `OpenstackNeutronOperatorKog`. Its
`spec` mirrors the chart values (see [configuration.md](configuration.md)); see
[`examples/neutron-operator/composition.yaml`](../examples/neutron-operator/composition.yaml) for a complete instance. Creating this CR
installs the operator layer (auth-bridge + RestDefinitions); it does not create any Neutron object.

## Generated Neutron CRDs

Each enabled `restdefinitions.<resource>` block ([configuration.md](configuration.md)) drives one
`RestDefinition` ([`chart/templates/rd-*.yaml`](../chart/templates)), from which `oasgen-provider`
generates a CRD plus a companion `<Kind>Configuration` CRD.

All Kinds share the API group **`network.openstack.krateo.io`**. The Neutron Kinds are served at version
**`v2-0`**: oasgen-provider derives it from each OAS document's `info.version` (`"2.0"`), lowercased with
every run of non-alphanumerics turned into `-` and a `v` prefixed. The `<Kind>Configuration` CRDs are always
`v1alpha1`. Until 0.1.2 these docs and the samples said `v1alpha1` for the Neutron Kinds, which the apiserver
rejects with "no matches for kind".

| Kind | Neutron API | Verbs | Envelope key |
|------|-------------|-------|--------------|
| `NeutronNetwork` | `/v2.0/networks` | create / get / update / delete | `network` |
| `NeutronSubnet` | `/v2.0/subnets` | create / get / update / delete | `subnet` |
| `NeutronRouter` | `/v2.0/routers` | create / get / update / delete | `router` |
| `NeutronRouterInterface` | `/v2.0/routers/{router_id}/add_router_interface` · `remove_router_interface` | create / findby / delete (immutable) | none — flat `spec.router_id` + `spec.subnet_id` |
| `NeutronPort` | `/v2.0/ports` | create / get / update / delete | `port` |
| `NeutronSecurityGroup` | `/v2.0/security-groups` | create / get / update / delete | `security_group` |
| `NeutronSecurityGroupRule` | `/v2.0/security-group-rules` | create / get / delete (immutable) | `security_group_rule` |
| `NeutronFloatingIP` | `/v2.0/floatingips` | create / get / update / delete | `floatingip` |

### Envelope-shaped spec and status

Neutron wraps payloads in a single-key envelope, and the CR mirrors that. For `NeutronNetwork`:

- `spec.network.*` — the desired Neutron `network` fields (e.g. `name`, `admin_state_up`, `shared`,
  `router:external`, `description`, `port_security_enabled`).
- `spec.configurationRef` — reference to the `<Kind>Configuration` CR carrying the bearer token.
- `status.network.id` — the created object's UUID (used for cross-resource references).
- `status.network.status` — the Neutron object status.

The `RestDefinition` declares the identifiers and the extra status fields exposed. For `NeutronNetwork`
([`chart/templates/rd-network.yaml`](../chart/templates/rd-network.yaml)):

```yaml
resource:
  kind: NeutronNetwork
  identifiers:
    - network.id
    - network.name
  additionalStatusFields:
    - network.id
    - network.status
  verbsDescription:
    - action: create
      method: POST
      path: /v2.0/networks
    - action: get
      method: GET
      path: /v2.0/networks/{id}
      requestFieldMapping:
        - inPath: id
          inCustomResource: status.network.id
    - action: update
      method: PUT
      path: /v2.0/networks/{id}
      requestFieldMapping:
        - inPath: id
          inCustomResource: status.network.id
    - action: delete
      method: DELETE
      path: /v2.0/networks/{id}
      requestFieldMapping:
        - inPath: id
          inCustomResource: status.network.id
```

`{id}` in the get/update/delete paths is resolved from `status.<envelope>.id`, so those verbs act on the
object created by the `POST`. Updates are `PUT` with a partial body (the Neutron convention).

### `NeutronRouterInterface` — a subnet attached to a router

Neutron has no router-interface resource with its own id. Attaching a subnet is a router **action**,
and so is detaching it:

| Verb | HTTP | Body |
|------|------|------|
| create | `PUT /v2.0/routers/{router_id}/add_router_interface` | `{"subnet_id": "<id>"}` |
| findby | `GET /v2.0/ports?device_id=<router_id>&fixed_ips=subnet_id%3D<subnet_id>` | — |
| delete | `PUT /v2.0/routers/{router_id}/remove_router_interface` | `{"subnet_id": "<id>"}` |

These payloads are **not** envelope-wrapped, so the CR is flat:

```yaml
apiVersion: network.openstack.krateo.io/v2-0
kind: NeutronRouterInterface
metadata:
  name: demo-router-demo-subnet
  namespace: krateo-system
spec:
  configurationRef:
    name: neutron-config-router-interface
    namespace: krateo-system
  router_id: "<a NeutronRouter's status.router.id>"
  subnet_id: "<a NeutronSubnet's status.subnet.id>"
```

**Why a findby, and why it has to match.** A second `add_router_interface` for the same subnet is a
permanent `400 Router already has a port on subnet <id>` (`neutron/db/l3_db.py`,
`_check_for_dup_router_subnets`). So the controller must recognise an attachment that already exists,
or every reconcile after the first would re-fire the create and fail forever. What an attach leaves
behind is a **port**: `device_id` is the router, one of its `fixed_ips` is on the subnet, and
`device_owner` is one of `network:router_interface`, `network:router_interface_distributed` (DVR) or
`network:ha_router_replicated_interface` (HA). The findby lists exactly those ports:

- **subnet** — matched by Neutron's own `fixed_ips=subnet_id=<id>` list filter. It cannot be matched
  client-side: rest-dynamic-controller's identifier matcher walks maps only, so no identifier can reach
  into the `fixed_ips` array, and an IPv6 interface port can carry several subnets at once.
- **router** — matched client-side. A `responseTransform` keeps `device_id` only on a router-interface
  port (the gateway, DVR centralized-SNAT and HA-network ports share the router's `device_id`), a
  response `fieldMapping` lifts it to `router_id`, and `identifiersMatchPolicy: AND` requires it to equal
  `spec.router_id`.

Both steps run before the comparison: findby normalizes each listed port and only then matches it.

This uses RestDefinition features (`itemsPath`, a findby `responseTransform`, response-direction
`fieldMapping`, `identifiersMatchPolicy`) present in oasgen-provider 0.52.0 and 0.54.1, the versions
this KOG fleet pins. oasgen-provider may log generation warnings for this Kind — `router_id` absent
from the raw findby item, and create/findby response shapes that differ — both expected: the matcher
sees the item after normalization, and an attach response is not a port.

Status after an attach:

| Field | From |
|-------|------|
| `status.router_id` | the port's `device_id` |
| `status.port_id` | the port's `id` (the router's port on the subnet) |
| `status.network_id` | the port's `network_id` |
| `status.device_owner` | which router-interface flavour (plain, DVR, HA) |
| `status.fixed_ips` | the router's address(es) on the network — the subnet's `gateway_ip` |
| `status.port_status` | the port's `status`, e.g. `ACTIVE` / `DOWN` |

Detaching with `remove_router_interface` answers `404` when the router, the subnet or the attachment
is already gone; the controller treats a `404` on delete as success. A `409` (a floating IP or an
extra route still uses the subnet) is retried until the blocker is removed.

### `<Kind>Configuration` CRDs

For every generated Kind, `oasgen-provider` also generates a `<Kind>Configuration` CRD (e.g.
`NeutronNetworkConfiguration`) carrying the authentication reference:

```yaml
apiVersion: network.openstack.krateo.io/v1alpha1
kind: NeutronNetworkConfiguration
metadata:
  name: neutron-config
  namespace: krateo-system
spec:
  authentication:
    bearer:
      tokenRef:
        name: neutron-token
        namespace: krateo-system
        key: token
```

The bearer token is a placeholder — the auth-bridge injects the real `X-Auth-Token`. Create one
Configuration per Kind you use and reference it from the CR's `spec.configurationRef`.

### Immutability

`NeutronSecurityGroupRule` has **no update verb** — its `RestDefinition`
([`chart/templates/rd-security-group-rule.yaml`](../chart/templates/rd-security-group-rule.yaml))
declares only create / get / delete. To change a rule, delete and recreate the CR.

`NeutronRouterInterface` has no update verb either: `spec.router_id` and `spec.subnet_id` are the
identity of the attachment. Editing either on a live CR attaches the new pair and leaves the old one
attached, so delete the CR (which detaches) and create a new one.

### Status fields that never fill in

`NeutronSubnet`, `NeutronSecurityGroup` and `NeutronSecurityGroupRule` list `<envelope>.status` in
`additionalStatusFields`, but Neutron's subnet, security-group and security-group-rule objects have no
`status` attribute (`neutron/db/db_base_plugin_common.py` `_make_subnet_dict`,
`neutron/db/securitygroups_db.py` `_make_security_group_dict` / `_make_security_group_rule_dict`; the
api-ref lists none). rest-dynamic-controller skips an absent field without a log, so those columns are
always empty — it does not mean Neutron has not filled them in yet.

They are not removed because oasgen-provider's RestDefinition CRD makes `additionalStatusFields`
**append-only** (a CEL transition rule): dropping an entry that already shipped would make `helm upgrade`
fail on every existing install. The `status-fields` CI job
([`hack/validate-status-fields.py`](../hack/validate-status-fields.py)) now fails any RestDefinition
whose status field is not in its observe response schema, and allowlists exactly these three.

### Cross-resource references

Dependent fields take an OpenStack UUID, read from the referenced CR's `status.<envelope>.id`:

| Field | Value |
|-------|-------|
| `NeutronSubnet.spec.subnet.network_id` | a `NeutronNetwork`'s `status.network.id` |
| `NeutronPort.spec.port.network_id` | a `NeutronNetwork`'s `status.network.id` |
| `NeutronSecurityGroupRule.spec.security_group_rule.security_group_id` | a `NeutronSecurityGroup`'s `status.security_group.id` |
| `NeutronRouterInterface.spec.router_id` | a `NeutronRouter`'s `status.router.id` |
| `NeutronRouterInterface.spec.subnet_id` | a `NeutronSubnet`'s `status.subnet.id` |

See [usage.md](usage.md) for how to read and wire these.
