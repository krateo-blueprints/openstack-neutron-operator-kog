---
type: Component
title: openstack-neutron-operator-kog — index
description: The map of the openstack-neutron-operator-kog doc bundle — a Krateo Operator Generator (KOG) blueprint that turns OpenStack Neutron networking resources into native Kubernetes custom resources via oasgen-provider and rest-dynamic-controller.
resource: oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog
tags: [kog, openstack, neutron, network, oasgen-provider, blueprint]
timestamp: 2026-08-11T00:00:00Z
---

# openstack-neutron-operator-kog

A Krateo Operator Generator (KOG) blueprint that turns **OpenStack Neutron
(networking v2.0)** resources — networks, subnets, routers, ports, security
groups, security-group rules and floating IPs — into native Kubernetes custom
resources. No hand-written controller: a curated OpenAPI subset per resource
plus a generic [`rest-dynamic-controller`](https://github.com/krateo-platformops/rest-dynamic-controller),
wired up by [`oasgen-provider`](https://github.com/krateo-platformops/oasgen-provider).

`kubectl apply` a `NeutronNetwork` / `NeutronSubnet` / … CR and it is reconciled
into a real Neutron object. A stateless **auth-bridge** proxy handles Keystone
token exchange so the generated controller can speak plain HTTP.

## Doc bundle

| Doc | What it covers |
|-----|----------------|
| [overview.md](overview.md) | What the blueprint is and how it is built — the KOG layer, the auth-bridge, the envelope/Kind naming convention |
| [usage.md](usage.md) | Install the chart or the Composition, supply `clouds.yaml`, apply Neutron CRs, verify in Horizon |
| [configuration.md](configuration.md) | The whole values surface — per-resource toggles and the auth-bridge block |
| [api.md](api.md) | The CompositionDefinition CRD and the generated Neutron CRDs (Kinds, groups, verbs) |
| [examples.md](examples.md) | Index of the runnable examples under [`examples/`](../examples) |
| [release.md](release.md) | How a release ships — one SemVer tag drives the chart to GHCR |
| [log.md](log.md) | Curated history of notable changes |
| [quickstart.md](quickstart.md) | End-to-end walkthrough: install, apply CRs, see them in Horizon |
| [llms.txt](llms.txt) | One-line-per-file index for LLM consumption |

## Repo layout

```
chart/                         # the Helm chart (the KOG operator layer)
  Chart.yaml
  values.yaml                  # per-resource toggles + auth-bridge config
  values.schema.json           # typed schema for the values above
  assets/                      # one Neutron OAS subset per resource
  scripts/                     # the openstacksdk Keystone-auth reverse proxy
  templates/                   # ConfigMaps, RestDefinitions, auth-bridge Deployment/Service
  samples/                     # example Neutron CRs
compositiondefinition.yaml     # registers the chart as a Krateo Composition
examples/                      # runnable example (the operator Composition)
docs/                          # this bundle
```

## Resources

| Kind | Neutron API | Verbs |
|------|-------------|-------|
| `NeutronNetwork` | `/v2.0/networks` | create / get / update / delete |
| `NeutronSubnet` | `/v2.0/subnets` | create / get / update / delete |
| `NeutronRouter` | `/v2.0/routers` | create / get / update / delete |
| `NeutronPort` | `/v2.0/ports` | create / get / update / delete |
| `NeutronSecurityGroup` | `/v2.0/security-groups` | create / get / update / delete |
| `NeutronSecurityGroupRule` | `/v2.0/security-group-rules` | create / get / delete (immutable) |
| `NeutronFloatingIP` | `/v2.0/floatingips` | create / get / update / delete |

See the [README](../README.md) for the short version.
