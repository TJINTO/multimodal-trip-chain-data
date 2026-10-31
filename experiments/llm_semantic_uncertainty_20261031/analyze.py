"""Analyze all sampled profiles, NLI meanings and fixed-prior propagation."""

from collections import defaultdict
from itertools import combinations
from pathlib import Path
import argparse
import hashlib
import json
import math
import time

import numpy as np
import pandas as pd
import torch

from metrics import BOUNDS, cpc, empirical_entropy, modal_consistency, cluster_from_entailments


HERE = Path(__file__).resolve().parent
NLI_MODEL = "cross-encoder/nli-deberta-v3-small"
NLI_REVISION = "fa2804872c3b4bd748f38c0185cc85775361e735"


def load_nli():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL, revision=NLI_REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL, revision=NLI_REVISION).to("cuda").eval()
    index = next(int(i) for i, name in model.config.id2label.items() if name.lower() == "entailment")
    return tokenizer, model, index


def nli_cluster(case, records, tokenizer, model, entailment):
    answers = [r["profile"]["summary"].strip() for r in records]
    unique = list(dict.fromkeys(answers))
    lookup = {a: i for i, a in enumerate(unique)}
    pairs = [(i, j) for i in range(len(unique)) for j in range(len(unique)) if i != j]
    question = f"What urban function and transport role does this {case['city']} area have? "
    directed = {}
    entailment_rows = []
    with torch.inference_mode():
        for start in range(0, len(pairs), 32):
            block = pairs[start:start + 32]
            encoded = tokenizer([question + unique[i] for i, _ in block],
                [question + unique[j] for _, j in block], padding=True, truncation=True,
                max_length=256, return_tensors="pt").to("cuda")
            probs = torch.softmax(model(**encoded).logits, dim=-1)
            winner = probs.argmax(-1).tolist()
            probability = probs[:, entailment].tolist()
            for (i, j), label, probability_value in zip(block, winner, probability):
                directed[(i, j)] = label == entailment
                entailment_rows.append({"case_id": case["case_id"], "left_unique": i,
                    "right_unique": j, "entailment_probability": probability_value,
                    "entails": label == entailment})
    assignment = cluster_from_entailments(len(unique), directed)
    labels = [assignment[lookup[a]] for a in answers]
    mapping = [{"case_id": case["case_id"], "replicate": r["replicate"], "summary": a,
        "unique_answer_index": lookup[a], "nli_cluster": label}
        for r, a, label in zip(records, answers, labels)]
    return labels, mapping, entailment_rows


def score(case, profile, direction):
    field = "production_multiplier" if direction == "out" else "attraction_weight"
    raw = case["downstream"]["raw_" + direction]
    cost = profile["free_flow_cost_factor"]
    access = max(0.75, min(1.25, cost ** -0.35))
    return math.log1p(raw * profile[field]) * case["downstream"]["central_factor"] * access


def mean_std(values):
    return {"mean": float(np.mean(values)), "std": float(np.std(values, ddof=1)) if len(values) > 1 else None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-nli", action="store_true")
    parser.add_argument("--samples", default="raw_samples.jsonl")
    args = parser.parse_args()
    started = time.perf_counter()
    torch.set_num_threads(4)
    torch.manual_seed(20261031)
    cases = json.loads((HERE / "inputs.json").read_text(encoding="utf-8"))
    protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    all_records = [json.loads(line) for line in (HERE / args.samples).read_text(encoding="utf-8").splitlines()]
    by_case = defaultdict(list)
    for row in all_records:
        by_case[row["case_id"]].append(row)
    tokenizer, model, entailment = load_nli() if not args.skip_nli else (None, None, None)
    unit_metrics, mappings, nli_scores, long_profiles = [], [], [], []
    for case in cases:
        records = sorted([r for r in by_case[case["case_id"]] if r["valid"]], key=lambda r: r["replicate"])
        if len(records) < 2:
            raise RuntimeError("Fewer than two valid samples: " + case["case_id"])
        categorical = [r["profile"]["dominant_semantic"] for r in records]
        lexical = [r["profile"]["summary"].strip() for r in records]
        row = {"case_id": case["case_id"], "city": case["city"], "unit_id": case["unit_id"],
            "n_valid": len(records), "label_entropy_nats": empirical_entropy(categorical),
            "label_consistency": modal_consistency(categorical), "lexical_entropy_nats": empirical_entropy(lexical)}
        if not args.skip_nli:
            clusters, mapping, scores = nli_cluster(case, records, tokenizer, model, entailment)
            mappings.extend(mapping)
            nli_scores.extend(scores)
            row.update(nli_entropy_nats=empirical_entropy(clusters), nli_consistency=modal_consistency(clusters),
                nli_cluster_count=len(set(clusters)))
        for field in BOUNDS:
            values = np.asarray([r["profile"][field] for r in records])
            row[field + "_mean"] = float(values.mean())
            row[field + "_std"] = float(values.std(ddof=1))
            row[field + "_cv"] = float(values.std(ddof=1) / values.mean())
        for r in records:
            long_profiles.append({"case_id": case["case_id"], "city": case["city"], "replicate": r["replicate"], **r["profile"]})
        unit_metrics.append(row)
        print("analyzed " + case["case_id"], flush=True)
    unit = pd.DataFrame(unit_metrics)
    unit.to_csv(HERE / "per_unit_uncertainty.csv", index=False)
    pd.DataFrame(long_profiles).to_csv(HERE / "sampled_profiles.csv", index=False)
    if not args.skip_nli:
        pd.DataFrame(mappings).to_csv(HERE / "nli_cluster_assignments.csv", index=False)
        pd.DataFrame(nli_scores).to_csv(HERE / "nli_directed_entailment_scores.csv", index=False)
    city_rows = []
    metric_names = ["label_entropy_nats", "label_consistency", "lexical_entropy_nats", *[k + "_cv" for k in BOUNDS]]
    if not args.skip_nli:
        metric_names += ["nli_entropy_nats", "nli_consistency", "nli_cluster_count"]
    for city, group in unit.groupby("city"):
        record = {"city": city, "units": len(group)}
        for metric in metric_names:
            for kind, value in mean_std(group[metric].tolist()).items():
                record[metric + "_" + kind] = value
        city_rows.append(record)
    pd.DataFrame(city_rows).to_csv(HERE / "city_uncertainty_summary.csv", index=False)

    prior_rows, share_rows = [], []
    for city in sorted(set(c["city"] for c in cases)):
        city_cases = [c for c in cases if c["city"] == city]
        for direction in ["out", "in"]:
            arrays = []
            for replicate in range(protocol["repeats"]):
                profiles = [next((r["profile"] for r in by_case[c["case_id"]] if r["valid"] and r["replicate"] == replicate), None) for c in city_cases]
                if any(p is None for p in profiles):
                    continue
                scores = np.asarray([score(c, p, direction) for c, p in zip(city_cases, profiles)])
                shares = scores / scores.sum()
                arrays.append(shares)
                share_rows.extend({"city": city, "direction": direction, "case_id": c["case_id"],
                    "replicate": replicate, "share": float(s)} for c, s in zip(city_cases, shares))
            values = [cpc(a.tolist(), b.tolist()) for a, b in combinations(arrays, 2)]
            matrix = np.asarray(arrays)
            prior_rows.append({"city": city, "direction": direction, "complete_replicates": len(arrays),
                "pairwise_prior_cpc_mean": float(np.mean(values)), "pairwise_prior_cpc_std": float(np.std(values, ddof=1)),
                "pairwise_prior_cpc_min": float(min(values)), "mean_unit_share_cv": float((matrix.std(axis=0, ddof=1) / matrix.mean(axis=0)).mean())})
    pd.DataFrame(prior_rows).to_csv(HERE / "prior_share_stability.csv", index=False)
    pd.DataFrame(share_rows).to_csv(HERE / "prior_shares_by_replicate.csv", index=False)
    report = {"valid_samples": sum(r["valid"] for r in all_records), "attempted_samples": len(all_records),
        "expected_samples": len(cases) * protocol["repeats"], "units": len(cases), "repeats": protocol["repeats"],
        "all_expected_valid": len(all_records) == len(cases) * protocol["repeats"] and all(r["valid"] for r in all_records),
        "summary_across_units": {m: mean_std(unit[m].tolist()) for m in metric_names},
        "nli_model": NLI_MODEL if model is not None else None,
        "nli_revision": getattr(model.config, "_commit_hash", None) if model is not None else None,
        "nli_id2label": model.config.id2label if model is not None else None,
        "nli_clustering": "Greedy first-representative clustering in replicate order; equivalent only if each summary entails the other; classifier argmax label.",
        "nli_order_dependence": "Greedy representative clustering can depend on sample order; assignments and directed scores are provided.",
        "raw_logits_available": False, "likelihood_weighted_entropy_computed": False,
        "sampling_wall_seconds": sum(r["wall_seconds"] for r in all_records),
        "analysis_seconds": time.perf_counter() - started,
        "metric_scope": "Empirical output consistency and fixed exogenous-prior sensitivity over selected units; not correctness, calibration, GT CPC, full-city or end-to-end PA-CVAE variance.",
        "reference": "https://github.com/trohit920/llm-uncertainty-quantification"}
    (HERE / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
