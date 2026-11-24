"""The result files of one testbed, read once and shared by the figures, tables and numbers of the paper."""
from __future__ import annotations

import json

import numpy as np

from common import MODELS, RESULTS, ROOT

PAPER = ROOT / "paper"
NAMES = {
    "bge-m3": "bge-m3",
    "me5-large": "mE5-large",
    "arctic-l-v2": "arctic-l-v2",
    "qwen3-0.6b": "Qwen3-0.6B",
    "embeddinggemma-2": "EmbGemma-2",
    "cohere-v3": "Cohere v3",
    "gemini-001": "Gemini-001",
}
BEDS = {"wiki-de": "Wiki-de", "miracl-de": "MIRACL-de", "archive": "Archive"}
FAMILY = {"bge-m3": "xlmr", "me5-large": "xlmr", "arctic-l-v2": "xlmr"}  # the other models stand alone
ALT = {"wiki-de": "english", "archive": "wikipedia"}
MAIN = "procrustes"  # the map the matrices, tables and predictions refer to
LABEL = {"procrustes": "orthogonal", "ridge": "ridge", "mlp": "residual network"}
WEAK = "minilm-l12"  # the much weaker old model


def load(name: str) -> list[dict]:
    path = RESULTS / name
    return [json.loads(line) for line in open(path)] if path.exists() else []


def mean(xs) -> float:
    xs = list(xs)
    return float(np.mean(xs)) if xs else float("nan")


class Bed:
    def __init__(self, name: str):
        self.name = name
        self.rows = load(f"{name}.jsonl")
        self.extra = load(f"{name}.extra.jsonl")
        self.native = {r["space"]: r for r in self.rows if r["kind"] == "native"}
        self.hybrid_native = {r["space"]: r for r in self.rows if r["kind"] == "hybrid-native"}
        self.bm25 = next((r for r in self.rows if r["kind"] == "bm25"), None)
        self.bridges = [r for r in self.rows if r["kind"] == "bridge"]
        self.hybrid_bridges = [r for r in self.rows if r["kind"] == "hybrid-bridge"]
        self.fidelity = [r for r in self.rows if r["kind"] == "fidelity"]
        self.open = [m for m in MODELS if m in self.native]
        self.sources = list(dict.fromkeys(r["source"] for r in self.bridges))
        self.closed = [s for s in self.sources if s not in self.open]
        self.sim = {}
        self.native_overlap = {(r["source"], r["target"]): r for r in self.rows if r["kind"] == "native-overlap"}
        self.tokens = {r["model"]: r for r in load("tokens.jsonl") if r["testbed"] == name}
        for part, label in [("", "in-domain"), (".anchors_en", "english"), (".anchors_wiki", "wikipedia")]:
            for r in load(f"{name}.similarity{part}.jsonl"):
                self.sim[(label, r["a"], r["b"])] = self.sim[(label, r["b"], r["a"])] = r

    def rel(self, r: dict, metric: str = "ndcg10") -> float:
        return r[metric] / self.native[r["target"]][metric]

    def stay(self, s: str, t: str, metric: str = "ndcg10") -> float:
        return self.native[s][metric] / self.native[t][metric]

    def pick(self, **want) -> list[dict]:
        return [r for r in self.bridges if all(r[k] == v for k, v in want.items())]

    def of(self, kind: str, **want) -> list[dict]:
        """Rows of the further measurements (evaluate_extra.py)."""
        return [r for r in self.extra if r["kind"] == kind and all(r[k] == v for k, v in want.items())]

    def kmax(self, anchors: str = "in-domain", adapter: str = MAIN) -> int:
        return max(r["k"] for r in self.bridges if r["anchors"] == anchors and r["adapter"] == adapter)

    def ks(self, anchors: str = "in-domain") -> list[int]:
        return sorted({r["k"] for r in self.bridges if r["anchors"] == anchors})

    def open_pair(self, r: dict) -> bool:
        return r["source"] in self.open

    def pairs(self) -> list[tuple[str, str]]:
        """The ordered pairs of open models, pairs within one family first."""
        every = [(s, t) for s in self.open for t in self.open if s != t]
        return [p for p in every if same_family(*p)] + [p for p in every if not same_family(*p)]


def same_family(s: str, t: str) -> bool:
    return FAMILY.get(s, s) == FAMILY.get(t, t)
