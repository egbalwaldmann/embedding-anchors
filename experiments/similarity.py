"""How alike are two spaces, judged from anchor embeddings alone?

    uv run python experiments/similarity.py <testbed>

For every pair of spaces with embeddings of the same anchor texts, computes
  rsa   Spearman correlation of the pairwise cosine similarities,
  cka   linear centred kernel alignment,
  knn   mean overlap of the 10 nearest anchors.
All three are invariant to rotation, so they can be read off published anchor
matrices before any map is fitted. Writes results/<testbed>.similarity[.<part>].jsonl.
"""
from __future__ import annotations

import json
import sys
from itertools import combinations

import numpy as np
from scipy.stats import spearmanr

from common import MODELS, RESULTS, SEED, emb_path, normalize
from metrics import topk

N = 2000


def cka(X: np.ndarray, Y: np.ndarray) -> float:
    X = X - X.mean(0)
    Y = Y - Y.mean(0)
    hsic = np.linalg.norm(X.T @ Y) ** 2
    return float(hsic / (np.linalg.norm(X.T @ X) * np.linalg.norm(Y.T @ Y)))


def main(testbed: str, part: str = "anchors") -> None:
    spaces = [m for m in list(MODELS) + ["cohere-v3", "gemini-001"] if emb_path(testbed, m, part).exists()]
    E = {m: normalize(np.load(emb_path(testbed, m, part)).astype(np.float32)) for m in spaces}
    n = min(len(v) for v in E.values())
    idx = np.random.default_rng(SEED).permutation(n)[:N]
    iu = np.triu_indices(len(idx), 1)
    rows = []
    for a, b in combinations(spaces, 2):
        A, B = E[a][idx], E[b][idx]
        rsa = float(spearmanr((A @ A.T)[iu], (B @ B.T)[iu]).statistic)
        ka, kb = topk(A, A, 11)[:, 1:], topk(B, B, 11)[:, 1:]
        knn = float(np.mean([len(set(x) & set(y)) / 10 for x, y in zip(ka, kb)]))
        rows.append({"testbed": testbed, "anchors": part, "a": a, "b": b, "rsa": rsa, "cka": cka(A, B), "knn": knn})
        print(rows[-1], flush=True)
    RESULTS.mkdir(exist_ok=True)
    suffix = "" if part == "anchors" else f".{part}"
    with open(RESULTS / f"{testbed}.similarity{suffix}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:])
