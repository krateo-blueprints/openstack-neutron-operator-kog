---
type: Example
title: neutron-operator — install the KOG operator and create Neutron resources
description: A runnable example of the OpenStack Neutron KOG — the Composition that installs the operator layer (auth-bridge + RestDefinitions) plus sample Neutron CRs (network, subnet, security group, security-group rule) that reconcile into real Neutron objects.
resource: oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog
tags: [example, kog, openstack, neutron, composition]
timestamp: 2026-08-11T00:00:00Z
---

# neutron-operator

A complete, runnable example of the OpenStack Neutron KOG blueprint. It has two parts:

- [`composition.yaml`](composition.yaml) — the **operator layer**: a Krateo Composition CR
  (`OpenstackNeutronOperatorKog`) that installs the auth-bridge proxy plus the per-resource
  RestDefinitions and their generated CRDs. It does **not** create any Neutron object itself.
- [`network-resources.yaml`](network-resources.yaml) — sample **Neutron CRs**
  (`NeutronNetwork` / `NeutronSubnet` / `NeutronSecurityGroup` / `NeutronSecurityGroupRule`) plus the
  `<Kind>Configuration` that carries the bearer token. Applying these creates real Neutron objects.

## Prerequisites

- The Krateo KOG provider (`oasgen-provider`) installed in the cluster.
- The CompositionDefinition applied so Krateo knows this blueprint:

  ```bash
  kubectl apply -f ../../compositiondefinition.yaml
  ```

- An admin `clouds.yaml` in a Secret named `neutron-clouds` in `krateo-system`:

  ```bash
  kubectl -n krateo-system create secret generic neutron-clouds \
    --from-file=clouds.yaml=clouds.yaml
  ```

## 1. Install the operator

```bash
kubectl apply -f composition.yaml
```

This example pins the Neutron endpoint (`authBridge.upstreamEndpoint`), enables the `network` and
`subnet` RestDefinitions, and disables `floatingip` to show how to toggle resources. The generated
Composition CR is `composition.krateo.io/v0-1-0`, Kind `OpenstackNeutronOperatorKog` — see
[../../docs/api.md](../../docs/api.md) for how that Kind/apiVersion is derived.

Wait for a RestDefinition to become Ready:

```bash
kubectl -n krateo-system wait restdefinition/openstack-neutron-operator-kog-network \
  --for=condition=Ready --timeout=300s
```

## 2. Create Neutron resources

The auth-bridge injects the real token, so the referenced token Secret value is a placeholder:

```bash
kubectl -n krateo-system create secret generic neutron-token \
  --from-literal=token=proxy-injects-real-token
kubectl -n krateo-system apply -f network-resources.yaml
```

Cross-resource references are by OpenStack UUID. Read the network id from its status and set it on the
subnet's `spec.subnet.network_id`:

```bash
NETID=$(kubectl -n krateo-system get neutronnetwork demo-net -o jsonpath='{.status.network.id}')
```

Watch reconciliation:

```bash
kubectl -n krateo-system get neutronnetworks.network.openstack.krateo.io -w
```

The created objects appear in the OpenStack Horizon dashboard — see
[../../docs/quickstart.md](../../docs/quickstart.md) for screenshots.

## Clean up

```bash
kubectl -n krateo-system delete -f network-resources.yaml
kubectl -n krateo-system delete -f composition.yaml
```
