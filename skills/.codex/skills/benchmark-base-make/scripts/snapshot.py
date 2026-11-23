"""Read a resolved Base table completely; never mutate the remote Base."""
import argparse
from common import ReadCLI, cli_prefix, write_json


def collect(cli, base, table, page_size=200):
    if not table.startswith("tbl") or not base:
        raise ValueError("Use the real resolved base token and table ID")
    if not 1 <= page_size <= 200:
        raise ValueError("page-size must be 1..200")
    common = ["--base-token", base, "--table-id", table, "--as", "user", "--format", "json"]
    fields = cli.call(["base", "+field-list"] + common)["fields"]
    known = {f["id"] for f in fields}
    records = {}
    offset = 0
    timezone = None
    revisions = []
    while True:
        data = cli.call(["base", "+record-list"] + common + ["--limit", str(page_size), "--offset", str(offset)])
        columns = data["field_id_list"]
        rows, ids = data["data"], data["record_id_list"]
        if len(columns) != len(set(columns)) or set(columns) != known:
            raise ValueError("Snapshot must include every real field exactly once")
        if len(rows) != len(ids):
            raise ValueError("Record/row count mismatch")
        if timezone is None:
            timezone = data.get("timezone")
        elif data.get("timezone") != timezone:
            raise ValueError("Table timezone changed during pagination")
        if "rev" in data:
            revisions.append(data["rev"])
        for rid, row in zip(ids, rows):
            if rid in records or len(row) != len(columns):
                raise ValueError("Duplicate record or malformed row; pagination may be unstable")
            records[rid] = dict(zip(columns, row))
        if "has_more" not in data or not isinstance(data["has_more"], bool):
            raise ValueError("Missing explicit completeness signal")
        if not data["has_more"]:
            break
        if not rows:
            raise ValueError("Empty page claims more data; refusing a partial snapshot")
        offset += len(rows)
    if len(set(revisions)) > 1:
        raise ValueError("Table changed during pagination; obtain a consistent snapshot")
    return {"schema_version": 1, "target": {"base_token": base, "table_id": table},
            "timezone": timezone, "fields": fields, "records": records,
            "complete": True, "revision": revisions[-1] if revisions else None}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-token", required=True)
    p.add_argument("--table-id", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--page-size", type=int, default=200)
    p.add_argument("--cli-prefix-json")
    a = p.parse_args()
    snapshot = collect(ReadCLI(cli_prefix(a.cli_prefix_json)), a.base_token, a.table_id, a.page_size)
    write_json(a.output, snapshot)
    print("Complete snapshot:", len(snapshot["records"]), "records")


if __name__ == "__main__":
    main()
