"""Validate a reviewed plan against snapshots and emit JSON requests; no remote writes."""
import argparse, pathlib, re
from common import read_json, write_json, field_index, normalize

WRITABLE = {"text", "number", "select", "datetime", "checkbox", "user", "group_chat", "link", "location"}


def canonical_fields(raw, snap):
    definitions, resolve = field_index(snap)
    result = {}
    for key, value in raw.items():
        fid = resolve(key)
        if fid in result:
            raise ValueError("Duplicate aliases for field " + fid)
        field = definitions[fid]
        if field["type"] not in WRITABLE:
            raise ValueError("Read-only, attachment, or unsupported CellValue field: " + key)
        normalize(value, field, snap.get("timezone"))
        if value is not None:
            if field["type"] == "text" and not isinstance(value, str):
                raise ValueError("Text requires a string")
            if field["type"] == "select":
                if field.get("multiple") and not isinstance(value, list):
                    raise ValueError("Multiselect requires a string array")
                if not field.get("multiple") and not isinstance(value, str):
                    raise ValueError("Single select requires a string")
                vals = value if isinstance(value, list) else [value]
                if not set(vals) <= {o["name"] for o in field.get("options", [])}:
                    raise ValueError("Unknown selection; perform authorized migration first: " + key)
            if field["type"] == "location" and (not isinstance(value, dict) or set(value) != {"lng", "lat"}
                    or any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in value.values())
                    or not -180 <= value["lng"] <= 180 or not -90 <= value["lat"] <= 90):
                raise ValueError("Location requires numeric lng/lat in range")
        result[fid] = value
    return result


def prepare(plan, directory):
    if plan.get("schema_version") != 1:
        raise ValueError("Unsupported plan version")
    source = plan["source"]
    if not source.get("question_id") or not source.get("record_id"):
        raise ValueError("Source question and record must be resolved")
    urls = source["target_urls_raw"]
    targets = {}
    for t in plan["targets"]:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", t["key"]) or t["key"] in targets or t["url"] not in urls:
            raise ValueError("Duplicate target key or target URL outside the selected source cell")
        snap = read_json(directory / t["snapshot_path"])
        if snap.get("complete") is not True or snap["target"] != {"base_token": t["base_token"], "table_id": t["table_id"]}:
            raise ValueError("Incomplete or wrong-target snapshot")
        targets[t["key"]] = (t, snap)
    keys, creates, updates, uploads, matchers, update_ids = set(), {}, {}, [], {}, set()
    for sample in plan["records"]:
        key = sample["key"]
        if key in keys or not key:
            raise ValueError("Sample keys must be unique and nonempty")
        keys.add(key)
        t, snap = targets[sample["target"]]
        values = canonical_fields(sample.get("fields", {}), snap)
        kind = sample["action"]
        if kind == "create":
            matches = canonical_fields(sample.get("match_fields", {}), snap)
            if not matches or any(v is None for v in matches.values()) or not matches.items() <= values.items():
                raise ValueError("Create requires nonempty match_fields included in submitted fields")
            defs, _ = field_index(snap)
            def matches_row(row):
                return all(normalize(row.get(fid), defs[fid], snap.get("timezone")) ==
                           normalize(v, defs[fid], snap.get("timezone")) for fid, v in matches.items())
            if any(matches_row(r) for r in snap["records"].values()):
                raise ValueError("Create key already exists; reconcile rather than recreate: " + key)
            for other_matches, other_values in matchers.setdefault(t["key"], []):
                if matches_row(other_values) or all(normalize(values.get(f), defs[f], snap.get("timezone")) == normalize(v, defs[f], snap.get("timezone")) for f, v in other_matches.items()):
                    raise ValueError("Ambiguous match key within create batch")
            matchers[t["key"]].append((matches, values))
            creates.setdefault(t["key"], []).append((key, values))
            rid = None
        elif kind == "update":
            rid = sample["record_id"]
            ident = (t["key"], rid)
            if rid not in snap["records"] or ident in update_ids:
                raise ValueError("Update record missing or specified twice")
            update_ids.add(ident)
            updates.setdefault(t["key"], []).append((key, rid, values))
        else:
            raise ValueError("Only create/update actions supported")
        defs, resolve = field_index(snap)
        for attachment in sample.get("attachments", []):
            fid = resolve(attachment["field"])
            if defs[fid]["type"] != "attachment":
                raise ValueError("Upload field is not an attachment")
            file = (directory / attachment["path"]).resolve()
            if not file.is_file():
                raise ValueError("Generate attachment before preparing writes")
            uploads.append({"sample_key": key, "target": t["key"], "record_id": rid,
                            "field_id": fid, "path": str(file)})
    gold = plan.get("gold", {})
    positives = {tuple(x) for x in gold.get("positive_pairs", [])}
    negatives = {tuple(x) for x in gold.get("negative_pairs", [])}
    for pair in positives | negatives:
        if len(pair) != 2 or not set(pair) <= keys:
            raise ValueError("Gold pair references unknown sample keys")
    if positives & negatives:
        raise ValueError("Same pair is both positive and negative")
    return targets, creates, updates, uploads


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    src = pathlib.Path(a.plan).resolve()
    targets, creates, updates, uploads = prepare(read_json(src), src.parent)
    out = pathlib.Path(a.output_dir)
    operations = []
    for key in targets:
        for action, collection in [("create", creates.get(key, [])), ("update", updates.get(key, []))]:
            for start in range(0, len(collection), 200):
                batch = collection[start:start + 200]
                name = f"{key}-{action}-{start // 200 + 1:03d}.json"
                body = {"create_records": [x[1] for x in batch]} if action == "create" else {"update_records": {x[1]: x[2] for x in batch}}
                write_json(out / name, body)
                operations.append({"target": key, "action": action, "sample_keys": [x[0] for x in batch],
                                   "payload_file": name})
    write_json(out / "operations.json", {"operations": operations, "attachments": uploads,
               "note": "Local preparation only; review scope and authorization before executing CLI writes."})
    print("Prepared", len(operations), "record requests and", len(uploads), "attachment tasks; no remote writes")


if __name__ == "__main__":
    main()
