#!/usr/bin/env python3
"""Refuse a release whose example Compositions name a different chart version.

WHY THIS EXISTS. crdgen derives a Composition's apiVersion from the chart version of the
CompositionDefinition that registers it: chart 0.1.2 -> composition.krateo.io/v0-1-2, and a CD
at that version serves ONLY that version. release-tag stamps Chart.yaml and the root
compositiondefinition.yaml from the tag, but it deliberately does not touch examples/ (they are
pinned fixtures a reader copies as-is). So the example has to be bumped by hand on every
release, and a comment saying so is prose: examples/neutron-operator/composition.yaml stayed at
v0-1-0 through 0.1.1, matching no released CompositionDefinition.

This makes the hand bump a precondition of the release instead. hack/release-preflight runs it,
called by the org-standard reusable release-preflight.yaml (krateo-blueprints/charts, PUBLISHING.md
rule 12) as release-tag's first job; package-and-push needs that job, so a stale example publishes
nothing.

Usage: validate-example-versions.py <version> [examples-dir]
  version       the release version, e.g. 0.1.2 (the tag, no "v")
  examples-dir  defaults to "examples"

Every YAML document under examples-dir whose apiVersion is in the composition.krateo.io group
must be exactly composition.krateo.io/v<version with dots as dashes>. Regex-driven rather than
YAML-parsed so it needs nothing beyond the standard library on the runner; apiVersion is only
matched at the start of a line, so the derivation notes in comments are not read as manifests.

Exit 1 on any mismatch, on an empty version, or if no Composition is found at all (a gate
with no input must not pass). The version's shape is the shared release-preflight's to check.
"""
import pathlib
import re
import sys

GROUP = "composition.krateo.io"
API_VERSION = re.compile(r"^apiVersion:\s*[\"']?" + re.escape(GROUP) + r"/([^\s\"'#]+)", re.M)


def main(version, examples_dir):
    # The version's shape is checked before this runs, by the shared release-preflight.yaml (charts 1.4.3 and later),
    # with rule 13's exact pattern; the check that stood here (^[0-9]+\.[0-9]+\.[0-9]+$) accepted 0.015.0 and is
    # retired. hack/validate-shared-preflight.py requires the pinned shared step to refuse what it refused. An empty
    # version still names nothing, so it is refused here too.
    if not version:
        print("FAIL: empty version")
        return 1
    # BEGIN dash-refusal (hack/test-validate-example-versions.py deletes it to prove its case sees it)
    # The served version replaces dots with dashes, so 0-1-2 and 0.1.2 would name the same example; refused here,
    # so this check is right on its own and not only behind the shared step's rule-13 check.
    if "-" in version:
        print("FAIL: %r contains '-', which the served version (dots as dashes) cannot tell from a dot" % version)
        return 1
    # END dash-refusal
    want = "v" + version.replace(".", "-")
    root = pathlib.Path(examples_dir)
    if not root.is_dir():
        print("FAIL: %s does not exist -- nothing was checked" % root)
        return 1

    found, bad = 0, []
    for path in sorted(list(root.rglob("*.yaml")) + list(root.rglob("*.yml"))):
        for doc in re.split(r"^---\s*$", path.read_text(), flags=re.M):
            for got in API_VERSION.findall(doc):
                found += 1
                if got == want:
                    print("ok    %s  %s/%s" % (path, GROUP, got))
                else:
                    bad.append("%s: apiVersion %s/%s, but this release (%s) serves %s/%s"
                               % (path, GROUP, got, version, GROUP, want))

    if found == 0:
        print("FAIL: no %s Composition found under %s -- nothing was checked" % (GROUP, root))
        return 1
    for b in bad:
        print("FAIL: " + b)
    if bad:
        print("Bump the example(s) to %s/%s, merge, then tag again." % (GROUP, want))
        return 1
    print("checked %d Composition(s) against %s" % (found, version))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: %s <version> [examples-dir]" % sys.argv[0])
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "examples"))
