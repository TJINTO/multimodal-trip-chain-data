"""Run independent reproducible LLM samples; keep every response and failure."""

from pathlib import Path
import argparse
import hashlib
import json
import time

import requests

from metrics import LABELS, BOUNDS, validate_profile


HERE = Path(__file__).resolve().parent
EXPECTED_MODEL_DIGEST = "500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"
SYSTEM = """You infer transport-relevant urban area profiles from supplied exogenous evidence.
Use only the supplied population, population density and POI counts. Do not infer passenger counts, OD flows or accuracy metrics.
Return one JSON object. dominant_semantic must be one of the schema categories.
production_multiplier and attraction_weight describe relative trip-generating and trip-attracting propensity, centered on 1, bounded 0.5 to 2.
free_flow_cost_factor describes relative access friction, centered on 1, bounded 0.8 to 1.2; smaller means easier access.
Counts without detailed land-use evidence can support mixed_activity. Do not treat missing employment data as zero jobs.
summary must be a single English sentence of at most 25 words describing the area's dominant function and transport role. Do not state coefficients or passenger totals in summary.
Do not provide hidden reasoning. Return the requested object only."""
SCHEMA = {"type": "object", "properties": {
    "dominant_semantic": {"type": "string", "enum": LABELS},
    **{k: {"type": "number", "minimum": lo, "maximum": hi} for k, (lo, hi) in BOUNDS.items()},
    "summary": {"type": "string"}},
    "required": ["dominant_semantic", *BOUNDS, "summary"], "additionalProperties": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="chatgpt5.5")
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--limit-cases", type=int)
    parser.add_argument("--output", default="raw_samples.jsonl")
    args = parser.parse_args()
    cases = json.loads((HERE / "inputs.json").read_text(encoding="utf-8"))
    if args.limit_cases:
        cases = cases[:args.limit_cases]
    session = requests.Session()
    session.trust_env = False
    tags = session.get("http://127.0.0.1:11434/api/tags", timeout=10).json()
    model = next(m for m in tags["models"] if m["name"] == args.model)
    if model["digest"] != EXPECTED_MODEL_DIGEST:
        raise RuntimeError("Model digest differs from the measured experiment")
    protocol = {"model": args.model, "model_digest": model["digest"], "model_details": model["details"],
        "repeats": args.repeats, "cases": len(cases), "temperature": 0.7, "top_p": 0.9,
        "top_k": 20, "repeat_penalty": 1.0,
        "inherited_defaults_note": "Recorded run inherited top_k=20 and repeat_penalty=1 from the model manifest; made explicit in the replay script.",
        "num_predict": 220, "num_ctx": 4096, "think": False, "seed_rule": "20261031 + replicate_index*10000 + case_index; both zero-based",
        "system_prompt": SYSTEM, "format": SCHEMA, "raw_logits_available": False,
        "no_retry_on_invalid_output": True, "source_reference": "https://github.com/trohit920/llm-uncertainty-quantification"}
    (HERE / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    output = HERE / args.output
    saved = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()] if output.exists() else []
    existing = {(r["case_id"], r["replicate"]) for r in saved}
    for replicate in range(args.repeats):
        for case_index, case in enumerate(cases):
            key = (case["case_id"], replicate)
            if key in existing:
                continue
            seed = 20261031 + replicate * 10000 + case_index
            user = json.dumps({"city": case["city"], "primary_mode_context": case["mode"], "period": "daily_24h", "evidence": case["evidence"]}, sort_keys=True)
            payload = {"model": args.model, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                "stream": False, "think": False, "format": SCHEMA, "keep_alive": "30m",
                "options": {"seed": seed, "temperature": 0.7, "top_p": 0.9, "top_k": 20, "repeat_penalty": 1.0, "num_predict": 220, "num_ctx": 4096}}
            record = {"case_id": case["case_id"], "city": case["city"], "replicate": replicate, "seed": seed,
                "user_prompt": user, "prompt_sha256": hashlib.sha256((SYSTEM + user).encode()).hexdigest()}
            started = time.perf_counter()
            try:
                response = session.post("http://127.0.0.1:11434/api/chat", json=payload, timeout=180)
                response.raise_for_status()
                data = response.json()
                record["raw_response"] = data["message"]["content"]
                record["response_metadata"] = {k: data.get(k) for k in ["model", "created_at", "done_reason", "eval_count", "prompt_eval_count", "total_duration", "load_duration", "eval_duration"]}
                if data.get("done_reason") != "stop":
                    raise ValueError("Generation did not finish normally: " + str(data.get("done_reason")))
                record["profile"] = validate_profile(json.loads(record["raw_response"]))
                record["valid"] = True
            except Exception as exc:
                record["valid"] = False
                record["error"] = type(exc).__name__ + ": " + str(exc)
            record["wall_seconds"] = time.perf_counter() - started
            with output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"replicate={replicate + 1}/{args.repeats} case={case['case_id']} valid={record['valid']} seconds={record['wall_seconds']:.2f}", flush=True)


if __name__ == "__main__":
    main()
