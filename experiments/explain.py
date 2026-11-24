"""Numbers behind the explanatory figures, computed on the public testbed Wiki-de; writes results/explain.json.

    uv run python experiments/explain.py

  offset   how long the mean anchor vector of a space is, which is what centring removes
  spaces   sixty held-out anchors in two spaces, as the new model places them and as the map does
  damping  cosine between a query and its relevant passages, with the new model's vectors and with translated ones
  fit      orthogonal map against ridge regression on held-out anchors and on queries: closeness and neighbours
  tie      per-query differences between a translated index and the old model, and the resampled mean

Only vectors and relevance judgements are read. The file holds numbers and model names, no text.
"""
from __future__ import annotations

import json
import time
from itertools import permutations

import numpy as np

from adapters import procrustes, ridge
from common import LEGACY, RESULTS, SEED, emb_path, normalize
from evaluate import BOOT, DEPTH, Bed
from metrics import topk

NAME = "wiki-de"  # the public testbed; nothing else is read
PART = "anchors"
SHOWN = ("bge-m3", "me5-large")  # the pair that the single-pair panels show
CROSS = ("qwen3-0.6b", "me5-large")  # a pair across model families
# Index translation against the old model: clearly below, just below, and tied (see `stay_lo`, `stay_hi` in the results).
TIES = [CROSS, SHOWN, ("bge-m3", "arctic-l-v2")]
FITS = {"procrustes": procrustes, "ridge": ridge}
HELD, DOTS = 1000, 60  # anchors kept out of the fit for the picture of two spaces, and how many of them are drawn
FIT_N, TEST_N = 5000, 2000  # as in the `retrieval` rows of evaluate_extra.py
SAMPLE = 20000  # passages that the queries of the `fit` part are searched in
BINS = np.round(np.linspace(0.4, 1.0, 61), 2)


def rounded(x, digits: int = 4):
    return np.round(np.asarray(x, dtype=np.float64), digits).tolist()


def neighbours(Q: np.ndarray, D: np.ndarray, own: bool) -> np.ndarray:
    """The ten nearest rows of D for every row of Q; with `own`, row i of D is the item itself and is left out."""
    S = Q @ D.T
    if own:
        np.fill_diagonal(S, -np.inf)
    return np.argsort(-S, axis=1)[:, :10]


def shared(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean([len(set(x) & set(y)) / 10 for x, y in zip(a, b)]))


def plane(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Mean, first two principal axes and the share of the variance that they carry."""
    mean = X.mean(0)
    C = np.cov((X - mean).astype(np.float64), rowvar=False)
    values, vectors = np.linalg.eigh(C)
    axes = vectors[:, ::-1][:, :2]
    return mean, axes, float(values[::-1][:2].sum() / values.sum())


def main() -> None:
    t0 = time.time()
    bed = Bed(NAME)
    usable = bed.anchor_rows[PART]
    order = usable[np.random.default_rng(SEED).permutation(len(usable))]  # the nested order of evaluate.py
    anchors = lambda m: bed.emb(m, PART)
    out: dict = {"testbed": NAME, "seed": SEED}

    # 1. The mean of unit vectors: a length near one means that all vectors point the same way.
    out["offset"] = []
    for m in bed.open + list(LEGACY) + bed.doc_only:
        if not bed.has(m, PART):
            continue
        A = anchors(m)[usable]
        length = float(np.linalg.norm(A.mean(0, dtype=np.float64)))
        n = len(A)
        out["offset"].append({"space": m, "n": n, "length": round(length, 4), "mean_cos": round((n * length**2 - 1) / (n - 1), 4)})
    print("offset", [(r["space"], r["length"]) for r in out["offset"]], flush=True)

    # 2. The same anchors in two spaces, each drawn in the plane of its first two principal components.
    s, t = SHOWN
    fit, held = order[:-HELD], order[-HELD:]
    f = procrustes(anchors(s)[fit], anchors(t)[fit])
    ms, Ps, vs = plane(anchors(s)[fit])
    mt, Pt, vt = plane(anchors(t)[fit])
    # A principal axis has no sign of its own; the target's axes are turned so that they run with the source's.
    for j in range(2):
        if np.corrcoef((anchors(s)[fit] - ms) @ Ps[:, j], (anchors(t)[fit] - mt) @ Pt[:, j])[0, 1] < 0:
            Pt[:, j] = -Pt[:, j]
    agree = [float(np.corrcoef((anchors(s)[fit] - ms) @ Ps[:, j], (anchors(t)[fit] - mt) @ Pt[:, j])[0, 1]) for j in range(2)]
    true, mapped = anchors(t)[held], f(anchors(s)[held])
    gap = mapped - true
    spread = lambda V, centre: round(float(np.sqrt(((V - centre) ** 2).sum(1).mean())), 4)
    out["spaces"] = {
        "source": s, "target": t, "fit": int(len(fit)), "held": int(len(held)), "shown": DOTS,
        "variance_source": round(vs, 4), "variance_target": round(vt, 4), "axes_agree": rounded(agree, 3),
        "cos_held": round(float((mapped * true).sum(1).mean()), 4), "cos_shown": round(float((mapped * true)[:DOTS].sum(1).mean()), 4),
        # How much of the distance between a translated vector and its counterpart lies in the drawn plane.
        "gap_in_plane": round(float(((gap @ Pt) ** 2).sum() / (gap**2).sum()), 4),
        # Root mean square distance of the held-out anchors from the mean of their space: an orthogonal map keeps the source's.
        "spread": {"source": spread(anchors(s)[held], ms), "target": spread(true, mt), "translated": spread(mapped, mt)},
        "in_source": rounded((anchors(s)[held[:DOTS]] - ms) @ Ps), "in_target": rounded((true[:DOTS] - mt) @ Pt),
        "translated": rounded((mapped[:DOTS] - mt) @ Pt),
    }
    print("spaces", {k: v for k, v in out["spaces"].items() if not isinstance(v, list) or len(v) < 5}, flush=True)

    # Index translation with all anchors, as in the headline rows: translated corpora and per-query scores.
    translated: dict[tuple[str, str], np.ndarray] = {}
    for s, t in dict.fromkeys([SHOWN, CROSS] + TIES):
        translated[(s, t)] = procrustes(anchors(s)[order], anchors(t)[order])(bed.emb(s, "corpus"))

    # 3. A translated vector is less similar to the query than the vector the new model would have written.
    pages = np.array(bed.doc_keys)
    out["damping"] = []
    for s, t in (SHOWN, CROSS):
        Q = bed.emb(t, "queries")
        own, moved = Q @ bed.emb(t, "corpus").T, Q @ translated[(s, t)].T
        kept = {"relevant_native": [], "relevant_translated": [], "best_native": [], "best_translated": [], "rival_native": [], "rival_translated": []}
        for q, rel in enumerate(bed.qrels):
            hit = np.isin(pages, list(rel))
            kept["relevant_native"] += own[q, hit].tolist()
            kept["relevant_translated"] += moved[q, hit].tolist()
            kept["best_native"].append(own[q, hit].max())
            kept["best_translated"].append(moved[q, hit].max())
            kept["rival_native"].append(own[q, ~hit].max())  # the best passage of a page that is not relevant
            kept["rival_translated"].append(moved[q, ~hit].max())
        kept = {k: np.array(v) for k, v in kept.items()}
        assert all(BINS[0] <= v.min() and v.max() <= BINS[-1] for k, v in kept.items() if not k.startswith("relevant")), "bins too narrow"
        out["damping"].append({
            "source": s, "target": t, "k": int(len(order)), "queries": len(bed.qrels), "pairs": int(len(kept["relevant_native"])),
            "bins": BINS.tolist(),
            "counts": {k: np.histogram(np.clip(v, BINS[0], BINS[-1]), BINS)[0].tolist() for k, v in kept.items()},
            "mean": {k: round(float(v.mean()), 4) for k, v in kept.items()},
            # Queries whose best relevant passage is less similar than the best passage of another page in the new model's space.
            "below_rival": {"native": round(float((kept["best_native"] < kept["rival_native"]).mean()), 4),
                            "translated": round(float((kept["best_translated"] < kept["rival_native"]).mean()), 4)},
        })
        print("damping", s, t, out["damping"][-1]["mean"], out["damping"][-1]["below_rival"], flush=True)

    # 4. Closeness to the true vector and agreement on the neighbours, for the two linear maps.
    fit_n, test = order[:FIT_N], order[-TEST_N:]
    sample = np.sort(np.random.default_rng(SEED).permutation(len(bed.corpus))[:SAMPLE])
    out["fit"] = {"fit": FIT_N, "held": TEST_N, "queries": len(bed.queries), "passages": SAMPLE, "pairs": []}
    for s, t in permutations(bed.open, 2):
        T = anchors(t)[test]
        near = neighbours(T, T, own=True)
        Qs, Qt, P = bed.emb(s, "queries"), bed.emb(t, "queries"), bed.emb(t, "corpus")[sample]
        found = neighbours(Qt, P, own=False)
        for method, fit_map in FITS.items():
            g = fit_map(anchors(s)[fit_n], anchors(t)[fit_n])
            M, Mq = g(anchors(s)[test]), g(Qs)
            out["fit"]["pairs"].append({
                "source": s, "target": t, "adapter": method,
                "cos_anchors": round(float((M * T).sum(1).mean()), 4),
                # The translated vector searched among the true vectors of the other held-out anchors, and among the translated ones.
                "near_anchors": round(shared(neighbours(M, T, own=True), near), 4),
                "near_anchors_within": round(shared(neighbours(M, M, own=True), near), 4),
                "acc1": round(float(((M @ T.T).argmax(1) == np.arange(len(T))).mean()), 4),
                "cos_queries": round(float((Mq * Qt).sum(1).mean()), 4),
                "near_queries": round(shared(neighbours(Mq, P, own=False), found), 4),
            })
    for method in FITS:
        rows = [r for r in out["fit"]["pairs"] if r["adapter"] == method]
        print("fit", method, {k: round(float(np.mean([r[k] for r in rows])), 4) for k in rows[0] if k not in ("source", "target", "adapter")}, flush=True)

    # 5. What a tie is: the difference to the old model query by query, and the mean over resampled query sets.
    resample = np.random.default_rng(SEED).integers(0, len(bed.queries), (BOOT, len(bed.queries)))
    stay = {s: bed.judge(topk(bed.emb(s, "queries"), bed.emb(s, "corpus"), DEPTH))[1] for s in {s for s, _ in TIES}}
    out["tie"] = []
    for s, t in TIES:
        diff = bed.judge(topk(bed.emb(t, "queries"), translated[(s, t)], DEPTH))[1] - stay[s]
        boot = diff[resample].mean(1)
        edges = np.linspace(boot.min(), boot.max(), 41)
        out["tie"].append({
            "source": s, "target": t, "k": int(len(order)), "resamples": BOOT, "diff": rounded(diff, 5), "mean": float(diff.mean()),
            "lo": float(np.percentile(boot, 2.5)), "hi": float(np.percentile(boot, 97.5)),
            "edges": rounded(edges, 6), "counts": np.histogram(boot, edges)[0].tolist(),
        })
        print("tie", s, t, {k: round(out["tie"][-1][k], 5) for k in ("mean", "lo", "hi")}, flush=True)

    with open(RESULTS / "explain.json", "w", encoding="utf8") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print(f"done ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
