"""Turn the result files into the paper's figures, tables and numbers.

    uv run python experiments/report.py

Reads results/<testbed>*.jsonl and writes paper/fig/*.pdf (figures.py) and paper/generated.typ. The paper takes every number from
generated.typ, so nothing is copied by hand.
"""
from __future__ import annotations

import json

import numpy as np
from scipy.stats import spearmanr

import figures
from beds import ALT, BEDS, FAMILY, MAIN, NAMES, PAPER, Bed, load, mean
from common import ALL, RESULTS
from figures import predict_points


def pct(x: float) -> str:
    return f"{100 * x:.1f}"


def f3(x: float) -> str:
    return f"{x:.3f}"


# ---------------------------------------------------------------- tables and numbers


def typ_table(columns: str, align: str, header: list[str], body: list[list[str]], top: str = "") -> str:
    cells = (top + ", " if top else "") + ", ".join(f"[*{h}*]" for h in header)
    lines = [f"table(columns: {columns}, align: {align}, stroke: none, inset: (x: 5pt, y: 3pt),",
             "  table.hline(stroke: 0.8pt),", f"  table.header({cells}),", "  table.hline(stroke: 0.4pt),"]
    for row in body:
        if row == ["-"]:
            lines.append("  table.hline(stroke: 0.4pt),")
        else:
            lines.append("  " + ", ".join(f"[{c}]" for c in row) + ",")
    lines.append("  table.hline(stroke: 0.8pt),\n)")
    return "\n".join(lines)


def table_native(beds: dict[str, Bed]) -> str:
    spaces = [m for m in NAMES if any(m in b.native for b in beds.values())]
    top = "[], [], " + ", ".join(f"table.cell(colspan: 2, align: center)[*{BEDS[b]}*]" for b in beds)
    header = ["Space", "Dim."] + ["nDCG\\@10", "R\\@10"] * len(beds)
    body = []
    for m in spaces:
        dim = next(b.native[m]["dim"] for b in beds.values() if m in b.native)
        row = [f"{NAMES[m]}", f"{dim:,}"]
        for b in beds.values():
            row += [f3(b.native[m]["ndcg10"]), f3(b.native[m]["recall10"])] if m in b.native else ["--", "--"]
        body.append(row)
    body.append(["-"])
    row = ["BM25", "--"]
    for b in beds.values():
        row += [f3(b.bm25["ndcg10"]), f3(b.bm25["recall10"])]
    body.append(row)
    return typ_table("(auto, auto" + ", auto" * (2 * len(beds)) + ")", "(left, right" + ", right" * (2 * len(beds)) + ")", header, body, top)


def table_closed(beds: dict[str, Bed]) -> str:
    header = ["Source", "Target", "$k$", "Index tr.", "Query tr.", "Overlap\\@10"]
    body = []
    for b in beds.values():
        for s in b.closed:
            for t in b.open:
                ks = [k for k in (1000, b.kmax()) if k in b.ks()]
                for k in ks:
                    f = b.pick(source=s, target=t, anchors="in-domain", adapter=MAIN, k=k, direction="forward")
                    g = b.pick(source=s, target=t, anchors="in-domain", adapter=MAIN, k=k, direction="backward")
                    if f and g:
                        body.append([NAMES[s] if k == ks[0] and t == b.open[0] else "", NAMES[t] if k == ks[0] else "", f"{k:,}",
                                     pct(b.rel(f[0])), pct(b.rel(g[0])), pct(f[0]["overlap10"])])
            body.append(["-"])
    return typ_table("(auto, auto, auto, auto, auto, auto)", "(left, left, right, right, right, right)", header, body[:-1])


def hybrid_rows(b: Bed, k: int, adapter: str = MAIN, direction: str = "forward") -> dict[str, float]:
    hb = [r for r in b.hybrid_bridges if r["k"] == k and r["adapter"] == adapter and r["direction"] == direction and b.open_pair(r)]
    br = {(r["source"], r["target"]): r for r in b.pick(anchors="in-domain", adapter=adapter, k=k, direction=direction)}
    if not hb:
        return {}
    return {
        "bridge": mean(br[(r["source"], r["target"])]["ndcg10"] for r in hb),
        "fused": mean(r["ndcg10"] for r in hb),
        "stay": mean(b.native[r["source"]]["ndcg10"] for r in hb),
        "stay-fused": mean(b.hybrid_native[r["source"]]["ndcg10"] for r in hb),
        "native": mean(b.native[r["target"]]["ndcg10"] for r in hb),
        "native-fused": mean(b.hybrid_native[r["target"]]["ndcg10"] for r in hb),
        "fused-beats-bm25": sum(r["ndcg10"] >= b.bm25["ndcg10"] for r in hb),
        "bridge-beats-bm25": sum(br[(r["source"], r["target"])]["ndcg10"] >= b.bm25["ndcg10"] for r in hb),
        "fused-beats-stay-fused": sum(r["ndcg10"] >= b.hybrid_native[r["source"]]["ndcg10"] for r in hb),
        "n": len(hb),
    }


def table_hybrid(beds: dict[str, Bed]) -> str:
    header = ["Testbed", "$k$", "BM25", "Bridge", "Bridge + BM25", "Native", "Native + BM25"]
    body = []
    for b in beds.values():
        for k in sorted({r["k"] for r in b.hybrid_bridges}):
            h = hybrid_rows(b, k)
            if h:
                first = not body or body[-1] == ["-"]
                body.append([BEDS[b.name] if first else "", f"{k:,}", f3(b.bm25["ndcg10"]) if first else ""]
                            + [f3(h[c]) for c in ("bridge", "fused", "native", "native-fused")])
        body.append(["-"])
    body = body[:-1]
    return typ_table("(auto" + ", auto" * 6 + ")", "(left" + ", right" * 6 + ")", header, body)


def numbers(beds: dict[str, Bed]) -> dict[str, str]:
    n: dict[str, str] = {}
    allpts = []
    for name, b in beds.items():
        p = name.split("-")[0]  # wiki / archive
        n[f"{p}.kmax"] = f"{b.kmax():,}"
        info = next((r for r in b.rows if r["kind"] == "testbed"), None)
        if info:
            n[f"{p}.corpus"] = f"{info['corpus']:,}"
            n[f"{p}.queries"] = f"{info['queries']:,}"
            n[f"{p}.groups"] = f"{info['groups']:,}"
            for label, count in info["anchors"].items():
                n[f"{p}.anchors.{label}"] = f"{count:,}"
        n[f"{p}.open"] = str(len(b.open))
        n[f"{p}.bm25.ndcg"] = f3(b.bm25["ndcg10"])
        for m, r in b.native.items():
            n[f"{p}.native.{m}.ndcg"] = f3(r["ndcg10"])
            n[f"{p}.native.{m}.r10"] = f3(r["recall10"])
        open_rows = [r for r in b.bridges if b.open_pair(r)]
        pairs = sorted({(r["source"], r["target"]) for r in open_rows})
        n[f"{p}.pairs"] = str(len(pairs))
        n[f"{p}.stay.mean"] = pct(mean(b.stay(s, t) for s, t in pairs))
        for anchors in sorted({r["anchors"] for r in b.bridges}):
            for adapter in ("procrustes", "ridge", "mlp"):
                for direction in ("forward", "backward"):
                    d = "fwd" if direction == "forward" else "bwd"
                    for k in b.ks(anchors):
                        sel = [r for r in open_rows if r["anchors"] == anchors and r["adapter"] == adapter and r["direction"] == direction and r["k"] == k]
                        if not sel:
                            continue
                        rels = [b.rel(r) for r in sel]
                        key = f"{p}.{anchors}.{adapter}.{d}.{k}"
                        n[f"{key}.mean"] = pct(mean(rels))
                        n[f"{key}.min"] = pct(min(rels))
                        n[f"{key}.max"] = pct(max(rels))
                        n[f"{key}.r10"] = pct(mean(b.rel(r, "recall10") for r in sel))
                        n[f"{key}.overlap"] = pct(mean(r["overlap10"] for r in sel))
                        n[f"{key}.vs-stay"] = pct(mean(r["ndcg10"] / b.native[r["source"]]["ndcg10"] for r in sel))
                        wins = sum(r["ndcg10"] >= b.native[r["source"]]["ndcg10"] for r in sel)
                        n[f"{key}.beats-stay"] = str(wins)
                        n[f"{key}.n"] = str(len(sel))
        # Closed sources (document vectors only).
        for s in b.closed:
            for anchors in sorted({r["anchors"] for r in b.bridges if r["source"] == s}):
                for adapter in ("procrustes", "ridge", "mlp"):
                    for direction in ("forward", "backward"):
                        d = "fwd" if direction == "forward" else "bwd"
                        for k in b.ks(anchors):
                            sel = b.pick(source=s, anchors=anchors, adapter=adapter, direction=direction, k=k)
                            if sel:
                                key = f"{p}.{s}.{anchors}.{adapter}.{d}.{k}"
                                n[f"{key}.mean"] = pct(mean(b.rel(r) for r in sel))
                                n[f"{key}.min"] = pct(min(b.rel(r) for r in sel))
                                n[f"{key}.max"] = pct(max(b.rel(r) for r in sel))
                                n[f"{key}.overlap"] = pct(mean(r["overlap10"] for r in sel))
        # Best and worst ordered pair at the largest anchor budget (index translation).
        top = sorted(b.pick(anchors="in-domain", adapter=MAIN, k=b.kmax(), direction="forward"), key=b.rel)
        top = [r for r in top if b.open_pair(r)]
        if top:
            n[f"{p}.worst.pair"] = f"{NAMES[top[0]['source']]} to {NAMES[top[0]['target']]}"
            n[f"{p}.worst.rel"] = pct(b.rel(top[0]))
            n[f"{p}.best.pair"] = f"{NAMES[top[-1]['source']]} to {NAMES[top[-1]['target']]}"
            n[f"{p}.best.rel"] = pct(b.rel(top[-1]))
        for k in sorted({r["k"] for r in b.hybrid_bridges}):
            for adapter in ("procrustes", "ridge"):
                for direction in ("forward", "backward"):
                    for name, v in hybrid_rows(b, k, adapter, direction).items():
                        key = f"{p}.hybrid.{adapter}.{'fwd' if direction == 'forward' else 'bwd'}.{k}.{name}"
                        n[key] = str(v) if isinstance(v, int) else f3(v)
        for adapter in ("procrustes", "ridge"):
            rows = [r for r in b.fidelity if r["adapter"] == adapter and b.open_pair(r)]
            for field in ("cos_docs_fwd", "cos_docs_bwd", "cos_queries_fwd", "cos_queries_bwd"):
                if rows:
                    n[f"{p}.fidelity.{adapter}.{field.replace('cos_', '').replace('_', '-')}"] = f"{mean(r[field] for r in rows):.2f}"
        # Short names for the headline configuration: in-domain anchors, each map at its largest budget.
        for adapter in ("procrustes", "ridge", "mlp"):
            ks = [r["k"] for r in open_rows if r["anchors"] == "in-domain" and r["adapter"] == adapter]
            if ks:
                n[f"{p}.top.{adapter}.k"] = f"{max(ks):,}"
                for d in ("fwd", "bwd"):
                    for stat in ("mean", "min", "max", "r10", "overlap", "vs-stay"):
                        n[f"{p}.top.{adapter}.{d}.{stat}"] = n[f"{p}.in-domain.{adapter}.{d}.{max(ks)}.{stat}"]
        hk = max((r["k"] for r in b.hybrid_bridges), default=None)
        if hk:
            for name, v in hybrid_rows(b, hk).items():
                n[f"{p}.hy.{name}"] = str(v) if isinstance(v, int) else f3(v)
        nat = [b.native[m]["ndcg10"] for m in b.open]
        n[f"{p}.native.min"], n[f"{p}.native.max"] = f3(min(nat)), f3(max(nat))
        n[f"{p}.native.spread"] = f"{100 * (max(nat) - min(nat)):.1f}"
        n[f"{p}.beats-stay.ndcg-max"] = f"{100 * max(r['ndcg10'] - b.native[r['source']]['ndcg10'] for r in open_rows):.1f}"
        # Index against query translation, pair by pair, for the headline configuration.
        fb = {(r["source"], r["target"], r["direction"]): b.rel(r) for r in b.pick(anchors="in-domain", adapter=MAIN, k=b.kmax())}
        gaps = {(s_, t_): fb[(s_, t_, "forward")] - fb[(s_, t_, "backward")] for s_, t_ in pairs}
        widest = max(gaps, key=lambda q: abs(gaps[q]))
        n[f"{p}.modes.gap.mean"] = f"{100 * mean(gaps.values()):.1f}"
        n[f"{p}.modes.gap.max"] = f"{100 * abs(gaps[widest]):.1f}"
        n[f"{p}.modes.gap.max-pair"] = f"{NAMES[widest[0]]} to {NAMES[widest[1]]}"
        # What anchors from elsewhere cost against in-domain anchors at equal size, pair by pair.
        alt = ALT.get(b.name)
        if alt:
            k = min(b.kmax(), b.kmax(alt))
            dom = {(r["source"], r["target"]): b.rel(r) for r in b.pick(anchors="in-domain", adapter=MAIN, k=k, direction="forward") if b.open_pair(r)}
            oth = {(r["source"], r["target"]): b.rel(r) for r in b.pick(anchors=alt, adapter=MAIN, k=k, direction="forward") if b.open_pair(r)}
            loss = [dom[q] - oth[q] for q in dom if q in oth]
            n[f"{p}.alt.k"] = f"{k:,}"
            n[f"{p}.alt.loss.mean"] = f"{100 * mean(loss):.1f}"
            n[f"{p}.alt.loss.max"] = f"{100 * max(loss):.1f}"
        # Does anchor similarity order the targets of one source? Mean rank correlation over the sources.
        pts = predict_points(b)
        for m in ("rsa", "cka", "knn"):
            rhos = []
            for src in b.open:
                own = [q for q in pts if q["pair"][0] == src]
                if len(own) > 2:
                    rhos.append(spearmanr([q[m] for q in own], [q["rel"] for q in own]).statistic)
            if rhos:
                n[f"{p}.predict-source.{m}"] = f"{mean(rhos):.2f}"
        r10 = [r["recall10"] - b.native[r["source"]]["recall10"] for r in open_rows]
        n[f"{p}.beats-stay.r10-max"] = f"{100 * max(r10):.1f}"
        wins = [r for r in open_rows if r["ndcg10"] >= b.native[r["source"]]["ndcg10"]]
        # Bridge against staying on the old model, over every measured combination.
        n[f"{p}.beats-stay.of"] = f"{len(open_rows):,}"
        n[f"{p}.beats-stay.ndcg"] = str(len(wins))
        n[f"{p}.beats-stay.r10"] = str(sum(r["recall10"] > b.native[r["source"]]["recall10"] for r in open_rows))
        n[f"{p}.beats-stay.significant"] = str(sum(r["stay_lo"] > 0 for r in open_rows))
        n[f"{p}.beats-stay.tie"] = str(sum(r["stay_lo"] <= 0 <= r["stay_hi"] for r in open_rows))
        n[f"{p}.beats-stay.below"] = f"{sum(r['stay_hi'] < 0 for r in open_rows):,}"
        if b.hybrid_bridges:
            n[f"{p}.hybrid.k"] = f"{max(r['k'] for r in b.hybrid_bridges):,}"
        for direction in ("forward", "backward"):
            d = "fwd" if direction == "forward" else "bwd"
            main = [r for r in b.pick(anchors="in-domain", adapter=MAIN, k=b.kmax(), direction=direction) if b.open_pair(r)]
            n[f"{p}.main.{d}.n"] = str(len(main))
            n[f"{p}.main.{d}.below"] = str(sum(r["stay_hi"] < 0 for r in main))
            n[f"{p}.main.{d}.tie"] = str(sum(r["stay_lo"] <= 0 <= r["stay_hi"] for r in main))
            n[f"{p}.main.{d}.overlap-keys"] = pct(mean(r["overlap10_keys"] for r in main))
            for label, same in (("within", True), ("cross", False)):
                sel = [r for r in main if (FAMILY.get(r["source"], r["source"]) == FAMILY.get(r["target"], r["target"])) == same]
                if sel:
                    n[f"{p}.main.{d}.{label}.mean"] = pct(mean(b.rel(r) for r in sel))
                    n[f"{p}.main.{d}.{label}.n"] = str(len(sel))
        if b.native_overlap:
            n[f"{p}.native-overlap"] = pct(mean(r["overlap10"] for r in b.native_overlap.values()))
            n[f"{p}.native-overlap-keys"] = pct(mean(r["overlap10_keys"] for r in b.native_overlap.values()))
        for model, t in b.tokens.items():
            n[f"{p}.tokens.{model}.truncated"] = pct(t["truncated"])
            n[f"{p}.tokens.{model}.limit"] = f"{t['limit']:,}"
        if b.tokens:
            n[f"{p}.tokens.max-truncated"] = pct(max(t["truncated"] for t in b.tokens.values()))
        # Does anchor similarity predict the outcome?
        for direction in ("forward", "backward"):
            pts = predict_points(b, direction)
            if direction == "forward":
                allpts += pts
            for m in ("rsa", "cka", "knn"):
                if len(pts) > 2:
                    n[f"{p}.predict.{m}.{'fwd' if direction == 'forward' else 'bwd'}"] = f"{spearmanr([q[m] for q in pts], [q['rel'] for q in pts]).statistic:.2f}"
        n[f"{p}.predict.n"] = str(len(predict_points(b)))
        # Similarity read off public anchors against the outcome with in-domain anchors.
        pub = [(b.sim[("wikipedia", r["source"], r["target"])], b.rel(r))
               for r in b.pick(anchors="in-domain", adapter=MAIN, k=b.kmax(), direction="forward")
               if ("wikipedia", r["source"], r["target"]) in b.sim]
        if len(pub) > 2:
            n[f"{p}.predict-public.n"] = str(len(pub))
            for m in ("rsa", "cka", "knn"):
                n[f"{p}.predict-public.{m}"] = f"{spearmanr([x[m] for x, _ in pub], [y for _, y in pub]).statistic:.2f}"
        for (label, a, c), v in b.sim.items():
            if label == "in-domain":
                for m in ("rsa", "cka", "knn"):
                    n[f"{p}.sim.{a}.{c}.{m}"] = f"{v[m]:.2f}"
        sims = [v for (label, a, c), v in b.sim.items() if label == "in-domain" and a < c]
        if sims:
            n[f"{p}.knn.min"] = f"{min(v['knn'] for v in sims):.2f}"
            n[f"{p}.knn.max"] = f"{max(v['knn'] for v in sims):.2f}"
    for m in ("rsa", "cka", "knn"):
        if len(allpts) > 2:
            n[f"all.predict.{m}"] = f"{spearmanr([q[m] for q in allpts], [q['rel'] for q in allpts]).statistic:.2f}"
    n["all.predict.n"] = str(len(allpts))
    count = lambda key: sum(int(n[f"{name.split('-')[0]}.beats-stay.{key}"].replace(",", "")) for name in beds)
    n["all.beats-stay.of"] = f"{count('of'):,}"
    n["all.beats-stay.ndcg"] = str(count("ndcg"))
    n["all.beats-stay.significant"] = str(count("significant"))
    lows = [float(n[f"{name.split('-')[0]}.top.{MAIN}.fwd.min"]) for name in beds]
    highs = [float(n[f"{name.split('-')[0]}.top.{MAIN}.fwd.max"]) for name in beds]
    n["all.top.fwd.min"], n["all.top.fwd.max"] = f"{min(lows):.0f}", f"{max(highs):.0f}"
    return n


def extra_numbers(beds: dict[str, Bed]) -> dict[str, str]:
    """Numbers from results/<testbed>.extra.jsonl (evaluate_extra.py), keys <testbed>.x.*"""
    n: dict[str, str] = {}
    total: dict[str, int] = {}
    pts = lambda x: f"{100 * x:.1f}"
    for name, b in beds.items():
        rows = load(f"{name}.extra.jsonl")
        if not rows:
            continue
        p = name.split("-")[0]
        of = lambda kind: [r for r in rows if r["kind"] == kind]
        rel = lambda r: r["ndcg10"] / b.native[r["target"]]["ndcg10"]
        kmax = b.kmax()
        # Query translation fitted on document-role or query-role anchors.
        for adapter in ("procrustes", "ridge"):
            for role in ("document", "query"):
                for k in sorted({r["k"] for r in of("role")}):
                    sel = [r for r in of("role") if r["adapter"] == adapter and r["role"] == role and r["k"] == k]
                    if sel:
                        n[f"{p}.x.role.{adapter}.{role}.{k}.mean"] = pct(mean(rel(r) for r in sel))
                        if k == kmax:
                            n[f"{p}.x.role.{adapter}.{role}.mean"] = pct(mean(rel(r) for r in sel))
                            n[f"{p}.x.role.{adapter}.{role}.min"] = pct(min(rel(r) for r in sel))
                            n[f"{p}.x.role.{adapter}.{role}.below"] = str(sum(r["stay_hi"] < 0 for r in sel))
                            n[f"{p}.x.role.{adapter}.{role}.n"] = str(len(sel))
            top = {(r["source"], r["target"], r["role"]): rel(r) for r in of("role") if r["adapter"] == adapter and r["k"] == kmax}
            gains = [top[(s_, t_, "query")] - top[(s_, t_, "document")] for (s_, t_, role) in top if role == "document"]
            if gains:
                n[f"{p}.x.role.{adapter}.gain.max"] = pts(max(gains))
                n[f"{p}.x.role.{adapter}.gain.min"] = pts(min(gains))
                n[f"{p}.x.role.{adapter}.better"] = str(sum(g > 0 for g in gains))
        for direction, d in (("forward", "fwd"), ("backward", "bwd")):
            sel = [r for r in of("uncentred") if r["direction"] == direction and r["k"] == kmax]
            if sel:
                worst = min(sel, key=rel)
                n[f"{p}.x.uncentred.{d}.mean"] = pct(mean(rel(r) for r in sel))
                n[f"{p}.x.uncentred.{d}.min"] = pct(rel(worst))
                n[f"{p}.x.uncentred.{d}.min-pair"] = f"{NAMES[worst['source']]} to {NAMES[worst['target']]}"
                centred = {(r["source"], r["target"]): b.rel(r) for r in b.pick(anchors="in-domain", adapter=MAIN, k=kmax, direction=direction)}
                n[f"{p}.x.uncentred.{d}.min-centred"] = pct(centred[(worst["source"], worst["target"])])
                n[f"{p}.x.uncentred.{d}.worse"] = str(sum(rel(r) < centred[(r["source"], r["target"])] - 0.01 for r in sel))
                n[f"{p}.x.uncentred.{d}.n"] = str(len(sel))
                n[f"{p}.x.uncentred.{d}.loss.max"] = pts(max(centred[(r["source"], r["target"])] - rel(r) for r in sel))
        up = of("upgrade")
        if up:
            counts = {"of": len(up), "above": sum(r["stay_lo"] > 0 for r in up), "reach": sum(r["stay_diff"] >= 0 for r in up),
                      "below": sum(r["stay_hi"] < 0 for r in up)}
            for key, value in counts.items():
                n[f"{p}.x.upgrade.{key}"] = f"{value:,}"
                total[key] = total.get(key, 0) + value
        # An old or document-only space with its own queries as the source.
        for nat in of("upgrade-native"):
            src = nat["space"]
            n[f"{p}.x.{src}.native"] = f3(nat["ndcg10"])
            n[f"{p}.x.{src}.native.r10"] = f3(nat["recall10"])
            n[f"{p}.x.{src}.native.rel"] = pct(nat["ndcg10"] / mean(b.native[m]["ndcg10"] for m in b.open))
            for anchors in sorted({r["anchors"] for r in of("upgrade") if r["source"] == src}):
                ks = sorted({r["k"] for r in of("upgrade") if r["source"] == src and r["anchors"] == anchors})
                for adapter in ("procrustes", "ridge"):
                    for direction, d in (("forward", "fwd"), ("backward", "bwd")):
                        for k in ks:
                            sel = [r for r in of("upgrade") if r["source"] == src and r["anchors"] == anchors
                                   and r["adapter"] == adapter and r["direction"] == direction and r["k"] == k]
                            if not sel:
                                continue
                            keys = [f"{p}.x.{src}.{anchors}.{adapter}.{d}.{k}"] + ([f"{p}.x.{src}.{anchors}.{adapter}.{d}"] if k == ks[-1] else [])
                            for key in keys:
                                n[f"{key}.mean"] = pct(mean(rel(r) for r in sel))
                                n[f"{key}.ndcg"] = f3(mean(r["ndcg10"] for r in sel))
                                n[f"{key}.vs-stay"] = pct(mean(r["ndcg10"] / nat["ndcg10"] for r in sel))
                                n[f"{key}.above"] = str(sum(r["stay_lo"] > 0 for r in sel))
                                n[f"{key}.below"] = str(sum(r["stay_hi"] < 0 for r in sel))
                                n[f"{key}.n"] = str(len(sel))
            hyb = [r for r in of("upgrade-hybrid") if r["source"] == src]
            if hyb:
                for field in ("bridge", "fused", "stay", "stay_fused"):
                    n[f"{p}.x.{src}.hy.{field.replace('_', '-')}"] = f3(mean(r[field] for r in hyb))
        # One index with translated and re-embedded vectors.
        for share in sorted({r["share"] for r in of("mixed")}):
            sel = [r for r in of("mixed") if r["share"] == share]
            key = f"{p}.x.mixed.{int(100 * share)}"
            n[f"{key}.mean"] = pct(mean(rel(r) for r in sel))
            n[f"{key}.min"] = pct(min(rel(r) for r in sel))
            n[f"{key}.translated"] = pct(mean(r["translated_in_top10"] for r in sel))
        # Other draws of the anchors: spread of the mean over pairs.
        for k in sorted({r["k"] for r in of("seed")}):
            for direction, d in (("forward", "fwd"), ("backward", "bwd")):
                per_seed = [mean(rel(r) for r in of("seed") if r["seed"] == seed and r["k"] == k and r["direction"] == direction)
                            for seed in sorted({r["seed"] for r in of("seed")})]
                n[f"{p}.x.seed.{k}.{d}.mean"] = pct(mean(per_seed))
                n[f"{p}.x.seed.{k}.{d}.sd"] = f"{100 * float(np.std(per_seed, ddof=1)):.2f}"
                n[f"{p}.x.seed.{k}.{d}.min"], n[f"{p}.x.seed.{k}.{d}.max"] = pct(min(per_seed)), pct(max(per_seed))
                spread = [float(np.std([rel(r) for r in of("seed") if (r["source"], r["target"]) == pair and r["k"] == k and r["direction"] == direction], ddof=1))
                          for pair in {(r["source"], r["target"]) for r in of("seed")}]
                n[f"{p}.x.seed.{k}.{d}.pair-sd.max"] = f"{100 * max(spread):.1f}"
            n[f"{p}.x.seed.n"] = str(len({r["seed"] for r in of("seed")}))
        # Fusion with BM25.
        for label in sorted({r["anchors"] for r in of("hybrid")}):
            for k in sorted({r["k"] for r in of("hybrid") if r["anchors"] == label}):
                sel = [r for r in of("hybrid") if r["anchors"] == label and r["k"] == k]
                key = f"{p}.x.hy.{label}.{k}"
                for field in ("bridge", "fused", "tuned"):
                    n[f"{key}.{field}"] = f3(mean(r[field] for r in sel))
                n[f"{key}.fused-beats"] = str(sum(r["fused_beats_bm25"] for r in sel))
                n[f"{key}.tuned-beats"] = str(sum(r["tuned_beats_bm25"] for r in sel))
                n[f"{key}.n"] = str(len(sel))
        hn = {r["space"]: r for r in of("hybrid-native")}
        if hn:
            n[f"{p}.x.hy.native.fused"] = f3(mean(hn[m]["fused"] for m in b.open for _ in range(len(b.open) - 1)))
            n[f"{p}.x.hy.native.tuned"] = f3(mean(hn[m]["tuned"] for m in b.open for _ in range(len(b.open) - 1)))
        # Held-out anchor retrieval as a predictor of the outcome.
        outcome = {(r["source"], r["target"]): b.rel(r) for r in b.pick(anchors="in-domain", adapter=MAIN, k=kmax, direction="forward")}
        for label in sorted({r["anchors"] for r in of("retrieval")}):
            sel = [r for r in of("retrieval") if r["anchors"] == label and (r["source"], r["target"]) in outcome]
            if len(sel) > 2:
                key = f"{p}.x.retrieval.{label}"
                n[f"{key}.rho"] = f"{spearmanr([r['acc1'] for r in sel], [outcome[(r['source'], r['target'])] for r in sel]).statistic:.2f}"
                n[f"{key}.n"] = str(len(sel))
                n[f"{key}.min"], n[f"{key}.max"] = pct(min(r["acc1"] for r in sel)), pct(max(r["acc1"] for r in sel))
                rhos = []
                for src in {r["source"] for r in sel}:
                    own = [r for r in sel if r["source"] == src]
                    if len(own) > 2:
                        rhos.append(spearmanr([r["acc1"] for r in own], [outcome[(r["source"], r["target"])] for r in own]).statistic)
                n[f"{key}.rho-source"] = f"{mean(rhos):.2f}"
        for r in of("contrast"):
            key = f"{p}.x.c.{r['name']}"
            n[f"{key}.diff"], n[f"{key}.lo"], n[f"{key}.hi"] = pts(r["diff"]), pts(r["lo"]), pts(r["hi"])
            n[f"{key}.a"], n[f"{key}.b"] = f3(r["a"]), f3(r["b"])
            n[f"{key}.sig"] = "yes" if r["lo"] > 0 or r["hi"] < 0 else "no"
    for key, value in total.items():
        n[f"all.x.upgrade.{key}"] = f"{value:,}"
    return n


def table_upgrade(beds: dict[str, Bed], source: str = "minilm-l12") -> str:
    header = ["Testbed", "Stay", "Index, orthogonal", "Index, ridge", "Queries, orthogonal", "Re-embed"]
    body = []
    for name, b in beds.items():
        rows = load(f"{name}.extra.jsonl")
        nat = next((r for r in rows if r["kind"] == "upgrade-native" and r["space"] == source), None)
        if not nat:
            continue

        def cell(adapter: str, direction: str) -> str:
            m = mean(r["ndcg10"] for r in rows if r["kind"] == "upgrade" and r["source"] == source and r["anchors"] == "in-domain"
                     and r["adapter"] == adapter and r["direction"] == direction and r["k"] == b.kmax())
            return f"{f3(m)} ({pct(m / nat['ndcg10'])}%)"

        body.append([BEDS[name], f3(nat["ndcg10"]), cell("procrustes", "forward"), cell("ridge", "forward"), cell("procrustes", "backward"),
                     f3(mean(b.native[m]["ndcg10"] for m in b.open))])
    return typ_table("(auto" + ", auto" * 5 + ")", "(left" + ", right" * 5 + ")", header, body)


def table_mixed(beds: dict[str, Bed]) -> str:
    header = ["Testbed", "10%", "50%", "90%", "100%", "In top ten at 50%"]
    body = []
    for name, b in beds.items():
        rows = [r for r in load(f"{name}.extra.jsonl") if r["kind"] == "mixed"]
        if not rows:
            continue
        rel = lambda r: r["ndcg10"] / b.native[r["target"]]["ndcg10"]
        share = lambda x: [r for r in rows if r["share"] == x]
        full = mean(b.rel(r) for r in b.pick(anchors="in-domain", adapter=MAIN, k=b.kmax(), direction="forward") if b.open_pair(r))
        body.append([BEDS[name]] + [pct(mean(rel(r) for r in share(x))) for x in (0.1, 0.5, 0.9)] + [pct(full),
                    pct(mean(r["translated_in_top10"] for r in share(0.5))) + "%"])
    return typ_table("(auto" + ", auto" * 5 + ")", "(left" + ", right" * 5 + ")", header, body)


# Revisions and licences of the weights that were used (the open models as in release_anchors.py).
REVISIONS = {
    "bge-m3": ("5617a9f61b028005a4858fdac845db406aefb181", "MIT"),
    "me5-large": ("3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3", "MIT"),
    "arctic-l-v2": ("ac6544c8a46e00af67e330e85a9028c66b8cfd9a", "Apache-2.0"),
    "qwen3-0.6b": ("97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3", "Apache-2.0"),
    "embeddinggemma-2": ("f9972ac22e696a105c482202646979e33e4b5a1e", "Apache-2.0"),
    "minilm-l12": ("e8f8c211226b894fcb81acc59f3b34ba3efd5f42", "Apache-2.0"),
}


def table_models() -> str:
    def raw(text: str) -> str:
        return "raw(" + json.dumps(text.replace("\n", "\\n"), ensure_ascii=False) + ")" if text else "[--]"

    names = {**NAMES, "minilm-l12": "MiniLM-L12"}
    header = ["Space", "Revision", "Licence", "Document prefix", "Query prefix"]
    lines = ["table(columns: (auto, auto, auto, auto, 1fr), align: (left, left, left, left, left), stroke: none, inset: (x: 5pt, y: 3.2pt),",
             "  table.hline(stroke: 0.8pt),", "  table.header(" + ", ".join(f"[*{h}*]" for h in header) + "),", "  table.hline(stroke: 0.4pt),"]
    for m, (revision, licence) in REVISIONS.items():
        lines.append(f"  [{names[m]}], raw(\"{revision[:8]}\"), [{licence}], {raw(ALL[m]['d'])}, {raw(ALL[m]['q'])},")
    lines.append("  table.hline(stroke: 0.8pt),\n)")
    return "\n".join(lines)


def main() -> None:
    beds = {name: Bed(name) for name in BEDS if (RESULTS / f"{name}.jsonl").exists()}
    figures.draw(list(beds.values()))
    n = numbers(beds)
    n.update(extra_numbers(beds))
    out = ["// Generated by experiments/report.py. Do not edit.", "#let n = ("]
    out += [f'  "{k}": "{v}",' for k, v in sorted(n.items())]
    out += [")", "", "#let table-native = " + table_native(beds), "", "#let table-closed = " + table_closed(beds), "",
            "#let table-hybrid = " + table_hybrid(beds), "", "#let table-upgrade = " + table_upgrade(beds), "",
            "#let table-mixed = " + table_mixed(beds), "", "#let table-models = " + table_models(), ""]
    (PAPER / "generated.typ").write_text("\n".join(out), encoding="utf8")
    print("numbers", len(n), "testbeds", list(beds))


if __name__ == "__main__":
    main()
