"""Validate the published dataset with the Python standard library."""

from collections import Counter, defaultdict
from pathlib import Path
import csv
import hashlib
import json
import math


ROOT = Path(__file__).resolve().parent


def read_csv(name):
    with (ROOT / "data" / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    for line in (ROOT / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        expected, path = line.split("  ", 1)
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    weighted = read_csv("shanghai_weighted_trip_chains_20000.csv")
    queries = read_csv("shanghai_r5_query_ods_1000.csv")
    chains = read_csv("shanghai_r5_fastest_trip_chains.csv")
    legs = read_csv("shanghai_r5_fastest_trip_chain_legs.csv")
    stops = read_csv("shanghai_r5_used_transit_stops.csv")
    assert len(weighted) == manifest["weighted_chains"]["rows"] == 20000
    assert len({r["sample_id"] for r in weighted}) == len(weighted)
    assert Counter(r["primary_mode"] for r in weighted) == manifest["weighted_chains"]["mode_counts"]
    assert len(queries) == manifest["r5_itineraries"]["query_od_count"] == 1000
    assert len(chains) == manifest["r5_itineraries"]["returned_chain_count"] == 998
    assert len(legs) == manifest["r5_itineraries"]["leg_count"]
    by_id = {r["chain_id"]: r for r in chains}
    assert len(by_id) == len(chains)
    assert set(by_id) <= {r["od_id"] for r in queries}
    stop_ids = {r["stop_id"] for r in stops}
    grouped = defaultdict(list)
    for row in legs:
        assert row["chain_id"] in by_id
        for field in ("travel_minutes", "wait_minutes"):
            assert math.isfinite(float(row[field])) and float(row[field]) >= 0
        for field in ("start_stop_id", "end_stop_id"):
            assert not row[field] or row[field] in stop_ids
        grouped[row["chain_id"]].append(row)
    for chain_id, group in grouped.items():
        group.sort(key=lambda row: int(row["leg_index"]))
        assert [int(r["leg_index"]) for r in group] == list(range(1, len(group) + 1))
        chain = by_id[chain_id]
        assert int(chain["leg_count"]) == len(group)
        assert chain["realized_mode_sequence"] == "+".join(r["mode"] for r in group)
        total = sum(float(r["travel_minutes"]) + float(r["wait_minutes"]) for r in group)
        assert math.isclose(total, float(chain["total_travel_minutes"]), abs_tol=1e-7)
    assert set(grouped) == set(by_id)
    print(f"PASS: {len(weighted)} weighted records; {len(queries)} query ODs; "
          f"{len(chains)} routed chains; {len(legs)} legs; checksums and references valid.")


if __name__ == "__main__":
    main()
