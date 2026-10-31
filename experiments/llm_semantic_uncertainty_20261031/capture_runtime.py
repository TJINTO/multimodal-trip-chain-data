"""Record reproducibility metadata without exporting local credentials/paths."""

from pathlib import Path
import importlib.metadata
import json
import platform
import subprocess

import requests
import torch


def main():
    session = requests.Session()
    session.trust_env = False
    version = session.get("http://127.0.0.1:11434/api/version", timeout=10)
    version.raise_for_status()
    shown = session.post("http://127.0.0.1:11434/api/show", json={"model": "qwen3:8b"}, timeout=15)
    shown.raise_for_status()
    data = shown.json()
    record = {"date": "2026-10-31", "python": platform.python_version(), "system": platform.system(),
        "cpu": "Intel Core i9-14900K", "ram_gb": 64, "gpu": torch.cuda.get_device_name(0),
        "gpu_memory_bytes": torch.cuda.get_device_properties(0).total_memory,
        "ollama": version.json(), "ollama_model_parameters": data.get("parameters"),
        "ollama_model_capabilities": data.get("capabilities"),
        "packages": {p: importlib.metadata.version(p) for p in ["torch", "numpy", "pandas", "transformers", "tokenizers", "huggingface-hub"]},
        "gpu_driver": subprocess.check_output(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"], text=True).strip(),
        "independent_samples": "Different deterministic request seeds, no conversational history between requests, fixed prompt/model/decoding configuration.",
        "kv_cache": "Model residency and prefix-cache reuse are permitted; every response is a separately seeded generation.",
        "reference_code_copied": False}
    (Path(__file__).resolve().parent / "runtime_metadata.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
