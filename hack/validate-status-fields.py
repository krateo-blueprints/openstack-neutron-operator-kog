#!/usr/bin/env python3
"""Fail if a RestDefinition asks for a status field its observe response cannot carry.

WHY THIS EXISTS. rest-dynamic-controller fills status.<field> for every identifier and
additionalStatusField by reading that path out of the observed response body, and SKIPS a
path that is absent -- no log, no condition (populateStatusFields). oasgen-provider notices at
generation time, but only as a warning (CodeStatusFieldNotFound) that nobody reads. So a field
that the response never carries renders as an empty status column forever, and looks exactly
like "Neutron has not filled it in yet".

Three Kinds shipped that way: NeutronSubnet, NeutronSecurityGroup and NeutronSecurityGroupRule
each list `<envelope>.status`, and Neutron's subnet, security-group and security-group-rule
objects have no `status` attribute (neutron/db/db_base_plugin_common.py _make_subnet_dict,
neutron/db/securitygroups_db.py _make_security_group_dict / _make_security_group_rule_dict;
the api-ref lists none either).

WHAT IT CHECKS, and against what. For each rendered RestDefinition it resolves the schema the
controller observes -- the `get` verb's 2xx response, else ONE ITEM of the `findby` response
(honouring itemsPath) -- from the curated OAS in the matching ConfigMap, and walks every
identifier and additionalStatusField through it. A field that a response-direction fieldMapping
(inResponse -> inCustomResource) on get/findby produces is resolved through its SOURCE path,
the same way oasgen-provider types it. The subject is the curated OAS, so this proves "the
document we ship can carry this field"; that the document is faithful to Neutron is what the
api-ref citations in each asset are for.

KNOWN_ABSENT is the escape hatch, and it is narrow on purpose: oasgen-provider's RestDefinition
CRD makes additionalStatusFields APPEND-ONLY (a CEL transition rule), so an entry that already
shipped cannot be removed without making `helm upgrade` fail for every existing install. Each
entry must name a reason, and an entry that starts resolving fails the check, so the list can
only shrink.

Exit 1 on any unresolvable field, on a stale KNOWN_ABSENT entry, or if no RestDefinition was
rendered at all (a gate with no input must not pass).
"""
import subprocess
import sys

import yaml

# (RestDefinition name suffix, status field) -> why it stays although it never resolves.
APPEND_ONLY = (
    "shipped in 0.1.x; oasgen-provider makes additionalStatusFields append-only, so removing it "
    "would fail helm upgrade for existing installs. Neutron's object has no status attribute, so "
    "status.%s is always empty."
)
KNOWN_ABSENT = {
    ("-subnet", "subnet.status"): APPEND_ONLY % "subnet.status",
    ("-security-group", "security_group.status"): APPEND_ONLY % "security_group.status",
    ("-security-group-rule", "security_group_rule.status"): APPEND_ONLY % "security_group_rule.status",
}


def render(chart):
    """Render the chart. Chart.yaml carries the CHART_VERSION placeholder until release, which
    helm rejects as a version, so CI stamps it first (see .github/workflows/lint.yaml)."""
    proc = subprocess.run(
        ["helm", "template", "release", chart, "--namespace", "krateo-system"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit("FAIL: helm template %s failed -- nothing was checked" % chart)
    return [d for d in yaml.safe_load_all(proc.stdout) if d]


def resolve_ref(doc, node, depth=0):
    if depth > 32:
        raise ValueError("$ref chain too deep")
    while isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"]
        if not ref.startswith("#/"):
            raise ValueError("only local $refs are supported: %s" % ref)
        cur = doc
        for seg in ref[2:].split("/"):
            cur = cur[seg]
        node = cur
        depth += 1
    return node


def response_schema(doc, verb):
    path_item = doc.get("paths", {}).get(verb["path"])
    if path_item is None:
        raise ValueError("path %s is not in the OAS" % verb["path"])
    op = path_item.get(verb["method"].lower())
    if op is None:
        raise ValueError("%s %s is not in the OAS" % (verb["method"], verb["path"]))
    for code, resp in sorted(op.get("responses", {}).items()):
        if str(code).startswith("2"):
            resp = resolve_ref(doc, resp)
            content = resp.get("content", {}).get("application/json")
            if content and "schema" in content:
                return resolve_ref(doc, content["schema"])
    raise ValueError("%s %s declares no 2xx application/json schema" % (verb["method"], verb["path"]))


def findby_item(doc, schema, items_path):
    schema = resolve_ref(doc, schema)
    if schema.get("type") == "array":
        return resolve_ref(doc, schema["items"])
    props = schema.get("properties", {})
    if items_path:
        cur = schema
        for seg in items_path.split("."):
            cur = resolve_ref(doc, cur.get("properties", {}).get(seg, {}))
        if cur.get("type") != "array":
            raise ValueError("itemsPath %s does not resolve to an array" % items_path)
        return resolve_ref(doc, cur["items"])
    arrays = [k for k, v in props.items() if resolve_ref(doc, v).get("type") == "array"]
    if len(arrays) == 1:
        return resolve_ref(doc, resolve_ref(doc, props[arrays[0]])["items"])
    if not arrays:
        return schema
    raise ValueError("findby response has several arrays %s and no itemsPath" % arrays)


def has_path(doc, schema, dotted):
    cur = resolve_ref(doc, schema)
    for seg in dotted.split("."):
        props = cur.get("properties", {})
        if seg not in props:
            return False
        cur = resolve_ref(doc, props[seg])
    return True


def main(chart):
    docs = render(chart)
    configmaps = {d["metadata"]["name"]: d for d in docs if d.get("kind") == "ConfigMap"}
    rds = [d for d in docs if d.get("kind") == "RestDefinition"]
    if not rds:
        print("FAIL: no RestDefinition rendered from %s -- nothing was checked" % chart)
        return 1

    failures = []
    seen_allowances = set()
    for rd in rds:
        name = rd["metadata"]["name"]
        res = rd["spec"]["resource"]
        # configmap://<namespace>/<name>/<key>
        _, _, rest = rd["spec"]["oasPath"].partition("configmap://")
        _, cm_name, key = rest.split("/", 2)
        doc = yaml.safe_load(configmaps[cm_name]["data"][key])

        verbs = {v["action"]: v for v in res.get("verbsDescription", [])}
        if "get" in verbs:
            observe = verbs["get"]
            schema = response_schema(doc, observe)
        elif "findby" in verbs:
            observe = verbs["findby"]
            schema = findby_item(doc, response_schema(doc, observe), observe.get("itemsPath", ""))
        else:
            failures.append("%s: no get or findby verb, so no status field can ever be populated" % name)
            continue

        mapped = {}
        for action in ("get", "findby"):
            for m in verbs.get(action, {}).get("fieldMapping", []) or []:
                if m.get("inResponse") and m.get("inCustomResource"):
                    dest = m["inCustomResource"]
                    if dest.startswith("status."):
                        dest = dest[len("status."):]
                    mapped.setdefault(dest, m["inResponse"])

        fields = list(res.get("identifiers", [])) + list(res.get("additionalStatusFields", []))
        checked = 0
        for field in dict.fromkeys(fields):
            checked += 1
            source = mapped.get(field, field)
            ok = has_path(doc, schema, source)
            allowance = next((k for k in KNOWN_ABSENT if name.endswith(k[0]) and k[1] == field), None)
            if allowance:
                seen_allowances.add(allowance)
            if allowance and not ok:
                print("known-absent  %s  status.%s  (%s)" % (name, field, KNOWN_ABSENT[allowance]))
            elif allowance and ok:
                failures.append("%s: status.%s is in KNOWN_ABSENT but now resolves -- remove the entry" % (name, field))
            elif not ok:
                via = "" if source == field else " (via fieldMapping from %s)" % source
                failures.append(
                    "%s: status.%s%s is not in the %s %s response schema, so it would stay empty forever"
                    % (name, field, via, observe["method"], observe["path"]))
            else:
                print("ok            %s  status.%s" % (name, field))
        if checked == 0:
            failures.append("%s: declares no identifiers or additionalStatusFields" % name)

    for k in KNOWN_ABSENT:
        if k not in seen_allowances:
            failures.append("KNOWN_ABSENT entry %s matches no rendered RestDefinition field -- remove it" % (k,))

    print("checked %d RestDefinitions" % len(rds))
    if failures:
        for f in failures:
            print("FAIL: " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "chart"))
