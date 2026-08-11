---
type: Runbook
title: openstack-neutron-operator-kog — release
description: How a release ships — a SemVer git tag matching Chart.yaml drives helm lint, helm package, and helm push to oci://ghcr.io/krateo-blueprints/charts, which the CompositionDefinition then points at.
resource: oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog
tags: [kog, openstack, neutron, release, oci, ghcr]
timestamp: 2026-08-11T00:00:00Z
---

# Release

The chart is published as an OCI artifact to GHCR by the `release-chart` workflow
([`.github/workflows/release-chart.yaml`](../.github/workflows/release-chart.yaml)).

## What ships

One artifact: the Helm chart under [`chart/`](../chart), pushed to
`oci://ghcr.io/krateo-blueprints/charts/openstack-neutron-operator-kog`. The
[`compositiondefinition.yaml`](../compositiondefinition.yaml) `spec.chart.url` points at that artifact,
and `spec.chart.version` selects the tag.

## How a release is cut

1. Bump `version` (and, if it moved, `appVersion`) in [`chart/Chart.yaml`](../chart/Chart.yaml).
2. Push a **SemVer tag** that matches `Chart.yaml` `version` exactly — e.g. for `version: 0.1.0`:

   ```bash
   git tag 0.1.0
   git push origin 0.1.0
   ```

   The tag has no `v` prefix; it must equal the chart version (the workflow fails the release if they
   differ).

The workflow can also be run manually via **workflow_dispatch**.

## What the workflow does

On a matching tag (`[0-9]+.[0-9]+.[0-9]+`) or manual dispatch it:

1. checks out the repo and installs Helm (`v3.19.0`);
2. runs `helm lint chart` (validates the chart and its `values.schema.json`);
3. verifies the git tag matches `Chart.yaml` `version` (tag runs only);
4. runs `helm package chart` — note `helm package` does **not** render templates, so a chart that
   needs runtime input still packages;
5. logs in to GHCR with the workflow `GITHUB_TOKEN`;
6. runs `helm push` to `oci://ghcr.io/<owner>/charts`, retrying on GHCR first-push flakiness.

## After publishing

- Update `compositiondefinition.yaml` `spec.chart.version` to the new tag (and
  `examples/neutron-operator/composition.yaml` if it pins a version) so consumers install the new
  chart.
- Update the pin at the top of [`docs/llms.txt`](llms.txt) to match the released version.

## Documentation gate

Documentation is linted on pull requests by the `lint-docs` job in
[`.github/workflows/lint.yaml`](../.github/workflows/lint.yaml), which reuses
`krateo-platformops/.github/.github/workflows/lint-docs.yaml`. Keep the core doc set, frontmatter, and
[`docs/llms.txt`](llms.txt) links valid — see [log.md](log.md) for the standard adoption.
