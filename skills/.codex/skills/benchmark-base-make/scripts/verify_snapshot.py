"""Verify exact allowed mutations and attachment evidence from complete local snapshots."""
import argparse, hashlib, pathlib
from common import read_json, write_json, field_index, normalize


def verify(before, after, expect, directory):
    if before.get("complete") is not True or after.get("complete") is not True or before["target"] != after["target"]:
        raise ValueError("Require complete snapshots of the same table")
    old_fields = {f["id"]: f for f in before["fields"]}
    new_fields, resolve = field_index(after)
    schema = expect.get("expected_schema", before["fields"])
    expected_fields = {f["id"]: f for f in schema}
    if len(expected_fields) != len(schema) or new_fields != expected_fields:
        raise ValueError("Unexpected field configuration change")
    old, new = before["records"], after["records"]
    created_list = expect.get("created_record_ids", [])
    created = set(created_list)
    if len(created) != len(created_list) or created & set(old) or set(new) != set(old) | created:
        raise ValueError("Unexpected/duplicate created IDs, removals, or unplanned rows")
    if len(new) != expect["expected_count"]:
        raise ValueError("Final row count mismatch")
    wanted = {}
    for rid, fields in expect.get("expected_records", {}).items():
        if rid not in new:
            raise ValueError("Expected record missing")
        values = {}
        for key, value in fields.items():
            fid = resolve(key)
            if fid in values:
                raise ValueError("Duplicate field aliases in expected record")
            values[fid] = value
        wanted[rid] = values
    if not created <= set(wanted) or any(not wanted[rid] for rid in created):
        raise ValueError("Every created record needs observed-ID-bound field expectations")
    allowed = {rid: {resolve(f) for f in fields} for rid, fields in expect.get("allowed_existing_changes", {}).items()}
    if not set(allowed) <= set(old):
        raise ValueError("Allowed changes reference nonexisting original records")
    attachment_keys = {(a["record_id"], resolve(a["field_id"])) for a in expect.get("attachments", [])}
    for rid, fields in allowed.items():
        for fid in fields:
            if fid not in wanted.get(rid, {}) and (rid, fid) not in attachment_keys:
                raise ValueError("Allowed change lacks a concrete expected value or attachment check")
    timezone = after.get("timezone")
    for rid, row in old.items():
        for fid in set(row) | set(new[rid]):
            if fid in allowed.get(rid, set()):
                continue
            field = new_fields.get(fid) or old_fields[fid]
            if expect.get("allow_system_updates") and allowed.get(rid) and field["type"] in {"updated_at", "updated_by"}:
                continue
            if normalize(row.get(fid), field, timezone) != normalize(new[rid].get(fid), field, timezone):
                raise ValueError("Unexpected existing-record mutation: " + rid + "/" + fid)
    for rid, fields in wanted.items():
        for fid, value in fields.items():
            if normalize(new[rid].get(fid), new_fields[fid], timezone) != normalize(value, new_fields[fid], timezone):
                raise ValueError("Expected value mismatch: " + rid + "/" + fid)
    integrity = []
    for item in expect.get("attachments", []):
        rid, fid = item["record_id"], resolve(item["field_id"])
        if new_fields[fid]["type"] != "attachment" or rid not in new:
            raise ValueError("Wrong attachment record or field")
        files = new[rid].get(fid) or []
        if "exact_count" in item and len(files) != item["exact_count"]:
            raise ValueError("Attachment count mismatch")
        absent = set(item.get("absent_tokens", []))
        current = {f["file_token"] for f in files}
        if current & absent:
            raise ValueError("Old attachment token still present")
        if rid in old:
            previous = {f["file_token"] for f in old[rid].get(fid) or []}
            if not previous - absent <= current:
                raise ValueError("Unexpected removal of a retained old attachment")
        local = (directory / item["local_path"]).resolve()
        matches = [f for f in files if f["name"] == local.name and f["size"] == local.stat().st_size]
        if len(matches) != 1:
            raise ValueError("Missing or ambiguous expected attachment")
        result = {"record_id": rid, "field_id": fid, "name_size_verified": True,
                  "download_hash_verified": False}
        if "downloaded_path" in item:
            downloaded = (directory / item["downloaded_path"]).resolve()
            if "download_receipt_path" not in item:
                raise ValueError("Cloud hash claim requires the actual CLI download receipt")
            receipt = read_json(directory / item["download_receipt_path"])
            if receipt.get("ok") is not True:
                raise ValueError("Download receipt unsuccessful")
            evidence = [f for f in receipt["data"]["downloaded"] if f.get("file_token") == matches[0]["file_token"]]
            if len(evidence) != 1 or pathlib.Path(evidence[0]["saved_path"]).resolve() != downloaded:
                raise ValueError("Download receipt does not bind the current token to the provided file")
            if evidence[0].get("record_id") != rid or evidence[0].get("field_id") != fid:
                raise ValueError("Download receipt is for a different record/field")
            if hashlib.sha256(local.read_bytes()).digest() != hashlib.sha256(downloaded.read_bytes()).digest():
                raise ValueError("Downloaded attachment content differs")
            result["download_hash_verified"] = True
        integrity.append(result)
    return {"status": "construction_checks_passed", "count": len(new), "created": len(created),
            "existing_records_checked": len(old), "allowed_modified_records": len(allowed),
            "schema_verified": True, "attachment_checks": integrity,
            "independent_semantic_extraction": "not_checked_by_this_helper", "query_blind_test": "not_run_by_this_helper"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ["before", "after", "expect", "output"]:
        p.add_argument("--" + key, required=True)
    a = p.parse_args()
    spec = pathlib.Path(a.expect).resolve()
    result = verify(read_json(a.before), read_json(a.after), read_json(spec), spec.parent)
    write_json(a.output, result)
    print("Construction checks passed; independent semantic/query acceptance is separate")


if __name__ == "__main__":
    main()
