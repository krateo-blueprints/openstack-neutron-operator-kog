# openstack-neutron-operator-kog

Krateo Operator Generator (KOG) packaging that turns **OpenStack Neutron (networking v2.0)**
resources into native Kubernetes custom resources — no hand-written controller, just a curated
OpenAPI subset per resource and a generic `rest-dynamic-controller`.

`kubectl apply` a `NeutronNetwork` / `NeutronSubnet` / … CR &rarr; KOG's
[`oasgen-provider`](https://github.com/krateoplatformops/oasgen-provider) +
[`rest-dynamic-controller`](https://github.com/krateoplatformops/rest-dynamic-controller)
reconcile it into a real Neutron object.

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

Each Neutron payload is envelope-wrapped (`{network:{…}}`, `{subnet:{…}}`, …), so every Kind is
prefixed `Neutron*` to avoid the crdgen Kind-vs-property collision (the same reason Nova's `Server`
→ `Instance`). Neutron updates are a `PUT` with a partial body (the Neutron convention), so CRUD
resources carry an `update` verb; security-group rules are immutable (no update).

## Auth: the openstacksdk proxy (auto-refreshing)

KOG's controller speaks plain HTTP and can't do Keystone token exchange. This chart ships a small
**auth-bridge** (`scripts/openstack-auth-proxy.py` in the openstack-client image): it authenticates
with a `clouds.yaml`, discovers the `network` endpoint, and injects a **fresh** `X-Auth-Token` on
every call. It never expires and works in-cluster (no public-DNS resolver trap). Supply the admin
`clouds.yaml` in a Secret:

```bash
kubectl create secret generic neutron-clouds --from-file=clouds.yaml=clouds.yaml -n krateo-system
```

## Quickstart

```bash
helm repo add krateo https://charts.krateo.io && helm repo update
helm upgrade --install oasgen-provider krateo/oasgen-provider -n krateo-system --create-namespace

kubectl create secret generic neutron-clouds --from-file=clouds.yaml=clouds.yaml -n krateo-system
helm upgrade --install neutron-kog ./chart -n krateo-system \
  --set authBridge.upstreamEndpoint=http://neutron-server.openstack.svc.cluster.local:9696

kubectl -n krateo-system apply -f chart/samples/network-resources.yaml
kubectl -n krateo-system get neutronnetworks.network.openstack.krateo.io -w
```

## What's in here

```
chart/
  Chart.yaml
  values.yaml                 # per-resource toggles + auth-bridge config
  assets/                     # one Neutron OAS subset per resource
    network.yaml subnet.yaml router.yaml port.yaml
    security-group.yaml security-group-rule.yaml floatingip.yaml
  scripts/
    openstack-auth-proxy.py   # openstacksdk Keystone-auth reverse proxy
  templates/
    configmap-*.yaml          # bundle each OAS into a ConfigMap
    rd-*.yaml                 # one RestDefinition per resource (toggle via values)
    auth-bridge-*.yaml        # the auth proxy Deployment/Service/ConfigMap
  samples/
    network-resources.yaml    # example CRs (Configuration + Network/Subnet/SecurityGroup/…)
```

## Notes

- Cross-resource references are by OpenStack UUID (e.g. `NeutronSubnet.spec.subnet.network_id`,
  `NeutronPort.spec.port.network_id`). Read the created ID from the referenced CR's
  `status.<envelope>.id` and wire it into the dependent CR — or use a Krateo Composition to
  sequence them.
- `NeutronSecurityGroupRule` is immutable; change a rule by deleting and recreating the CR.

## License

Apache-2.0 — see [LICENSE](LICENSE).
