"""Generate the report and checksums directly from recorded measurements."""

from pathlib import Path
import hashlib
import json

import pandas as pd


HERE = Path(__file__).resolve().parent


def main():
    result = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    city = pd.read_csv(HERE / "city_uncertainty_summary.csv")
    prior = pd.read_csv(HERE / "prior_share_stability.csv")
    summary = result["summary_across_units"]
    rows = ["# Repeated LLM Semantic-Profile Experiment", "", "Measured on 31 October 2026.", "",
        "## Design", "",
        "Forty spatial units were selected, ten each from Baltimore-MPO, Chengdu-DIDI, Shanghai-MetroFlow and Philadelphia-SEPTA. Selection used deterministic farthest-point coverage in standardized log-transformed population/POI feature space, without target traffic observations. Units cover feature diversity; they are not a population-representative random sample.", "",
        "Each fixed input was submitted ten times to local **Qwen3-8B (Q4_K_M)** through Ollama, yielding 400 separately seeded generations. Temperature=0.7, top-p=0.9, top-k=20, repeat penalty=1, context limit=4096 and maximum generated tokens=220. Thinking was disabled. Request seed=20261031 + 10000×replicate_index + case_index, with zero-based indices. Prompts, model digest and decoding settings are saved. Model residency/prefix caching was allowed, but no prior answers or dialogue were supplied to subsequent requests.", "",
        "The LLM returned a categorical function label, a short English semantic summary, and three bounded coefficients: production multiplier and attraction weight in [0.5, 2.0], access-cost factor in [0.8, 1.2]. Input evidence excludes employment fields, existing semantic labels, target flows and accuracy metrics. All 400 responses passed validation; no samples were replaced or excluded for their uncertainty.", "",
        "## Metrics", "",
        "- Label entropy: H = −Σ p(c) ln p(c), where c is a structured functional category. Units: nats.",
        "- Label consistency: fraction of samples in the most frequent functional category.",
        "- NLI semantic entropy/consistency: apply the same statistics after bidirectional-entailment clustering of the English summaries using cross-encoder/nli-deberta-v3-small. Entailment is determined from the model-config label index, not a hard-coded class number. A summary joins the first representative cluster only if entailment is predicted in both directions; replicate order is fixed. Greedy clustering can be order-dependent.",
        "- Coefficient CV: per-unit sample standard deviation (ddof=1) divided by the ten-sample mean.",
        "- Prior stability: inject each replicate's coefficients into the existing, frozen exogenous-prior score transformation; normalize over the ten selected units of each city and direction; compare all 45 replicate pairs using CPC. This CPC measures **agreement between generated priors**, not accuracy against observed traffic.", "",
        "Ollama does not expose raw generation logits here. Token entropy and likelihood-weighted semantic entropy are not reported. The procedure was inspired by [trohit920/llm-uncertainty-quantification](https://github.com/trohit920/llm-uncertainty-quantification); no source code from that repository was copied.", "",
        "## Results", "",
        "Values below are means over ten units per city. Detailed standard deviations are provided in city_uncertainty_summary.csv; per-unit values are in per_unit_uncertainty.csv.", "",
        "| City | Label entropy / nats | Label consistency | NLI entropy / nats | NLI consistency | Production CV | Attraction CV | Access-cost CV |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for _, r in city.iterrows():
        rows.append(f"| {r.city} | {r.label_entropy_nats_mean:.3f} | {r.label_consistency_mean:.1%} | {r.nli_entropy_nats_mean:.3f} | {r.nli_consistency_mean:.1%} | {r.production_multiplier_cv_mean:.2%} | {r.attraction_weight_cv_mean:.2%} | {r.free_flow_cost_factor_cv_mean:.2%} |")
    rows += ["", f"Across all 40 units, label entropy was {summary['label_entropy_nats']['mean']:.3f} ± {summary['label_entropy_nats']['std']:.3f} nats and label consistency was {summary['label_consistency']['mean']:.1%}. NLI semantic entropy was {summary['nli_entropy_nats']['mean']:.3f} ± {summary['nli_entropy_nats']['std']:.3f} nats, with mean semantic consistency {summary['nli_consistency']['mean']:.1%}. The ± values are between-unit sample standard deviations, not standard errors or calibrated uncertainty intervals.", "",
        "| City | Direction | Mean pairwise prior CPC | SD across 45 pairs | Minimum pairwise CPC | Mean unit share CV |",
        "| --- | --- | ---: | ---: | ---: | ---: |"]
    for _, r in prior.iterrows():
        rows.append(f"| {r.city} | {r.direction} | {r.pairwise_prior_cpc_mean:.4f} | {r.pairwise_prior_cpc_std:.4f} | {r.pairwise_prior_cpc_min:.4f} | {r.mean_unit_share_cv:.2%} |")
    rows += ["", "The 45 pairwise comparisons share replicates and are not 45 independent experimental runs. Direction out/in refers to the frozen prior module's production/attraction targets; Chengdu retains its demand/response semantics.", "",
        "## Interpretation", "",
        "Structured function labels were more consistent than full free-text meanings under the NLI criterion. The NLI results do not support claiming that all semantic variation is superficial or that semantic entropy is negligible. Shanghai showed the largest attraction-coefficient variation and lower label agreement. Numerical propagation through the frozen prior transform was more stable than the coefficients themselves, with mean pairwise CPC from " + f"{prior.pairwise_prior_cpc_mean.min():.4f} to {prior.pairwise_prior_cpc_mean.max():.4f}. This is compatible with damping by the logarithmic prior transformation and share normalization.", "",
        "This supplementary study measures repeated Qwen3-8B profile elicitation and its propagation to the prior interface. The original project uses deterministic transforms of a fixed LLM-authored ontology; it does not resample an LLM on every prediction. The experiment is not a rerun of the original ontology-creation model, not an end-to-end PA-CVAE replication, not a full-city demand benchmark, and not evidence of empirical traffic accuracy. No high-entropy unit was dropped, and no low-entropy result was assumed in advance. Agreement alone does not establish correctness.", "",
        "## Hardware and Cost", "",
        f"Intel Core i9-14900K, 64 GB RAM, NVIDIA RTX 4090 (24 GB). The 400 warmed-model requests took {result['sampling_wall_seconds']:.2f} s in total. NLI analysis and aggregation took {result['analysis_seconds']:.2f} s. These times exclude software installation, model download, initial model warm-up and pilot requests. Runtime versions and model identifiers are in runtime_metadata.json and protocol.json.", "",
        "## Reproduction", "",
        "1. Download this experiment directory, including inputs.json and protocol.json.",
        "2. Install the recorded dependencies and ensure Ollama is serving the same qwen3:8b model digest. The recorded quantization, schema and decoding controls matter.",
        "3. Run `python sample_profiles.py --output independent_samples.jsonl`. This uses a new output filename; existing saved request keys are otherwise reused to resume a run.",
        "4. Run `python analyze.py --samples independent_samples.jsonl` with CUDA PyTorch and the specified NLI checkpoint. This writes fresh summary files in the working experiment directory; use a separate copy to retain the published results.",
        "5. Run `python -m pytest test_metrics.py -q` for metric and validation checks.", "",
        "inputs.json contains the exact exogenous evidence and frozen numerical downstream bases used here. prepare_inputs.py documents the original case-selection process and expects the source project/datasets; replaying the published 40 inputs does not require those complete datasets. No model weights, credentials, true passenger records or target GT are included. Floating-point and backend differences can affect exact regeneration across versions.", "",
        "## Files", "",
        "- raw_samples.jsonl: all 400 raw model responses, seeds, prompt hashes, validation flags and timing receipts.",
        "- sampled_profiles.csv: structured profiles, including text summaries, without hiding their numeric variation.",
        "- nli_cluster_assignments.csv and nli_directed_entailment_scores.csv: cluster assignment and directed classifier evidence.",
        "- per_unit_uncertainty.csv and city_uncertainty_summary.csv: uncertainty metrics at both aggregation levels.",
        "- prior_shares_by_replicate.csv and prior_share_stability.csv: numerical propagation and pairwise prior agreement.",
        "- results.json, protocol.json, input_manifest.json and runtime_metadata.json: machine-readable summary and reproducibility metadata.", ""]
    (HERE / "README.md").write_text("\n".join(rows), encoding="utf-8")
    excerpt = (
        "为评估语义画像生成的随机性，本文从巴尔的摩、成都、上海和费城各选取10个空间单元，"
        "仅依据外生人口、POI及交通供给相关特征进行选择，并对每个固定输入采用Qwen3-8B进行10次独立种子采样。"
        "采样温度设为0.7，top-p设为0.9，共获得400份有效画像。"
        f"结构化功能标签的一致率为{summary['label_consistency']['mean']:.1%}，"
        f"基于双向蕴涵聚类的语义熵为{summary['nli_entropy_nats']['mean']:.3f}±{summary['nli_entropy_nats']['std']:.3f} nats，"
        "表明自由文本语义仍存在一定波动。发生系数、吸引系数和接入成本系数的平均变异系数分别为"
        f"{summary['production_multiplier_cv']['mean']:.2%}、{summary['attraction_weight_cv']['mean']:.2%}和{summary['free_flow_cost_factor_cv']['mean']:.2%}。"
        "将各次采样系数输入固定的外生先验计算模块后，各城市两方向的重复输出间平均CPC为"
        f"{prior.pairwise_prior_cpc_mean.min():.4f}—{prior.pairwise_prior_cpc_mean.max():.4f}。"
        "这说明数值变换与归一化可在一定程度上减弱画像参数波动对先验份额的影响；"
        "其中上海吸引系数的波动较大，需保留相应的不确定性说明。"
        "该CPC用于衡量重复输出的一致性，评价范围为所选空间单元的先验接口，不等同于对真实流量的预测精度或PA-CVAE端到端稳定性。\n"
    )
    (HERE / "manuscript_excerpt_zh.md").write_text(excerpt, encoding="utf-8")
    print(excerpt)


if __name__ == "__main__":
    main()
