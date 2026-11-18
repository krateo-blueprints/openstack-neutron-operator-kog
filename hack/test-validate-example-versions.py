#!/usr/bin/env python3
"""hack/validate-example-versions.py gives the right verdict on its own, and its dash refusal is what refuses 0-1-2.

    python3 hack/test-validate-example-versions.py

Writes an examples/ directory whose Composition is composition.krateo.io/v0-1-2, runs the validator on it with each
version, and checks the exit code: 0.1.2 passes; 0-1-2 (which the dots-as-dashes mapping cannot tell from 0.1.2),
0.1.3, v0.1.2 and an empty version are refused. Then it deletes the marked `dash-refusal` block and requires that
mutant to pass 0-1-2, so the case is shown to test that block.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "validate-example-versions.py")).read()
CASES = [("0.1.2", 0), ("0-1-2", 1), ("0.1.3", 1), ("v0.1.2", 1), ("", 1)]


def run(source, version, examples):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(source)
    try:
        return subprocess.run([sys.executable, "-I", f.name, version, examples], capture_output=True, text=True).returncode
    finally:
        os.unlink(f.name)


lines = SRC.split("\n")
b = [i for i, l in enumerate(lines) if "# BEGIN dash-refusal" in l]
e = [i for i, l in enumerate(lines) if "# END dash-refusal" in l]
if len(b) != 1 or len(e) != 1:
    print("FAILED MEASUREMENT: the dash-refusal block is not marked exactly once")
    sys.exit(2)
mutant = "\n".join(lines[:b[0]] + lines[e[0] + 1:])
bad = 0
with tempfile.TemporaryDirectory() as d:
    ex = os.path.join(d, "examples")
    os.makedirs(ex)
    open(os.path.join(ex, "composition.yaml"), "w").write("apiVersion: composition.krateo.io/v0-1-2\nkind: NeutronOperator\n")
    for version, want in CASES:
        rc = run(SRC, version, ex)
        ok = rc == want
        bad += not ok
        print("%s  %-8r exit=%d (want %d)" % ("ok  " if ok else "FAIL", version, rc, want))
    rc = run(mutant, "0-1-2", ex)
    ok = rc == 0
    bad += not ok
    print("%s  without dash-refusal, '0-1-2' exit=%d (want 0: the case tests the block)" % ("ok  " if ok else "FAIL", rc))
print("%d case(s) and 1 mutant, %d failure(s)" % (len(CASES), bad))
sys.exit(1 if bad else 0)
