#!/usr/bin/env python3
"""The release's version shape is the shared release-preflight's to check, and it refuses what this repo's own check did.

    hack/validate-shared-preflight.py [repo-root]

krateo-blueprints/charts release-preflight.yaml (1.4.3 and later) refuses any version that is not a plain X.Y.Z, rule
13's pattern, before the hook runs. This repository's own looser check (`^[0-9]+\\.[0-9]+\\.[0-9]+$`, which accepts
0.015.0) was retired in its favour. So that retirement is safe only while the shared step really refuses, this reads
the release-preflight.yaml pin from .github/workflows/release-tag.yaml, fetches that file AT THAT COMMIT from
krateo-blueprints/charts, and runs its "Run hack/release-preflight" step in a directory with no hook, so only the
version check can decide:
  refused: everything the retired check refused (v1.2.3, 1.2, 1.2.3.4, 1.2.3-rc.1, 1.2.3+build.5, an empty version,
           x.y.z), and what it accepted but rule 13 refuses (0.015.0, 01.2.3, 1.02.3);
  accepted: 1.2.3, 0.15.0, 10.20.30.
Fails (exit 2) when the pin or the step cannot be read, (exit 1) when a case gets the wrong verdict.
"""
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

try:
    import yaml
except ImportError:
    print("FAILED MEASUREMENT: PyYAML unavailable")
    sys.exit(2)

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
REL = os.path.join(ROOT, ".github", "workflows", "release-tag.yaml")
PIN = re.compile(r"krateo-blueprints/charts/\.github/workflows/release-preflight\.yaml@([0-9a-f]{40})")
STEP = "Run hack/release-preflight"
REFUSED = ["v1.2.3", "1.2", "1.2.3.4", "1.2.3-rc.1", "1.2.3+build.5", "", "x.y.z", "0.015.0", "01.2.3", "1.02.3"]
ACCEPTED = ["1.2.3", "0.15.0", "10.20.30"]


def measurement_failed(msg):
    print("FAILED MEASUREMENT: " + msg)
    sys.exit(2)


pins = PIN.findall(open(REL, encoding="utf-8").read())
if len(set(pins)) != 1:
    measurement_failed("expected one release-preflight.yaml pin in %s, found %s" % (REL, sorted(set(pins))))
sha = pins[0]
url = "https://raw.githubusercontent.com/krateo-blueprints/charts/%s/.github/workflows/release-preflight.yaml" % sha
try:
    wf = yaml.safe_load(urllib.request.urlopen(url, timeout=30).read().decode())
except OSError as e:
    measurement_failed("cannot read %s: %s" % (url, e))
steps = [s for s in wf["jobs"]["preflight"]["steps"] if s.get("name") == STEP]
if len(steps) != 1:
    measurement_failed("expected one %r step in release-preflight.yaml at %s" % (STEP, sha))
script = steps[0]["run"]

bad = []
with tempfile.TemporaryDirectory() as empty:
    for version in REFUSED + ACCEPTED:
        env = dict(os.environ, VERSION=version, WORKDIR=empty)
        r = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
        want_ok = version in ACCEPTED
        good = (r.returncode == 0) == want_ok and (want_ok or "is not a plain X.Y.Z" in (r.stdout + r.stderr)
                                                   or (version == "" and "empty version" in (r.stdout + r.stderr)))
        print("%s  %-14r %s" % ("ok  " if good else "FAIL", version, "accepted" if r.returncode == 0 else "refused"))
        if not good:
            bad.append(version)
if bad:
    print("FAIL: release-preflight.yaml at %s gives the wrong verdict for %s" % (sha[:12], bad))
    sys.exit(1)
print("OK: the shared release-preflight at %s refuses %d versions (all the retired check refused, and 0.015.0) and "
      "accepts %d" % (sha[:12], len(REFUSED), len(ACCEPTED)))
