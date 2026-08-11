---
type: API
title: openstack-neutron-operator-kog — API
description: The CompositionDefinition CRD that registers this blueprint, the generated Composition CR, and the seven generated Neutron CRDs (Kinds, API group, envelope-shaped spec/status, and verb-to-HTTP mappings).
resource: oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog
tags: [kog, openstack, neutron, api, crd, compositiondefinition]
timestamp: 2026-08-11T00:00:00Z
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
    version: "0.1.0"
```

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
- **version** = chart version `0.1.0` → `v0-1-0`
- **Kind** = PascalCase of the definition name (hyphens removed):
  `openstack-neutron-operator-kog` → `OpenstackNeutronOperatorKog`

So the Composition CR is `composition.krateo.io/v0-1-0`, Kind `OpenstackNeutronOperatorKog`. Its
`spec` mirrors the chart values (see [configuration.md](configuration.md)); see
[`examples/neutron-operator/composition.yaml`](../examples/neutron-operator/composition.yaml) for a complete instance. Creating this CR
installs the operator layer (auth-bridge + RestDefinitions); it does not create any Neutron object.

## Generated Neutron CRDs

Each enabled `restdefinitions.<resource>` block ([configuration.md](configuration.md)) drives one
`RestDefinition` ([`chart/templates/rd-*.yaml`](../chart/templates)), from which `oasgen-provider`
generates a CRD plus a companion `<Kind>Configuration` CRD.

All Kinds share the API group **`network.openstack.krateo.io`**, version `v1alpha1`.

| Kind | Neutron API | Verbs | Envelope key |
|------|-------------|-------|--------------|
| `NeutronNetwork` | `/v2.0/networks` | create / get / update / delete | `network` |
| `NeutronSubnet` | `/v2.0/subnets` | create / get / update / delete | `subnet` |
| `NeutronRouter` | `/v2.0/routers` | create / get / update / delete | `router` |
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

### Cross-resource references

Dependent fields take an OpenStack UUID, read from the referenced CR's `status.<envelope>.id`:

| Field | Value |
|-------|-------|
| `NeutronSubnet.spec.subnet.network_id` | a `NeutronNetwork`'s `status.network.id` |
| `NeutronPort.spec.port.network_id` | a `NeutronNetwork`'s `status.network.id` |
| `NeutronSecurityGroupRule.spec.security_group_rule.security_group_id` | a `NeutronSecurityGroup`'s `status.security_group.id` |

See [usage.md](usage.md) for how to read and wire these.
