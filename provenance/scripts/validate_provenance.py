"""Validate public metadata, frozen text hashes and artifact associations."""

from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import argparse
import csv
import hashlib
import json
import re


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--allow-pending-snapshot-url", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    rows = read_csv(root / "metadata.csv")
    artifacts = read_csv(root / "provenance/artifacts.csv")
    summary = json.loads((root / "provenance/summary.json").read_text(encoding="utf-8"))
    required = {"data_id", "source_url", "platform", "timestamp", "snapshot_url", "content_hash", "used_for"}
    assert rows and required <= set(rows[0])
    ids = {r["data_id"] for r in rows}
    assert len(rows) == len(ids) == summary["source_count"]
    assert len(artifacts) == summary["artifact_count"]
    snapshots = 0
    for row in rows:
        parsed = urlparse(row["source_url"])
        assert parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password
        assert not {"key", "api_key", "token", "access_token"}.intersection(x.lower() for x in parse_qs(parsed.query))
        receipt_path = root / row["receipt_path"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert row["capture_status"] == receipt["capture_status"]
        assert row["content_hash"] == receipt["content_hash"]
        if row["capture_timestamp_iso"]:
            stamp = datetime.fromisoformat(row["capture_timestamp_iso"])
            assert stamp.utcoffset() == timedelta(hours=8)
            assert stamp.strftime("%Y-%m-%d %H:%M:%S") == row["timestamp"]
        else:
            assert not row["timestamp"] and row["capture_status"] == "reference_only_no_request"
        if row["content_hash"]:
            assert row["capture_status"] == "captured_text" and re.fullmatch("[0-9a-f]{64}", row["content_hash"])
        if row["content_path"]:
            text = (root / row["content_path"]).read_bytes()
            assert hashlib.sha256(text).hexdigest() == row["content_hash"]
            assert row["snapshot_type"] == "repository_normalized_text_snapshot"
            snapshots += 1
        if not args.allow_pending_snapshot_url:
            assert row["snapshot_url"]
            if row["snapshot_type"].startswith("repository_"):
                assert "/blob/" + summary["snapshot_commit"] + "/" in row["snapshot_url"]
                assert re.fullmatch("[0-9a-f]{40}", summary["snapshot_commit"])
    assert snapshots == summary["public_text_snapshot_count"]
    assert len({r["artifact_id"] for r in artifacts}) == len(artifacts)
    for artifact in artifacts:
        assert set(artifact["source_data_ids"].split(";")) <= ids
        assert re.fullmatch("[0-9a-f]{64}", artifact["artifact_hash"])
        assert int(artifact["byte_count"]) > 0
        assert not re.match(r"[A-Za-z]:", artifact["artifact_locator"])
    checksums = root / "provenance/SHA256SUMS"
    if checksums.exists():
        for line in checksums.read_text(encoding="ascii").splitlines():
            expected, path = line.split("  ", 1)
            assert hashlib.sha256((root / path).read_bytes()).hexdigest() == expected, path
    print(f"PASS: {len(rows)} source records; {len(artifacts)} artifact hashes; {snapshots} text snapshots; times, links and associations consistent.")


if __name__ == "__main__":
    main()
