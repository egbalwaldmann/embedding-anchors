"""Shared paths, model registry and embedding cache."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"          # public data and cached vectors (git-ignored, reproducible)
# Private case-study data lives outside the repository (set EA_PRIVATE); never published.
PRIVATE = Path(os.environ.get("EA_PRIVATE", ROOT / "private"))
RESULTS = ROOT / "results"
SEED = 20261120

# Open models, all run locally through sentence-transformers.
# `q`/`d` are the prompts the model cards prescribe for queries and documents.
MODELS: dict[str, dict] = {
    "bge-m3": {"hf": "BAAI/bge-m3", "family": "XLM-R encoder", "q": "", "d": ""},
    "me5-large": {
        "hf": "intfloat/multilingual-e5-large",
        "family": "XLM-R encoder",
        "q": "query: ",
        "d": "passage: ",
    },
    "arctic-l-v2": {
        "hf": "Snowflake/snowflake-arctic-embed-l-v2.0",
        "family": "XLM-R encoder (bge-m3 retrofit)",
        "q": "query: ",
        "d": "",
    },
    "qwen3-0.6b": {
        "hf": "Qwen/Qwen3-Embedding-0.6B",
        "family": "decoder LLM",
        "q": "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery:",
        "d": "",
    },
    "embeddinggemma-2": {
        "hf": "google/embeddinggemma-2",
        "family": "Gemma encoder",
        "q": "task: search result | query: ",
        "d": "title: none | text: ",
    },
}


# An older and much weaker model, used only as the old side of an upgrade.
LEGACY: dict[str, dict] = {
    "minilm-l12": {
        "hf": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "family": "MiniLM (2019)",
        "q": "",
        "d": "",
    },
}
ALL = {**MODELS, **LEGACY}


def emb_path(testbed: str, model: str, part: str) -> Path:
    base = PRIVATE if testbed == "archive" else DATA
    return base / "emb" / testbed / f"{model}.{part}.npy"


def load_emb(testbed: str, model: str, part: str) -> np.ndarray:
    return np.load(emb_path(testbed, model, part))


def normalize(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return (x / n).astype(np.float32)


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf8") as f:
        return [json.loads(line) for line in f]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def device() -> str:
    import torch

    if os.environ.get("EA_DEVICE"):
        return os.environ["EA_DEVICE"]
    return "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
