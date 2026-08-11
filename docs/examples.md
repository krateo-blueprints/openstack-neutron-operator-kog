---
type: ExampleIndex
title: openstack-neutron-operator-kog — examples
description: Index of the runnable examples under examples/ — installing the KOG operator as a Composition and creating Neutron resources.
resource: oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog
tags: [kog, openstack, neutron, examples]
timestamp: 2026-08-11T00:00:00Z
---

# Examples

Runnable examples live under [`examples/`](../examples).

| Example | What it shows |
|---------|---------------|
| [neutron-operator](../examples/neutron-operator/README.md) | Install the operator layer as a Krateo Composition (`OpenstackNeutronOperatorKog`), then create sample Neutron CRs (`NeutronNetwork` / `NeutronSubnet` / `NeutronSecurityGroup` / `NeutronSecurityGroupRule`) that reconcile into real Neutron objects. |

The example ships two manifests:

- [`examples/neutron-operator/composition.yaml`](../examples/neutron-operator/composition.yaml) — the
  operator Composition (auth-bridge + RestDefinitions; enables network/subnet, disables floatingip).
- [`examples/neutron-operator/network-resources.yaml`](../examples/neutron-operator/network-resources.yaml) —
  sample Neutron CRs plus the `<Kind>Configuration` carrying the token.

The same sample CRs are also bundled in the chart at
[`chart/samples/network-resources.yaml`](../chart/samples/network-resources.yaml).

For the full click-through with Horizon screenshots, see [quickstart.md](quickstart.md).
