"""Recompute the central claims from recorded outputs; no model required."""

from collections import defaultdict
from itertools import combinations
from pathlib import Path
import csv
import hashlib
import json
import math

from metrics import empirical_entropy, modal_consistency, validate_profile, cpc


ROOT = Path(__file__).resolve().parent


def load_csv(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    cases = json.loads((ROOT / "inputs.json").read_text(encoding="utf-8"))
    protocol = json.loads((ROOT / "protocol.json").read_text(encoding="utf-8"))
    report = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    records = [json.loads(line) for line in (ROOT / "raw_samples.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(cases) == 40 and len(records) == 400 and protocol["repeats"] == 10
    assert len({(r["case_id"], r["replicate"]) for r in records}) == 400
    assert len({r["seed"] for r in records}) == 400
    grouped = defaultdict(list)
    for r in records:
        assert r["valid"] and r["response_metadata"]["done_reason"] == "stop"
        validate_profile(r["profile"])
        assert json.loads(r["raw_response"]) == r["profile"]
        assert r["seed"] == 20261031 + r["replicate"] * 10000 + int(r["case_id"].split("_")[1]) - 1
        assert hashlib.sha256((protocol["system_prompt"] + r["user_prompt"]).encode()).hexdigest() == r["prompt_sha256"]
        grouped[r["case_id"]].append(r)
    for values in grouped.values():
        assert len(values) == 10 and len({r["prompt_sha256"] for r in values}) == 1
    units = {r["case_id"]: r for r in load_csv("per_unit_uncertainty.csv")}
    clusters = defaultdict(list)
    for r in load_csv("nli_cluster_assignments.csv"):
        clusters[r["case_id"]].append(int(r["nli_cluster"]))
    for case_id, values in grouped.items():
        labels = [r["profile"]["dominant_semantic"] for r in values]
        assert math.isclose(empirical_entropy(labels), float(units[case_id]["label_entropy_nats"]), abs_tol=1e-10)
        assert math.isclose(modal_consistency(labels), float(units[case_id]["label_consistency"]), abs_tol=1e-10)
        assert math.isclose(empirical_entropy(clusters[case_id]), float(units[case_id]["nli_entropy_nats"]), abs_tol=1e-10)
    shares = defaultdict(lambda: defaultdict(dict))
    for row in load_csv("prior_shares_by_replicate.csv"):
        shares[(row["city"], row["direction"])][row["replicate"]][row["case_id"]] = float(row["share"])
    for row in load_csv("prior_share_stability.csv"):
        by_rep = shares[(row["city"], row["direction"])]
        arrays = [[v[k] for k in sorted(v)] for _, v in sorted(by_rep.items())]
        assert len(arrays) == 10 and all(len(a) == 10 for a in arrays)
        assert all(math.isclose(sum(a), 1, abs_tol=1e-12) for a in arrays)
        comparisons = [cpc(a, b) for a, b in combinations(arrays, 2)]
        assert math.isclose(sum(comparisons) / len(comparisons), float(row["pairwise_prior_cpc_mean"]), abs_tol=1e-10)
    assert report["all_expected_valid"] and report["valid_samples"] == 400
    if (ROOT / "SHA256SUMS").exists():
        for line in (ROOT / "SHA256SUMS").read_text(encoding="ascii").splitlines():
            digest, path = line.split("  ", 1)
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    print("PASS: 400 raw responses, seed independence, fixed prompts, uncertainty metrics, prior comparisons and checksums.")


if __name__ == "__main__":
    main()
