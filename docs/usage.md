---
type: Usage
title: openstack-neutron-operator-kog — usage
description: How to install the blueprint (chart or Composition), supply the admin clouds.yaml Secret, apply Neutron CRs, wire cross-resource UUID references, and verify the objects in Horizon.
resource: oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog
tags: [kog, openstack, neutron, install, composition, usage]
timestamp: 2026-08-11T00:00:00Z
---

# Usage

This blueprint installs the **operator layer** — the auth-bridge proxy plus one
`RestDefinition` (and generated CRD) per Neutron resource. Once installed, you apply
`Neutron*` custom resources to create real Neutron objects.

For a full click-through with screenshots, see [quickstart.md](quickstart.md).

## Prerequisites

- A Kubernetes cluster with the Krateo KOG provider (`oasgen-provider`) installed:

  ```bash
  helm repo add krateo https://charts.krateo.io && helm repo update
  helm upgrade --install oasgen-provider krateo/oasgen-provider -n krateo-system --create-namespace
  ```

- Network reachability from the cluster to your OpenStack Neutron / Keystone endpoints.
- An admin `clouds.yaml` for your OpenStack cloud.

## 1. Supply the admin `clouds.yaml`

The auth-bridge authenticates with a `clouds.yaml` provided in a Secret. The Secret name defaults to
`neutron-clouds` (see `authBridge.cloudsSecret`):

```bash
kubectl -n krateo-system create secret generic neutron-clouds \
  --from-file=clouds.yaml=clouds.yaml
```

## 2. Install the operator

### Option A — the chart directly

```bash
helm upgrade --install neutron-kog \
  oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog \
  -n krateo-system --create-namespace \
  --set authBridge.upstreamEndpoint=http://neutron-server.openstack.svc.cluster.local:9696
```

Leave `authBridge.upstreamEndpoint` empty to let the proxy auto-discover the `network` endpoint from
the Keystone catalog; set it to pin an in-cluster address (avoids the public-DNS resolver trap).

Wait for a RestDefinition to become Ready (that confirms `oasgen-provider` generated the CRD):

```bash
kubectl -n krateo-system wait restdefinition/neutron-kog-network \
  --for=condition=Ready --timeout=300s
```

### Option B — as a Krateo Composition

Register the chart as a Composition, then create the generated Composition CR:

```bash
kubectl apply -f compositiondefinition.yaml
kubectl apply -f examples/composition.yaml
```

The Composition CR's Kind is `OpenstackNeutronOperatorKog` (PascalCase of the CompositionDefinition
name) and its apiVersion is `composition.krateo.io/v0-1-0` (derived from chart version `0.1.0`). See
[examples.md](examples.md) and [api.md](api.md).

## 3. Create Neutron resources

Each Kind needs a `<Kind>Configuration` CR that references a token Secret. The auth-bridge injects the
real `X-Auth-Token`, so the token value here is a placeholder — any non-empty Secret value works:

```bash
kubectl -n krateo-system create secret generic neutron-token \
  --from-literal=token=proxy-injects-real-token
```

Apply the bundled samples ([`chart/samples/network-resources.yaml`](../chart/samples/network-resources.yaml)):

```bash
kubectl -n krateo-system apply -f chart/samples/network-resources.yaml
kubectl -n krateo-system get neutronnetworks.network.openstack.krateo.io -w
```

A minimal `NeutronNetwork`:

```yaml
apiVersion: network.openstack.krateo.io/v1alpha1
kind: NeutronNetwork
metadata:
  name: demo-net
  namespace: krateo-system
spec:
  configurationRef:
    name: neutron-config
    namespace: krateo-system
  network:
    name: demo-net
    admin_state_up: true
```

## 4. Wire cross-resource references (by UUID)

References between Neutron resources are by OpenStack UUID, not Kubernetes object name. Read the
created id from the referenced CR's status and set it on the dependent CR:

```bash
NETID=$(kubectl -n krateo-system get neutronnetwork demo-net -o jsonpath='{.status.network.id}')
```

Then set `NeutronSubnet.spec.subnet.network_id: "$NETID"`. Sequence dependent resources by hand, or
wire the whole chain with a Krateo Composition.

## 5. Verify

Check reconciliation status:

```bash
kubectl -n krateo-system get neutronnetwork demo-net -o jsonpath='{.status.network.id}{"\n"}'
```

The objects also appear in the OpenStack **Horizon** dashboard under **Network → Networks** and
**Network → Security Groups** — see [quickstart.md](quickstart.md) for screenshots.

## Notes and constraints

- **One namespace.** Keep the Secret, the Configuration CRs and the Neutron CRs in the same namespace
  used to install (default `krateo-system`).
- **Security-group rules are immutable.** To change a `NeutronSecurityGroupRule`, delete and recreate
  the CR.
- **Toggle resources you do not need** via `restdefinitions.<resource>.enabled=false` (see
  [configuration.md](configuration.md)) — fewer CRDs, less surface.
