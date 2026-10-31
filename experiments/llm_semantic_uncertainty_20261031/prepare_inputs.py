"""Select cases using exogenous information only; freeze downstream score inputs."""

from pathlib import Path
import hashlib
import json
import math
import sys

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_unified_prior_guided_neural_generator as neural

FEATURES = ["population", "population_density", "poi_amenity", "poi_shop", "poi_office",
            "poi_industrial", "poi_public_transport", "poi_railway", "poi_tourism", "poi_building"]
TARGETS = {"Baltimore-MPO": ("motor_vehicle", "motor_outflow", "motor_inflow"),
           "Chengdu-DIDI": ("ride_hailing", "demand", "response"),
           "Shanghai-MetroFlow": ("metro", "metro_out", "metro_in"),
           "Philadelphia-SEPTA": ("bus", "bus_tap_out", "bus_tap_in")}


def main():
    replacement = pd.read_csv(ROOT / "experiments/pa_cvae_4city_replacement_septa_20260824/data/external_features/septa_replacement_external_features.csv", dtype={"unit_id": str})
    source = {city: replacement[replacement.city_id == city].copy() for city in ["Baltimore-MPO", "Philadelphia-SEPTA"]}
    source["Chengdu-DIDI"] = pd.read_csv("D:/Python_Projects/datasets/chengdu_didi/grid_external_features.csv", dtype={"unit_id": str})
    source["Shanghai-MetroFlow"] = pd.read_csv("D:/Python_Projects/datasets/MetroFlow/MetroFlow/station_external_features.csv", dtype={"unit_id": str})
    cases = []
    for city, frame in sorted(source.items()):
        frame = frame.sort_values("unit_id").reset_index(drop=True)
        values = np.log1p(frame[FEATURES].apply(pd.to_numeric, errors="raise").clip(lower=0).to_numpy())
        spread = values.std(axis=0)
        scaled = (values - values.mean(axis=0)) / np.where(spread > 0, spread, 1)
        chosen = [int(np.argmin(np.square(scaled).sum(axis=1)))]
        for _ in range(9):
            distances = np.min(np.square(scaled[:, None, :] - scaled[chosen][None, :, :]).sum(axis=2), axis=1)
            distances[chosen] = -1
            chosen.append(int(np.argmax(distances)))
        lon_min, lon_max = frame.lon.min(), frame.lon.max()
        lat_min, lat_max = frame.lat.min(), frame.lat.max()
        for index in chosen:
            raw = frame.iloc[index].to_dict()
            external = {k: v for k, v in raw.items() if pd.notna(v)}
            x = float((raw["lon"] - lon_min) / (lon_max - lon_min))
            y = float((raw["lat"] - lat_min) / (lat_max - lat_min))
            centrality = max(0, 1 - math.hypot(x - 0.5, y - 0.5))
            central_factor = 1 + 0.05 * centrality
            mode, out_target, in_target = TARGETS[city]
            fixed = dict(external, production_multiplier=1.0, attraction_weight=1.0, free_flow_cost_factor=1.0)
            downstream = {"central_factor": central_factor, "target_out": out_target, "target_in": in_target}
            for direction, target in [("out", out_target), ("in", in_target)]:
                score = neural._exogenous_prior_unit_score(fixed, mode=mode, target_name=target, x=x, y=y)
                raw_score = math.expm1(score / central_factor)
                downstream["raw_" + direction] = raw_score
                check = neural._exogenous_prior_unit_score(dict(fixed, production_multiplier=1.4, attraction_weight=1.4, free_flow_cost_factor=1.1), mode=mode, target_name=target, x=x, y=y)
                derived = math.log1p(raw_score * 1.4) * central_factor * (1.1 ** -0.35)
                assert math.isclose(check, derived, rel_tol=1e-9)
            cases.append({"case_id": f"case_{len(cases) + 1:03d}", "city": city, "unit_id": str(raw["unit_id"]),
                "mode": mode, "evidence": {k: float(raw[k]) for k in FEATURES}, "downstream": downstream})
    (HERE / "inputs.json").write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
    manifest = {"cases": len(cases), "per_city": 10, "selection": "Deterministic farthest-point coverage in standardized log1p exogenous feature space; first point nearest feature-space mean.",
        "ground_truth_used": False, "employment_fields_used": False, "ontology_labels_exposed_to_llm": False,
        "downstream_scope": "Frozen exogenous prior score module, normalized over 10 selected units per city; no PA-CVAE retraining or GT accuracy comparison.",
        "project_score_function": "run_unified_prior_guided_neural_generator._exogenous_prior_unit_score",
        "project_score_source_sha256": hashlib.sha256((ROOT / "scripts/run_unified_prior_guided_neural_generator.py").read_bytes()).hexdigest()}
    (HERE / "input_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
