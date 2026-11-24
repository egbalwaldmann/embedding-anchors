"""Further measurements on top of evaluate.py; writes results/<testbed>.extra.jsonl.

    uv run python experiments/evaluate_extra.py <testbed>

  role       query translation with maps fitted on anchors in the query role
  uncentred  the orthogonal map without centring, both modes
  upgrade    an old, much weaker model (or a document-only space whose queries
             exist) as the source, against staying on it
  mixed      one index that holds translated and re-embedded vectors side by side
  seed       other random draws of the anchors
  hybrid     fusion with BM25 for further anchor sets and with a tuned weight
  retrieval  how often a mapped held-out anchor finds its own counterpart
  contrast   paired bootstrap intervals for the comparisons the paper draws

Everything uses the orthogonal map unless stated; anchors are in-domain unless stated.
"""
from __future__ import annotations

import json
import sys
import time
from itertools import permutations

import numpy as np

from adapters import procrustes, procrustes_uncentred, ridge
from common import LEGACY, RESULTS, SEED
from evaluate import BOOT, DEPTH, KS, Bed, bm25_ranks, fuse
from metrics import topk

SEEDS = [1, 2, 3, 4, 5]
SEED_KS = [1000, 5000]
SHARES = [0.1, 0.5, 0.9]
WEIGHTS = [0.2, 0.35, 0.5, 0.65, 0.8]  # weight of the dense ranking in the fusion
FITS = {"procrustes": procrustes, "ridge": ridge}


def weighted_fuse(dense: np.ndarray, lexical: np.ndarray, w: float, k: int = 60) -> np.ndarray:
    out = []
    for x, y in zip(dense, lexical):
        score: dict[int, float] = {}
        for i, d in enumerate(x[:DEPTH]):
            score[d] = score.get(d, 0.0) + w / (k + i + 1)
        for i, d in enumerate(y[:DEPTH]):
            score[d] = score.get(d, 0.0) + (1 - w) / (k + i + 1)
        out.append(sorted(score, key=score.get, reverse=True)[:DEPTH])
    return np.array(out)


def main(name: str) -> None:
    bed = Bed(name)
    legacy = [m for m in LEGACY if bed.has(m, "corpus") and bed.has(m, "queries")]
    bed.open = [m for m in bed.open if m not in LEGACY]
    rows: list[dict] = []
    emit = lambda **r: rows.append({"testbed": name, **r})
    nq = len(bed.queries)
    resample = np.random.default_rng(SEED).integers(0, nq, (BOOT, nq))
    fold = np.random.default_rng(SEED).permutation(nq) % 2

    def interval(diff: np.ndarray) -> dict:
        boot = diff[resample].mean(1)
        return dict(diff=float(diff.mean()), lo=float(np.percentile(boot, 2.5)), hi=float(np.percentile(boot, 97.5)))

    def anchors(model: str, part: str, role: str = "document") -> np.ndarray:
        """Anchor vectors in a role. Models without prompts have one set of vectors for both roles."""
        other = f"{part}@query"
        return bed.emb(model, other if role == "query" and bed.has(model, other) else part)

    def nested(part: str, seed: int = 0) -> np.ndarray:
        usable = bed.anchor_rows[part]
        return usable[np.random.default_rng(SEED + seed).permutation(len(usable))]

    native, per_query = {}, {}
    for m in bed.open + legacy + [m for m in bed.doc_only if bed.has(m, "queries")]:
        native[m] = topk(bed.emb(m, "queries"), bed.emb(m, "corpus"), DEPTH)
        means, per_query[m], _ = bed.judge(native[m])
        if m not in bed.open:
            emit(kind="upgrade-native", space=m, dim=int(bed.emb(m, "corpus").shape[1]), **means)
    bm25 = bm25_ranks(bed)
    bm25_q = bed.judge(bm25)[1]

    part = bed.anchor_sets["in-domain"]
    order = nested(part)
    kmax = max(k for k in KS if k <= len(order))
    ks = [k for k in KS if k <= len(order)]
    alt = next((label for label in bed.anchor_sets if label != "in-domain"), None)
    pairs = list(permutations(bed.open, 2))
    # Per-query nDCG@10 of the configurations that the contrasts compare, one array per pair.
    kept: dict[str, list[np.ndarray]] = {}
    keep = lambda key, arr: kept.setdefault(key, []).append(arr)
    t0 = time.time()

    for s, t in pairs:
        Ds, Dt, Qt = bed.emb(s, "corpus"), bed.emb(t, "corpus"), bed.emb(t, "queries")
        As, At = anchors(s, part), anchors(t, part)
        Aqs, Aqt = anchors(s, part, "query"), anchors(t, part, "query")
        common = dict(source=s, target=t)

        for k in ks:
            sel = order[:k]
            for method, fit in FITS.items():
                # Query translation: T queries into S, fitted on document-role or on query-role anchors.
                for role, (X, Y) in (("document", (At, As)), ("query", (Aqt, Aqs))):
                    g = fit(X[sel], Y[sel])
                    means, q, _ = bed.judge(topk(g(Qt), Ds, DEPTH))
                    emit(kind="role", role=role, adapter=method, k=k, **common, **means,
                         **{f"stay_{a}": b for a, b in interval(q - per_query[s]).items()})
                    if k == kmax:
                        keep(f"bwd.{method}.{role}", q)
            # The orthogonal map without centring.
            f, g = procrustes_uncentred(As[sel], At[sel]), procrustes_uncentred(At[sel], As[sel])
            emit(kind="uncentred", direction="forward", k=k, **common, **bed.score(topk(Qt, f(Ds), DEPTH)))
            emit(kind="uncentred", direction="backward", k=k, **common, **bed.score(topk(g(Qt), Ds, DEPTH)))

        # Headline configuration: index translation with all in-domain anchors.
        f = procrustes(As[order[:kmax]], At[order[:kmax]])
        Df = f(Ds)
        fwd = topk(Qt, Df, DEPTH)
        fwd_q = bed.judge(fwd)[1]
        keep("fwd", fwd_q)
        keep("native", per_query[t])

        # One index with translated and re-embedded vectors side by side.
        for share in SHARES:
            mask = np.random.default_rng(SEED).random(len(Ds)) < share
            ranked = topk(Qt, np.where(mask[:, None], Df, Dt), DEPTH)
            emit(kind="mixed", share=share, k=kmax, **common, **bed.score(ranked),
                 translated_in_top10=float(mask[ranked[:, :10]].mean()))

        # Other draws of the anchors.
        for seed in SEEDS:
            o = nested(part, seed)
            for k in [k for k in SEED_KS if k <= len(o)]:
                f2, g2 = procrustes(As[o[:k]], At[o[:k]]), procrustes(At[o[:k]], As[o[:k]])
                emit(kind="seed", seed=seed, k=k, direction="forward", **common, ndcg10=bed.score(topk(Qt, f2(Ds), DEPTH))["ndcg10"])
                emit(kind="seed", seed=seed, k=k, direction="backward", **common, ndcg10=bed.score(topk(g2(Qt), Ds, DEPTH))["ndcg10"])

        # Fusion with BM25: equal weights, and a weight chosen on the other half of the queries.
        def fusion(label: str, k: int, ranked: np.ndarray, alone: np.ndarray) -> None:
            fused_q = bed.judge(fuse(bm25, ranked))[1]
            per_w = np.stack([bed.judge(weighted_fuse(ranked, bm25, w))[1] for w in WEIGHTS])
            tuned = np.empty(nq)
            for half in (0, 1):
                tuned[fold == half] = per_w[per_w[:, fold != half].mean(1).argmax(), fold == half]
            emit(kind="hybrid", anchors=label, k=k, **common, bridge=float(alone.mean()), fused=float(fused_q.mean()),
                 tuned=float(tuned.mean()), fused_beats_bm25=bool(fused_q.mean() >= bm25_q.mean()),
                 tuned_beats_bm25=bool(tuned.mean() >= bm25_q.mean()))
            keep(f"fused.{label}.{k}", fused_q)
            keep(f"tuned.{label}.{k}", tuned)
            keep(f"bridge.{label}.{k}", alone)

        fusion("in-domain", kmax, fwd, fwd_q)
        if 1000 in ks:
            f1 = procrustes(As[order[:1000]], At[order[:1000]])
            r1 = topk(Qt, f1(Ds), DEPTH)
            fusion("in-domain", 1000, r1, bed.judge(r1)[1])
        if alt and bed.has(s, bed.anchor_sets[alt]) and bed.has(t, bed.anchor_sets[alt]):
            apart = bed.anchor_sets[alt]
            ao = nested(apart)
            for k in sorted({min(kmax, len(ao)), max(k for k in KS if k <= len(ao))}):
                fa = procrustes(anchors(s, apart)[ao[:k]], anchors(t, apart)[ao[:k]])
                ra = topk(Qt, fa(Ds), DEPTH)
                qa = bed.judge(ra)[1]
                fusion(alt, k, ra, qa)
                if k == min(kmax, len(ao)):
                    keep("fwd.alt", qa)
                    keep("fwd.same-k", fwd_q if k == kmax else bed.judge(topk(Qt, procrustes(As[order[:k]], At[order[:k]])(Ds), DEPTH))[1])
        print(f"{s} -> {t} done ({time.time() - t0:.0f}s)", flush=True)

    # A native index fused with BM25, with the tuned weight.
    for m in bed.open:
        per_w = np.stack([bed.judge(weighted_fuse(native[m], bm25, w))[1] for w in WEIGHTS])
        tuned = np.empty(nq)
        for half in (0, 1):
            tuned[fold == half] = per_w[per_w[:, fold != half].mean(1).argmax(), fold == half]
        emit(kind="hybrid-native", space=m, fused=float(bed.judge(fuse(bm25, native[m]))[1].mean()), tuned=float(tuned.mean()))

    # An old or document-only space with its own queries as the source: can a bridge beat staying on it?
    for s in [m for m in native if m not in bed.open]:
        Ds = bed.emb(s, "corpus")
        for t in bed.open:
            Dt, Qt = bed.emb(t, "corpus"), bed.emb(t, "queries")
            for label, apart in bed.anchor_sets.items():
                if not (bed.has(s, apart) and bed.has(t, apart)):
                    continue
                o = nested(apart)
                As, At = anchors(s, apart), anchors(t, apart)
                Aqs, Aqt = anchors(s, apart, "query"), anchors(t, apart, "query")
                for k in [k for k in KS if k <= len(o)]:
                    for method, fit in FITS.items():
                        f = fit(As[o[:k]], At[o[:k]])
                        g = fit(Aqt[o[:k]], Aqs[o[:k]]) if bed.has(s, f"{apart}@query") or s in LEGACY else fit(At[o[:k]], As[o[:k]])
                        for direction, ranked in (("forward", topk(Qt, f(Ds), DEPTH)), ("backward", topk(g(Qt), Ds, DEPTH))):
                            means, q, _ = bed.judge(ranked)
                            emit(kind="upgrade", source=s, target=t, anchors=label, adapter=method, k=k, direction=direction,
                                 **means, **{f"stay_{a}": b for a, b in interval(q - per_query[s]).items()})
                            if method == "procrustes" and label == "in-domain" and k == kmax and direction == "forward":
                                fq = bed.judge(fuse(bm25, ranked))[1]
                                emit(kind="upgrade-hybrid", source=s, target=t, k=k, bridge=float(q.mean()), fused=float(fq.mean()),
                                     stay=float(per_query[s].mean()), stay_fused=float(bed.judge(fuse(bm25, native[s]))[1].mean()))
            print(f"{s} -> {t} done ({time.time() - t0:.0f}s)", flush=True)

    # Held-out anchors: fit on 5,000, then ask how often a mapped anchor is nearest to its own counterpart.
    spaces = bed.open + bed.doc_only + legacy
    for label, apart in bed.anchor_sets.items():
        o = nested(apart)
        fit_n, test = o[: min(5000, len(o) - 2000)], o[-2000:]
        for s, t in permutations([m for m in spaces if bed.has(m, apart)], 2):
            if t not in bed.open:
                continue
            f = procrustes(anchors(s, apart)[fit_n], anchors(t, apart)[fit_n])
            hit = topk(f(anchors(s, apart)[test]), anchors(t, apart)[test], 1)[:, 0] == np.arange(len(test))
            emit(kind="retrieval", anchors=label, source=s, target=t, fit=int(len(fit_n)), acc1=float(hit.mean()))

    # Paired bootstrap over queries; every side is the mean over the ordered pairs of open models.
    mean = lambda key: np.mean(kept[key], axis=0)
    hk = kmax
    contrasts = {
        "index-vs-query-translation": ("fwd", "bwd.procrustes.document"),
        "query-role-vs-document-role.procrustes": ("bwd.procrustes.query", "bwd.procrustes.document"),
        "query-role-vs-document-role.ridge": ("bwd.ridge.query", "bwd.ridge.document"),
        "in-domain-vs-other-anchors": ("fwd.same-k", "fwd.alt"),
        "fused-vs-bridge": (f"fused.in-domain.{hk}", f"bridge.in-domain.{hk}"),
        "tuned-vs-fused": (f"tuned.in-domain.{hk}", f"fused.in-domain.{hk}"),
        "bridge-vs-native": ("fwd", "native"),
    }
    for label, (a, b) in contrasts.items():
        if a in kept and b in kept:
            emit(kind="contrast", name=label, a=float(mean(a).mean()), b=float(mean(b).mean()), **interval(mean(a) - mean(b)))
    for key in [k for k in kept if k.startswith(("fused.", "tuned.", "bridge."))]:
        emit(kind="contrast", name=f"{key}-vs-bm25", a=float(mean(key).mean()), b=float(bm25_q.mean()), **interval(mean(key) - bm25_q))

    with open(RESULTS / f"{name}.extra.jsonl", "w", encoding="utf8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print("rows", len(rows))


if __name__ == "__main__":
    main(sys.argv[1])
