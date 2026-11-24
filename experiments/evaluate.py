"""Run the migration experiments for one testbed and write results/<testbed>.jsonl.

    uv run python experiments/evaluate.py <testbed>

For every ordered pair (source space S = the old model whose document vectors
are stored, target space T = the new model) two ways of avoiding a re-embed are
measured, each with adapters fitted on k paired anchors:

  forward   translate the stored document vectors S -> T and search them with
            native T queries (the index is migrated once);
  backward  keep the S index and translate T queries T -> S at query time
            (the Drift-Adapter setting).

Reference points: `native` (full re-embed in T), and `stay` (keep using S for
documents and queries), where query vectors in S exist.
"""
from __future__ import annotations

import json
import sys
import time
from itertools import permutations

import numpy as np

from adapters import ADAPTERS
from common import DATA, MODELS, PRIVATE, RESULTS, SEED, emb_path, normalize, read_jsonl
from metrics import collapse, ndcg, overlap, recall, rrf, topk

KS = [100, 300, 1000, 3000, 5000, 10000, 20000]
MLP_KS = [3000, 20000]
HYBRID_KS = [1000, 5000, 20000]
DEPTH = 1000  # passages retrieved per query; deep enough to fill ten pages after collapsing
BOOT = 2000  # bootstrap resamples of the query set

TESTBEDS = {
    # name: (anchor sets, extra document-only spaces, key function name)
    "wiki-de": ({"in-domain": "anchors", "english": "anchors_en"}, ["cohere-v3"], "page"),
    "miracl-de": ({"in-domain": "anchors"}, [], "id"),
    "archive": ({"in-domain": "anchors", "wikipedia": "anchors_wiki"}, ["gemini-001"], "id"),
}


def cos(a: np.ndarray, b: np.ndarray) -> float:
    return float((normalize(a) * normalize(b)).sum(1).mean())


def shared(a: list[set], b: list[set]) -> float:
    """Mean share of b's top-ten keys that a's top ten contains."""
    return float(np.mean([len(x & y) / max(len(y), 1) for x, y in zip(a, b)]))


def key_fn(name: str):
    if name == "page":
        return lambda cid: cid.split("_")[1]
    return lambda cid: cid


class Bed:
    def __init__(self, name: str):
        self.name = name
        self.folder = (PRIVATE if name == "archive" else DATA) / name
        anchors, extra, key = TESTBEDS[name]
        self.anchor_sets = {
            label: part for label, part in anchors.items() if (self.folder / f"{part}.jsonl").exists()
        }
        self.key = key_fn(key)
        self.corpus = read_jsonl(self.folder / "corpus.jsonl")
        self.queries = read_jsonl(self.folder / "queries.jsonl")
        self.doc_keys = [self.key(r["id"]) for r in self.corpus]
        # Anchors must not be searched: rows whose passage also sits in the corpus are left out of every fit.
        ids = {r["id"] for r in self.corpus}
        self.anchor_rows = {
            part: np.array([i for i, r in enumerate(read_jsonl(self.folder / f"{part}.jsonl")) if r["id"] not in ids])
            for part in self.anchor_sets.values()
        }
        qrels_file = "qrels_pages.json" if key == "page" else "qrels.json"
        raw = json.load(open(self.folder / qrels_file))
        self.qrels = [
            ({p: 1 for p in raw[q["id"]]} if isinstance(raw[q["id"]], list) else raw[q["id"]]) for q in self.queries
        ]
        self.open = [m for m in MODELS if emb_path(name, m, "corpus").exists()]
        self.doc_only = [m for m in extra if emb_path(name, m, "corpus").exists()]
        self._cache: dict[tuple[str, str], np.ndarray] = {}

    def emb(self, model: str, part: str) -> np.ndarray:
        if (model, part) not in self._cache:
            # Stored vectors of a truncated space are not unit length; cosine search needs them to be.
            self._cache[(model, part)] = normalize(np.load(emb_path(self.name, model, part)))
        return self._cache[(model, part)]

    def has(self, model: str, part: str) -> bool:
        return emb_path(self.name, model, part).exists()

    def judge(self, ranked: np.ndarray) -> tuple[dict, np.ndarray, list[set]]:
        """Metrics for a (queries x depth) matrix of corpus indices, nDCG@10 per query, top-ten keys."""
        nd, r10, r100, top = [], [], [], []
        for row, rel in zip(ranked, self.qrels):
            keys = collapse([self.doc_keys[i] for i in row], lambda k: k)
            nd.append(ndcg(keys, rel, 10))
            r10.append(recall(keys, rel, 10))
            r100.append(recall(keys, rel, 100))
            top.append(set(keys[:10]))
        means = {"ndcg10": float(np.mean(nd)), "recall10": float(np.mean(r10)), "recall100": float(np.mean(r100))}
        return means, np.array(nd), top

    def score(self, ranked: np.ndarray) -> dict:
        return self.judge(ranked)[0]


def bm25_ranks(bed: Bed) -> np.ndarray:
    import bm25s
    import Stemmer

    stem = Stemmer.Stemmer("german")
    docs = bm25s.tokenize([r["text"] for r in bed.corpus], stopwords="de", stemmer=stem, show_progress=False)
    retriever = bm25s.BM25()
    retriever.index(docs, show_progress=False)
    q = bm25s.tokenize([r["text"] for r in bed.queries], stopwords="de", stemmer=stem, show_progress=False)
    ranks, _ = retriever.retrieve(q, k=DEPTH, show_progress=False)
    return np.asarray(ranks)


def fuse(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Reciprocal rank fusion of two rankings, query by query."""
    return np.array([rrf([list(x), list(y)], depth=DEPTH)[:DEPTH] for x, y in zip(a, b)])


def main(name: str) -> None:
    bed = Bed(name)
    out = RESULTS / f"{name}.jsonl"
    RESULTS.mkdir(exist_ok=True)
    rows: list[dict] = []

    def emit(**r):
        rows.append({"testbed": name, **r})

    emit(
        kind="testbed",
        corpus=len(bed.corpus),
        queries=len(bed.queries),
        groups=len(set(bed.doc_keys)),
        anchors={label: int(len(bed.anchor_rows[part])) for label, part in bed.anchor_sets.items()},
    )
    # Reference rankings: each open space searched natively.
    native = {m: topk(bed.emb(m, "queries"), bed.emb(m, "corpus"), DEPTH) for m in bed.open}
    judged = {m: bed.judge(native[m]) for m in bed.open}
    for m in bed.open:
        emit(kind="native", space=m, dim=int(bed.emb(m, "corpus").shape[1]), **judged[m][0])
    # How much do two models agree before any translation? The yardstick for a bridge's overlap.
    for s, t in permutations(bed.open, 2):
        emit(kind="native-overlap", source=s, target=t, overlap10=overlap(native[s], native[t]),
             overlap10_keys=shared(judged[s][2], judged[t][2]))
    resample = np.random.default_rng(SEED).integers(0, len(bed.queries), (BOOT, len(bed.queries)))

    def against(source: str, target: str, ranked: np.ndarray) -> dict:
        """Scores of a bridged ranking, its agreement with the re-embed, and its distance from staying."""
        means, per_query, top = bed.judge(ranked)
        out = dict(means, overlap10=overlap(ranked, native[target]), overlap10_keys=shared(top, judged[target][2]))
        if source in judged:  # paired bootstrap of nDCG@10(bridge) - nDCG@10(stay) over queries
            diff = (per_query - judged[source][1])[resample].mean(1)
            out.update(stay_lo=float(np.percentile(diff, 2.5)), stay_hi=float(np.percentile(diff, 97.5)))
        return out

    # A document-only space searched natively, once its query vectors exist.
    for m in bed.doc_only:
        if bed.has(m, "queries"):
            native[m] = topk(bed.emb(m, "queries"), bed.emb(m, "corpus"), DEPTH)
            emit(kind="native", space=m, dim=int(bed.emb(m, "corpus").shape[1]), **bed.score(native[m]))

    bm25 = bm25_ranks(bed)
    emit(kind="bm25", **bed.score(bm25))
    for m, r in native.items():
        emit(kind="hybrid-native", space=m, **bed.score(fuse(bm25, r)))

    pairs = [(s, t) for s, t in permutations(bed.open, 2)] + [(s, t) for s in bed.doc_only for t in bed.open]
    t0 = time.time()
    for s, t in pairs:
        Ds, Dt, Qt = bed.emb(s, "corpus"), bed.emb(t, "corpus"), bed.emb(t, "queries")
        for label, part in bed.anchor_sets.items():
            if not (bed.has(s, part) and bed.has(t, part)):
                continue
            usable = bed.anchor_rows[part]
            As, At = bed.emb(s, part)[usable], bed.emb(t, part)[usable]
            # The same nested anchor subsets for every pair and every map.
            order = np.random.default_rng(SEED).permutation(len(As))
            for k in [k for k in KS if k <= len(As)]:
                sel = order[:k]
                for method, fit in ADAPTERS.items():
                    if method == "mlp" and (k not in MLP_KS or label != "in-domain"):
                        continue
                    f = fit(As[sel], At[sel])  # S -> T
                    g = fit(At[sel], As[sel])  # T -> S
                    fwd = topk(Qt, f(Ds), DEPTH)
                    bwd = topk(g(Qt), Ds, DEPTH)
                    common = dict(source=s, target=t, anchors=label, k=k, adapter=method)
                    emit(kind="bridge", direction="forward", **common, **against(s, t, fwd))
                    emit(kind="bridge", direction="backward", **common, **against(s, t, bwd))
                    if method != "mlp" and k in HYBRID_KS and label == "in-domain":
                        for direction, ranks in (("forward", fwd), ("backward", bwd)):
                            emit(kind="hybrid-bridge", direction=direction, **common, **bed.score(fuse(bm25, ranks)))
                    if method != "mlp" and label == "in-domain" and k == max(x for x in KS if x <= len(As)):
                        # How faithfully does the map reproduce true target vectors: for passages it
                        # has not seen, and for queries (anchors are passages, never queries)?
                        held = np.random.default_rng(SEED).permutation(len(Ds))[:2000]
                        fid = dict(cos_docs_fwd=cos(f(Ds[held]), Dt[held]), cos_docs_bwd=cos(g(Dt[held]), Ds[held]))
                        if bed.has(s, "queries"):
                            Qs = bed.emb(s, "queries")
                            fid.update(cos_queries_fwd=cos(f(Qs), Qt), cos_queries_bwd=cos(g(Qt), Qs))
                        emit(kind="fidelity", **common, **fid)
        print(f"{s} -> {t} done ({time.time() - t0:.0f}s)", flush=True)
        with open(out, "w", encoding="utf8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
    print("rows", len(rows))


if __name__ == "__main__":
    main(sys.argv[1])
