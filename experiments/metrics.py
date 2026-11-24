"""Exact cosine retrieval and ranking metrics."""
from __future__ import annotations

import math

import numpy as np
import torch


def topk(Q: np.ndarray, D: np.ndarray, k: int = 100) -> np.ndarray:
    """Indices of the k most similar documents for every query (vectors are unit length)."""
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    Dt = torch.tensor(D, device=dev)
    out = []
    for i in range(0, len(Q), 256):
        s = torch.tensor(Q[i : i + 256], device=dev) @ Dt.T
        out.append(torch.topk(s, k, dim=1).indices.cpu().numpy())
    return np.concatenate(out)


def collapse(ranked_ids: list[str], group) -> list[str]:
    """Rank groups (e.g. pages) by their best passage."""
    seen, out = set(), []
    for x in ranked_ids:
        g = group(x)
        if g not in seen:
            seen.add(g)
            out.append(g)
    return out


def ndcg(ranked: list[str], rel: dict[str, int], k: int = 10) -> float:
    dcg = sum((2 ** rel.get(d, 0) - 1) / math.log2(i + 2) for i, d in enumerate(ranked[:k]))
    ideal = sorted(rel.values(), reverse=True)[:k]
    idcg = sum((2**r - 1) / math.log2(i + 2) for i, r in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0


def recall(ranked: list[str], rel: dict[str, int], k: int) -> float:
    pos = {d for d, r in rel.items() if r > 0}
    return len(pos & set(ranked[:k])) / len(pos) if pos else 0.0


def overlap(a: np.ndarray, b: np.ndarray, k: int = 10) -> float:
    """Mean share of b's top-k that also appears in a's top-k."""
    return float(np.mean([len(set(x[:k]) & set(y[:k])) / k for x, y in zip(a, b)]))


def rrf(rankings: list[list[int]], k: int = 60, depth: int = 100) -> list[int]:
    score: dict[int, float] = {}
    for r in rankings:
        for i, d in enumerate(r[:depth]):
            score[d] = score.get(d, 0.0) + 1.0 / (k + i + 1)
    return sorted(score, key=score.get, reverse=True)
