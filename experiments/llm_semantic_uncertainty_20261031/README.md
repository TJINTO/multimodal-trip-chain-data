# Repeated LLM Semantic-Profile Experiment

Measured on 31 October 2026.

## Design

Forty spatial units were selected, ten each from Baltimore-MPO, Chengdu-DIDI, Shanghai-MetroFlow and Philadelphia-SEPTA. Selection used deterministic farthest-point coverage in standardized log-transformed population/POI feature space, without target traffic observations. Units cover feature diversity; they are not a population-representative random sample.

Each fixed input was submitted ten times to local **Qwen3-8B (Q4_K_M)** through Ollama, yielding 400 separately seeded generations. Temperature=0.7, top-p=0.9, top-k=20, repeat penalty=1, context limit=4096 and maximum generated tokens=220. Thinking was disabled. Request seed=20261031 + 10000×replicate_index + case_index, with zero-based indices. Prompts, model digest and decoding settings are saved. Model residency/prefix caching was allowed, but no prior answers or dialogue were supplied to subsequent requests.

The LLM returned a categorical function label, a short English semantic summary, and three bounded coefficients: production multiplier and attraction weight in [0.5, 2.0], access-cost factor in [0.8, 1.2]. Input evidence excludes employment fields, existing semantic labels, target flows and accuracy metrics. All 400 responses passed validation; no samples were replaced or excluded for their uncertainty.

## Metrics

- Label entropy: H = −Σ p(c) ln p(c), where c is a structured functional category. Units: nats.
- Label consistency: fraction of samples in the most frequent functional category.
- NLI semantic entropy/consistency: apply the same statistics after bidirectional-entailment clustering of the English summaries using cross-encoder/nli-deberta-v3-small. Entailment is determined from the model-config label index, not a hard-coded class number. A summary joins the first representative cluster only if entailment is predicted in both directions; replicate order is fixed. Greedy clustering can be order-dependent.
- Coefficient CV: per-unit sample standard deviation (ddof=1) divided by the ten-sample mean.
- Prior stability: inject each replicate's coefficients into the existing, frozen exogenous-prior score transformation; normalize over the ten selected units of each city and direction; compare all 45 replicate pairs using CPC. This CPC measures **agreement between generated priors**, not accuracy against observed traffic.

Ollama does not expose raw generation logits here. Token entropy and likelihood-weighted semantic entropy are not reported. The procedure was inspired by [trohit920/llm-uncertainty-quantification](https://github.com/trohit920/llm-uncertainty-quantification); no source code from that repository was copied.

## Results

Values below are means over ten units per city. Detailed standard deviations are provided in city_uncertainty_summary.csv; per-unit values are in per_unit_uncertainty.csv.

| City | Label entropy / nats | Label consistency | NLI entropy / nats | NLI consistency | Production CV | Attraction CV | Access-cost CV |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baltimore-MPO | 0.208 | 92.0% | 1.339 | 46.0% | 6.86% | 5.82% | 2.93% |
| Chengdu-DIDI | 0.000 | 100.0% | 1.498 | 41.0% | 4.73% | 2.10% | 2.44% |
| Philadelphia-SEPTA | 0.305 | 87.0% | 1.708 | 32.0% | 5.98% | 9.27% | 3.24% |
| Shanghai-MetroFlow | 0.724 | 63.0% | 1.164 | 53.0% | 7.96% | 24.81% | 9.05% |

Across all 40 units, label entropy was 0.309 ± 0.376 nats and label consistency was 85.5%. NLI semantic entropy was 1.427 ± 0.391 nats, with mean semantic consistency 43.0%. The ± values are between-unit sample standard deviations, not standard errors or calibrated uncertainty intervals.

| City | Direction | Mean pairwise prior CPC | SD across 45 pairs | Minimum pairwise CPC | Mean unit share CV |
| --- | --- | ---: | ---: | ---: | ---: |
| Baltimore-MPO | out | 0.9897 | 0.0046 | 0.9787 | 1.99% |
| Baltimore-MPO | in | 0.9916 | 0.0057 | 0.9791 | 1.77% |
| Chengdu-DIDI | out | 0.9913 | 0.0036 | 0.9822 | 1.52% |
| Chengdu-DIDI | in | 0.9906 | 0.0050 | 0.9804 | 1.52% |
| Philadelphia-SEPTA | out | 0.9889 | 0.0036 | 0.9804 | 1.87% |
| Philadelphia-SEPTA | in | 0.9833 | 0.0071 | 0.9657 | 2.83% |
| Shanghai-MetroFlow | out | 0.9802 | 0.0060 | 0.9669 | 3.55% |
| Shanghai-MetroFlow | in | 0.9690 | 0.0073 | 0.9528 | 5.30% |

The 45 pairwise comparisons share replicates and are not 45 independent experimental runs. Direction out/in refers to the frozen prior module's production/attraction targets; Chengdu retains its demand/response semantics.

## Interpretation

Structured function labels were more consistent than full free-text meanings under the NLI criterion. The NLI results do not support claiming that all semantic variation is superficial or that semantic entropy is negligible. Shanghai showed the largest attraction-coefficient variation and lower label agreement. Numerical propagation through the frozen prior transform was more stable than the coefficients themselves, with mean pairwise CPC from 0.9690 to 0.9916. This is compatible with damping by the logarithmic prior transformation and share normalization.

This supplementary study measures repeated Qwen3-8B profile elicitation and its propagation to the prior interface. The original project uses deterministic transforms of a fixed LLM-authored ontology; it does not resample an LLM on every prediction. The experiment is not a rerun of the original ontology-creation model, not an end-to-end PA-CVAE replication, not a full-city demand benchmark, and not evidence of empirical traffic accuracy. No high-entropy unit was dropped, and no low-entropy result was assumed in advance. Agreement alone does not establish correctness.

## Hardware and Cost

Intel Core i9-14900K, 64 GB RAM, NVIDIA RTX 4090 (24 GB). The 400 warmed-model requests took 213.81 s in total. NLI analysis and aggregation took 9.07 s. These times exclude software installation, model download, initial model warm-up and pilot requests. Runtime versions and model identifiers are in runtime_metadata.json and protocol.json.

## Reproduction

1. Download this experiment directory, including inputs.json and protocol.json.
2. Install the recorded dependencies and ensure Ollama is serving the same qwen3:8b model digest. The recorded quantization, schema and decoding controls matter.
3. Run `python sample_profiles.py --output independent_samples.jsonl`. This uses a new output filename; existing saved request keys are otherwise reused to resume a run.
4. Run `python analyze.py --samples independent_samples.jsonl` with CUDA PyTorch and the specified NLI checkpoint. This writes fresh summary files in the working experiment directory; use a separate copy to retain the published results.
5. Run `python -m pytest test_metrics.py -q` for metric and validation checks.

inputs.json contains the exact exogenous evidence and frozen numerical downstream bases used here. prepare_inputs.py documents the original case-selection process and expects the source project/datasets; replaying the published 40 inputs does not require those complete datasets. No model weights, credentials, true passenger records or target GT are included. Floating-point and backend differences can affect exact regeneration across versions.

## Files

- raw_samples.jsonl: all 400 raw model responses, seeds, prompt hashes, validation flags and timing receipts.
- sampled_profiles.csv: structured profiles, including text summaries, without hiding their numeric variation.
- nli_cluster_assignments.csv and nli_directed_entailment_scores.csv: cluster assignment and directed classifier evidence.
- per_unit_uncertainty.csv and city_uncertainty_summary.csv: uncertainty metrics at both aggregation levels.
- prior_shares_by_replicate.csv and prior_share_stability.csv: numerical propagation and pairwise prior agreement.
- results.json, protocol.json, input_manifest.json and runtime_metadata.json: machine-readable summary and reproducibility metadata.
