---
type: Runbook
title: openstack-neutron-operator-kog — release
description: How a release ships — a SemVer git tag runs the org release-preflight hook (refusing if the example Composition names another version), stamps the chart and the CompositionDefinition, then helm push to oci://ghcr.io/krateo-blueprints/charts and attaches the stamped CompositionDefinition to the release.
resource: oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog
tags: [kog, openstack, neutron, release, oci, ghcr]
timestamp: 2026-11-17T00:00:00Z
---

# Release

The chart is published as an OCI artifact to GHCR by the `release-tag` workflow
([`.github/workflows/release-tag.yaml`](../.github/workflows/release-tag.yaml)).

## What ships

- The Helm chart under [`chart/`](../chart), pushed to
  `oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog:<tag>`.
- The CompositionDefinition, attached to the GitHub release as `compositiondefinition.yaml`.

In git, both [`chart/Chart.yaml`](../chart/Chart.yaml) `version` and
[`compositiondefinition.yaml`](../compositiondefinition.yaml) `spec.chart.version` are the
`CHART_VERSION` placeholder. The workflow stamps both from the tag, so neither is bumped by hand.
Apply the CompositionDefinition attached to the release, not the one in the repository.

## How a release is cut

1. Bump the example Composition's apiVersion to the new version, merged on `main`. crdgen derives the
   Composition's apiVersion from the chart version (`0.1.3` → `composition.krateo.io/v0-1-3`), and a
   CompositionDefinition at that version serves only that one. Nothing stamps `examples/`, so this is
   the one hand edit:
   - [`examples/neutron-operator/composition.yaml`](../examples/neutron-operator/composition.yaml)
     `apiVersion` (required; the release refuses without it), and
   - the derivation examples in [usage.md](usage.md), [api.md](api.md),
     [`examples/neutron-operator/README.md`](../examples/neutron-operator/README.md) and the pin at the
     top of [`docs/llms.txt`](llms.txt) (prose; not checked).
2. Push a **SemVer tag**, with no `v` prefix:

   ```bash
   git tag 0.1.3
   git push origin 0.1.3
   ```

If the release refuses at the example check, nothing has been published yet. Delete the tag (locally and
on the remote), merge the bump, and push the tag again.

## What the workflow does

On a tag matching `[0-9]+.[0-9]+.[0-9]+`, [`release-tag.yaml`](../.github/workflows/release-tag.yaml)
runs two jobs.

**`preflight`** calls the org-standard reusable `release-preflight.yaml` from krateo-blueprints/charts
(PUBLISHING.md rule 12). That workflow runs this repository's executable
[`hack/release-preflight`](../hack/release-preflight) with the tag as `$1`. Here it **refuses the
release** unless every `composition.krateo.io` Composition under `examples/` names
`v<tag with dots as dashes>` ([`hack/validate-example-versions.py`](../hack/validate-example-versions.py)).

**`package-and-push`** declares `needs: preflight`, so a refusal publishes nothing. It:

1. checks out the repo and installs Helm;
2. stamps `CHART_VERSION` in the root `compositiondefinition.yaml` with the tag;
3. logs in to GHCR with the workflow `GITHUB_TOKEN`;
4. stamps `CHART_VERSION` in `Chart.yaml`, then `helm package --version <tag>` and `helm push`;
5. creates the GitHub release if needed and attaches the stamped `compositiondefinition.yaml`.

`helm lint` / `helm template` and the `status-fields` gate run on pull requests
([`.github/workflows/lint.yaml`](../.github/workflows/lint.yaml)), not on the tag.

The `preflight` job pins krateo-blueprints/charts 1.1.0 by its full commit SHA, with `# 1.1.0`
beside it, and never a branch. [`.github/dependabot.yml`](../.github/dependabot.yml) proposes each newer
release as a reviewed PR (PUBLISHING.md rule 9).

## Documentation gate

Documentation is linted on pull requests by the `lint-docs` job in
[`.github/workflows/lint.yaml`](../.github/workflows/lint.yaml), which reuses
`krateo-platformops/.github/.github/workflows/lint-docs.yaml`. Keep the core doc set, frontmatter, and
[`docs/llms.txt`](llms.txt) links valid — see [log.md](log.md) for the standard adoption.
