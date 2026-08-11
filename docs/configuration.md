---
type: Configuration
title: openstack-neutron-operator-kog — configuration
description: The whole values surface of the chart — the per-resource RestDefinition toggles and the auth-bridge block (clouds Secret, endpoint discovery, image, resources) — plus the CompositionDefinition input mapping.
resource: oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog
tags: [kog, openstack, neutron, values, configuration, auth-bridge]
timestamp: 2026-08-11T00:00:00Z
---

# Configuration

All configuration is the chart's [`values.yaml`](../chart/values.yaml), typed by
[`values.schema.json`](../chart/values.schema.json). When installed as a Composition, the same values
are set under the Composition CR's `spec` (see [`examples/neutron-operator/composition.yaml`](../examples/neutron-operator/composition.yaml)).

## `restdefinitions` — per-resource toggles

One block per Neutron resource. Each controls whether the chart emits that resource's
`RestDefinition` (and therefore the generated CRD). The three keys are identical in shape across all
seven resources:

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `enabled` | boolean | `true` | Generate the RestDefinition (and CRD) for this resource. Set `false` to skip it. |
| `resourceGroup` | string | `network.openstack.krateo.io` | Kubernetes API group for the generated CRD (GVK = `<resourceGroup>/v1alpha1`). |
| `resourceKind` | string | `Neutron<Resource>` | Generated CRD Kind. Prefixed `Neutron*` to avoid the crdgen Kind-vs-envelope-property collision. |

The seven resource blocks and their default Kinds:

| Block | Neutron API | Default `resourceKind` |
|-------|-------------|------------------------|
| `network` | `/v2.0/networks` | `NeutronNetwork` |
| `subnet` | `/v2.0/subnets` | `NeutronSubnet` |
| `router` | `/v2.0/routers` | `NeutronRouter` |
| `port` | `/v2.0/ports` | `NeutronPort` |
| `security_group` | `/v2.0/security-groups` | `NeutronSecurityGroup` |
| `security_group_rule` | `/v2.0/security-group-rules` | `NeutronSecurityGroupRule` |
| `floatingip` | `/v2.0/floatingips` | `NeutronFloatingIP` |

Example — install only networks and subnets:

```yaml
restdefinitions:
  network:
    enabled: true
  subnet:
    enabled: true
  router:
    enabled: false
  port:
    enabled: false
  security_group:
    enabled: false
  security_group_rule:
    enabled: false
  floatingip:
    enabled: false
```

## `authBridge` — the Keystone-auth proxy

The stateless openstacksdk reverse proxy that fronts Neutron and injects a fresh `X-Auth-Token`. See
[overview.md](overview.md) for how it fits together.

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `authBridge.enabled` | boolean | `true` | Deploy the auth-bridge. Disable only if you front Neutron with your own token-injecting proxy. |
| `authBridge.replicaCount` | integer | `1` | Proxy Deployment replicas. |
| `authBridge.cloudsSecret` | string | `neutron-clouds` | Name of the Secret holding the admin `clouds.yaml` (mounted at `/etc/openstack/clouds.yaml`). |
| `authBridge.osCloud` | string | `openstack` | The cloud entry in `clouds.yaml` to authenticate as (`OS_CLOUD`). |
| `authBridge.serviceType` | string | `network` | Keystone service type to discover (Neutron = `network`). |
| `authBridge.osInterface` | string | `internal` | Endpoint interface to use from the catalog (`public` / `internal` / `admin`). |
| `authBridge.upstreamEndpoint` | string | `""` | Pin the Neutron endpoint (e.g. `http://neutron-server.openstack.svc.cluster.local:9696`). Empty = auto-discover from the Keystone catalog. |
| `authBridge.image.repository` | string | `quay.io/airshipit/openstack-client` | Image that ships `python3` + openstacksdk. |
| `authBridge.image.tag` | string | `2026.1-ubuntu_noble` | Image tag. |
| `authBridge.image.pullPolicy` | string | `IfNotPresent` | Image pull policy. |
| `authBridge.service.type` | string | `ClusterIP` | Proxy Service type. |
| `authBridge.service.port` | integer | `8080` | Proxy Service port (the RestDefinition `servers[0].url` targets this). |
| `authBridge.resources` | object | see below | Container resource requests/limits. |
| `authBridge.podAnnotations` | object | `{}` | Extra annotations on the proxy Pod. |
| `authBridge.nodeSelector` | object | `{}` | Pod nodeSelector. |
| `authBridge.tolerations` | array | `[]` | Pod tolerations. |
| `authBridge.affinity` | object | `{}` | Pod affinity. |

Default `authBridge.resources`:

```yaml
resources:
  requests:
    cpu: 20m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

The in-cluster URL the generated controller hits is derived by the chart:
`http://<release>-auth-bridge.<namespace>.svc.cluster.local:<authBridge.service.port>`
(the `authBridgeUrl` helper in [`chart/templates/_helpers.tpl`](../chart/templates/_helpers.tpl)).

## `serviceAccount`

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `serviceAccount.create` | boolean | `false` | Create a ServiceAccount for the auth-bridge. |
| `serviceAccount.name` | string | `""` | Name of the ServiceAccount to use (empty = default). |

## Naming overrides

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `nameOverride` | string | `""` | Override the chart name portion of generated resource names. |
| `fullnameOverride` | string | `""` | Override the full resource name prefix. |

## Composition input mapping

When installed as a Composition, set the same values under the CR `spec`. The example
([`examples/neutron-operator/composition.yaml`](../examples/neutron-operator/composition.yaml)) sets `authBridge` (Secret, cloud,
`upstreamEndpoint`) and toggles individual `restdefinitions.<resource>.enabled`. The Composition's
Kind/apiVersion are generated by `crdgen` from the CompositionDefinition — see [api.md](api.md).
