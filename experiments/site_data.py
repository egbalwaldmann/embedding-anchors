"""The numbers behind the companion page in site/.

    uv run python experiments/site_data.py

Reads results/<testbed>*.jsonl through beds.py, as report.py does, and writes site/data.json: every measured
combination of pair, map, mode, anchor set and anchor budget, the reference points, the mixed index, the fusion
with BM25 and the similarities of the anchor matrices. Only aggregate numbers per pair of spaces are written. The
paper's own numbers (report.numbers) go along under "paper", and a few of them are recomputed from the exported rows
as a check, so the page cannot drift from the PDF.
"""
from __future__ import annotations

import json
import math
import re
import warnings

from beds import ALT, BEDS, FAMILY, LABEL, MAIN, NAMES, ROOT, WEAK, Bed, mean
from common import RESULTS
from figures import predict_points, top
from report import extra_numbers, numbers

SITE = ROOT / "site"
MODE = {"forward": "index", "backward": "query"}
EXTERNAL = {"english": "English Wikipedia", "wikipedia": "German Wikipedia"}
# The paper's numbers that the page quotes; everything else stays in paper/generated.typ.
KEEP = re.compile(r"^(all\.|[a-z]+\.(top\.|main\.|predict|hy\.|hybrid\.k|x\.mixed\.|x\.hy\.|x\.upgrade\.|beats-stay\.|native\.|bm25|kmax|pairs|"
                  r"stay\.mean|alt\.|native-overlap|x\.retrieval\.|x\.c\.(bridge-vs-native|index-vs-query-translation)))")


def r4(x):
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    if isinstance(x, float):
        return None if math.isnan(x) else round(x, 4)
    return x


def row(*values) -> list:
    return [r4(v) for v in values]


def export(b: Bed) -> dict:
    info = next(r for r in b.rows if r["kind"] == "testbed")
    weak = next(iter(b.of("upgrade-native", space=WEAK)), None)
    out: dict = {
        "label": BEDS[b.name],
        "open": b.open,
        "closed": b.closed,
        "corpus": info["corpus"],
        "queries": info["queries"],
        "anchorSets": {label: {"count": count, "ks": b.ks(label), "label": EXTERNAL.get(label, "in-domain")}
                       for label, count in info["anchors"].items() if b.ks(label)},
        "kmax": b.kmax(),
        "native": {m: row(r["ndcg10"], r["recall10"], r["recall100"], r["dim"]) for m, r in b.native.items()},
        "bm25": row(b.bm25["ndcg10"], b.bm25["recall10"], b.bm25["recall100"]),
        "weak": row(weak["ndcg10"], weak["recall10"], weak["recall100"]) if weak else None,
        "stay": {f"{s}|{t}": r4(b.stay(s, t)) for s, t in b.pairs()},
        "nativeOverlap": {f"{s}|{t}": r4(r["overlap10"]) for (s, t), r in b.native_overlap.items()},
    }
    # Every bridge. Source is the old model and target the new one in both modes; rel is nDCG@10 over the
    # target's own nDCG@10 (b.rel), and stay_lo/stay_hi the 95% interval of nDCG@10 minus the old model's.
    out["bridgeFields"] = ["source", "target", "adapter", "mode", "anchors", "k", "ndcg10", "rel", "recall10", "relRecall10",
                           "overlap10", "stayLo", "stayHi"]
    out["bridges"] = [row(r["source"], r["target"], r["adapter"], MODE[r["direction"]], r["anchors"], r["k"], r["ndcg10"], b.rel(r),
                          r["recall10"], b.rel(r, "recall10"), r["overlap10"], r.get("stay_lo") if b.open_pair(r) else None,
                          r.get("stay_hi") if b.open_pair(r) else None) for r in b.bridges]
    # Mixed index: share of translated passages against quality, with both ends as in fig_mixed.
    full = top(b)
    mixed = {(r["source"], r["target"], r["share"]): r for r in b.of("mixed")}
    out["mixedFields"] = ["source", "target", "share", "rel", "translatedInTop10"]
    out["mixed"] = []
    for p in full:
        if (*p, 0.5) not in mixed:
            continue
        out["mixed"].append(row(*p, 0.0, 1.0, 0.0))
        for share in sorted(s for (a, c, s) in mixed if (a, c) == p):
            m = mixed[(*p, share)]
            out["mixed"].append(row(*p, share, b.rel(m), m["translated_in_top10"]))
        out["mixed"].append(row(*p, 1.0, b.rel(full[p]), 1.0))
    # Fusion with BM25 (evaluate_extra.py), as in fig_hybrid.
    hn = {r["space"]: r for r in b.of("hybrid-native")}
    out["hybridNative"] = {m: row(b.native[m]["ndcg10"], hn[m]["fused"], hn[m]["tuned"]) for m in b.open if m in hn}
    out["hybridFields"] = ["source", "target", "anchors", "k", "bridge", "fused", "tuned"]
    out["hybrid"] = [row(r["source"], r["target"], r["anchors"], r["k"], r["bridge"], r["fused"], r["tuned"]) for r in b.of("hybrid")]
    # Similarity of the anchor matrices against the outcome, as in fig_predict.
    hit = {(r["source"], r["target"]): r["acc1"] for r in b.of("retrieval", anchors="in-domain")}
    out["predictFields"] = ["source", "target", "mode", "rel", "rsa", "cka", "knn", "acc1"]
    out["predict"] = [row(*p["pair"], MODE[d], p["rel"], p["rsa"], p["cka"], p["knn"], hit.get(p["pair"]) if d == "forward" else None)
                      for d in ("forward", "backward") for p in predict_points(b, d)]
    out["simFields"] = ["anchors", "a", "b", "rsa", "cka", "knn"]
    out["sim"] = [row(label, a, c, v["rsa"], v["cka"], v["knn"]) for (label, a, c), v in b.sim.items() if a < c]
    return out


def check(data: dict, n: dict) -> list[str]:
    """Recompute a few of the paper's numbers from the exported rows."""
    lines = []
    for name, bed in data["beds"].items():
        p = name.split("-")[0]
        f = bed["bridgeFields"]
        rows = [dict(zip(f, r)) for r in bed["bridges"]]
        for mode, d in (("index", "fwd"), ("query", "bwd")):
            sel = [r["rel"] for r in rows if r["source"] in bed["open"] and r["adapter"] == MAIN and r["mode"] == mode
                   and r["anchors"] == "in-domain" and r["k"] == bed["kmax"]]
            key = f"{p}.top.{MAIN}.{d}.mean"
            ours = f"{100 * mean(sel):.1f}"
            assert ours == n[key], (key, ours, n[key])
            lines.append(f"{key:34s} paper {n[key]:>6s}  page {ours:>6s}")
        m = [dict(zip(bed["mixedFields"], r)) for r in bed["mixed"]]
        key, ours = f"{p}.x.mixed.90.mean", f"{100 * mean(r['rel'] for r in m if r['share'] == 0.9):.1f}"
        assert ours == n[key], (key, ours, n[key])
        lines.append(f"{key:34s} paper {n[key]:>6s}  page {ours:>6s}")
    return lines


def main() -> None:
    beds = {name: Bed(name) for name in BEDS if (RESULTS / f"{name}.jsonl").exists()}
    with warnings.catch_warnings():  # a source whose four targets tie on held-out anchors has no rank correlation
        warnings.simplefilter("ignore")
        n = numbers(beds)
        n.update(extra_numbers(beds))
    data = {
        "names": {**NAMES, WEAK: "MiniLM-L12"},
        "beds": {name: export(b) for name, b in beds.items()},
        "family": FAMILY,
        "adapters": LABEL,
        "main": MAIN,
        "alt": ALT,
        "paper": {k: v for k, v in sorted(n.items()) if KEEP.match(k)},
    }
    for line in check(data, n):
        print(line)
    SITE.mkdir(exist_ok=True)
    path = SITE / "data.json"
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    print(f"{path.relative_to(ROOT)}: {path.stat().st_size / 1024:.0f} KB, {sum(len(b['bridges']) for b in data['beds'].values()):,} bridges")


if __name__ == "__main__":
    main()
