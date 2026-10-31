"""Recapture registered public sources into a new directory, never the old release."""

from pathlib import Path
import argparse
import csv
import json

from registry import capture, now


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=Path(__file__).resolve().parents[1] / "source_catalog.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--check-wayback", action="store_true")
    args = parser.parse_args()
    output, private = args.output_dir.resolve(), args.private_dir.resolve()
    if private == output or output in private.parents:
        raise ValueError("The private full-text cache must be outside the public output directory")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a new empty output directory to preserve prior captures")
    output.mkdir(parents=True, exist_ok=True)
    sources = json.loads(args.catalog.read_text(encoding="utf-8"))
    rows = []
    for source in sources:
        receipt = capture(source, private, output, args.check_wayback)
        rows.append({"data_id": source["data_id"], "source_url": source["source_url"], "platform": source["platform"],
            "timestamp": receipt["capture_finished_at"], "snapshot_url": "", "content_hash": receipt["content_hash"],
            "used_for": source["used_for"], "capture_status": receipt["capture_status"],
            "content_path": receipt["content_path"], "external_archive_url": receipt["external_archive_url"],
            "capture_time_basis": "new_capture_not_historical_reconstruction"})
        print(source["data_id"], receipt["capture_status"], flush=True)
    with (output / "recaptured_metadata.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with (output / "recapture_manifest.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump({"finished_at": now(), "source_count": len(rows), "note": "Fresh capture, not the historical input snapshot; snapshot URLs await separate immutable publication."}, handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
