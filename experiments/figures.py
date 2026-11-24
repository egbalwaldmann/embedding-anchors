"""The paper's figures, drawn from the result files. Called by report.py.

One convention holds throughout. Blue is the main configuration (orthogonal map, in-domain
anchors), orange the alternative it is compared with, green a third; reference points such as
staying on the old model, a full re-embed or BM25 are black and grey. Where a figure has one
panel per testbed, the testbed needs no colour; where the testbeds share a panel, each has its
own marker (MARKS).
"""
from __future__ import annotations

import json
import logging
from statistics import mode

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter

from beds import ALT, BEDS, LABEL, MAIN, NAMES, PAPER, WEAK, Bed, mean, same_family
from common import MODELS, RESULTS, SEED

logging.getLogger("fontTools").setLevel(logging.ERROR)  # the embedded font carries no timestamps
FIG = PAPER / "fig"
WIDTH = 6.3  # inches; the text width of the paper, so that figures are set at their true size

BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, FAINT, GRID = "#111111", "#6f6f6f", "#c9c9c9", "#e6e6e6"
MAP_COLOR = {"procrustes": BLUE, "ridge": ORANGE, "mlp": GREEN}
DASH = (0, (3.5, 2))        # query translation
LEXICAL = (0, (5, 1.5, 1, 1.5))  # BM25
# One hue from light to dark for magnitudes; a second ramp where two measures share one figure.
BLUES = LinearSegmentedColormap.from_list("blues", ["#f4f8fe", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
ORANGES = LinearSegmentedColormap.from_list("oranges", ["#fef6f1", "#fbd9c8", "#f4a57f", "#eb6834", "#b8461a", "#7a2c0e"])
ROW = {**NAMES, WEAK: "MiniLM-L12", "bm25": "BM25"}
MARKS = {"wiki-de": ("o", BLUE, 22), "miracl-de": ("s", GREEN, 19), "archive": ("^", ORANGE, 26)}  # marker, colour, area
EXTERNAL = {"english": "English Wikipedia", "wikipedia": "German Wikipedia"}  # where the external anchors come from
RELEVANCE = {"wiki-de": "judged page", "miracl-de": "judged passage", "archive": "one known passage"}
BACKGROUND = {"wiki-de": 100_000, "miracl-de": 100_000}  # N_CORPUS in prep_public.py: passages drawn at random around the judged ones
CHOICE = ("wiki-de", "archive")  # the easiest and the hardest testbed, for the figure that needs a row per testbed

# Computer Modern, which ships with matplotlib, to match the type of the paper.
plt.rcParams.update({
    "font.family": "cmr10", "mathtext.fontset": "cm", "axes.formatter.use_mathtext": True, "axes.unicode_minus": False,
    "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": INK, "xtick.color": INK, "ytick.color": INK,
    "legend.frameon": False, "legend.handlelength": 2.6, "lines.solid_capstyle": "round", "svg.fonttype": "path", "svg.hashsalt": "anchors",
})


# ---------------------------------------------------------------- helpers


def panels(rows: int, cols: int, height: float, **kw):
    fig, axes = plt.subplots(rows, cols, figsize=(WIDTH, height), layout="constrained", squeeze=False, **kw)
    fig.get_layout_engine().set(w_pad=0.05, h_pad=0.04, wspace=0.04, hspace=0.05)
    return fig, axes


def save(fig, name: str) -> None:
    # SVG, because an accessible PDF (PDF/UA) cannot embed other PDFs; without a date, so that a rebuild is identical.
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight", pad_inches=0.02, metadata={"Date": None})
    plt.close(fig)


def grid(ax, axis: str = "y") -> None:
    ax.grid(axis=axis, color=GRID, lw=0.5)
    ax.set_axisbelow(True)


def percent(ax, axis: str = "y") -> None:
    getattr(ax, f"{axis}axis").set_major_formatter(PercentFormatter(1.0, decimals=0, symbol=""))


def short(k: int) -> str:
    return f"{k // 1000}k" if k >= 1000 else str(k)


def k_axis(ax, ks: list[int], skip: tuple[int, ...] = (5000,)) -> None:
    ax.set_xscale("log")
    ax.set_xticks(ks, ["" if k in skip else short(k) for k in ks])
    ax.minorticks_off()
    ax.tick_params(axis="x", labelsize=7)
    ax.set_xlabel("anchor pairs $k$")


def key(color: str = INK, ls: str = "-", marker: str | None = None, filled: bool = True, lw: float = 1.5, ms: float = 4) -> Line2D:
    return Line2D([], [], color=color, ls=ls, lw=lw, marker=marker, ms=ms, mfc=color if filled else "white", mec=color, mew=0.9)


def below(fig, keys: list[tuple[Line2D, str]], ncol: int) -> None:
    fig.legend([h for h, _ in keys], [l for _, l in keys], loc="outside lower center", ncol=ncol, columnspacing=1.6, handletextpad=0.5)


def arrow(s: str, t: str) -> str:
    return f"{ROW[s]} $\\rightarrow$ {ROW[t]}"


def top(bed: Bed, direction: str = "forward", adapter: str = MAIN) -> dict[tuple[str, str], dict]:
    """The headline configuration: in-domain anchors, all of them, ordered pairs of open models."""
    rows = bed.pick(anchors="in-domain", adapter=adapter, k=bed.kmax(adapter=adapter), direction=direction)
    return {(r["source"], r["target"]): r for r in rows if bed.open_pair(r)}


def identity(ax, lo: float, hi: float) -> None:
    ax.plot([lo, hi], [lo, hi], color=FAINT, lw=0.8, zorder=1)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")


def bed_keys(beds: list[Bed]) -> list[tuple[Line2D, str]]:
    return [(key(MARKS[b.name][1], "", MARKS[b.name][0]), BEDS[b.name]) for b in beds]


def sizes(bed: Bed) -> dict:
    """Passages, queries and anchors of a testbed, as evaluate.py counted them."""
    return next(r for r in bed.rows if r["kind"] == "testbed")


# ---------------------------------------------------------------- reference points


def fig_native(beds: list[Bed]) -> None:
    fig, axes = panels(1, len(beds), 2.1, sharey=True)
    for ax, bed in zip(axes[0], beds):
        weak = next(iter(bed.of("upgrade-native", space=WEAK)), None)
        rows = [(m, bed.native[m], BLUE) for m in bed.open] + ([(WEAK, weak, MUTED)] if weak else []) + [("bm25", bed.bm25, MUTED)]
        for i, (m, r, color) in enumerate(rows):
            ax.plot([r["ndcg10"], r["recall10"]], [i, i], color=FAINT, lw=1.2, zorder=2)
            ax.plot(r["recall10"], i, "o", ms=4.2, mfc="white", mec=color, mew=1.0, zorder=3)
            ax.plot(r["ndcg10"], i, "o", ms=4.6, mfc=color, mec="white", mew=0.6, zorder=4)
        ax.axhline(len(bed.open) - 0.5, color=GRID, lw=0.6)
        ax.set_yticks(range(len(rows)), [ROW[m] for m, _, _ in rows])
        ax.set_ylim(len(rows) - 0.4, -0.6)
        ax.set_xlim(0, 1.02)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1], ["0", "", "0.5", "", "1"])
        ax.tick_params(axis="y", length=0)
        ax.set_title(BEDS[bed.name])
        grid(ax, "x")
    below(fig, [(key(BLUE, "", "o"), "nDCG@10"), (key(BLUE, "", "o", filled=False), "Recall@10"),
                (key(MUTED, "", "o"), "weak old model and BM25")], 3)
    save(fig, "native")


def fig_similarity(beds: list[Bed]) -> None:
    """Two rotation-invariant similarities of the anchor matrices: neighbour overlap below the diagonal, CKA above."""
    sims = [v for bed in beds for (label, a, b), v in bed.sim.items() if label == "in-domain"]
    span = {m: (min(v[m] for v in sims), max(v[m] for v in sims)) for m in ("knn", "cka")}
    fig, axes = panels(1, len(beds), 2.75)
    for ax, bed in zip(axes[0], beds):
        spaces = bed.open + bed.closed
        n = len(spaces)
        for i, a in enumerate(spaces):
            for j, b in enumerate(spaces):
                v = bed.sim.get(("in-domain", a, b))
                if i == j or not v:
                    continue
                m, cmap = ("knn", BLUES) if i > j else ("cka", ORANGES)
                lo, hi = span[m]
                x = 0.12 + 0.76 * (v[m] - lo) / (hi - lo)
                ax.add_patch(plt.Rectangle((j - 0.47, i - 0.47), 0.94, 0.94, color=cmap(x), lw=0))
                ax.text(j, i, f"{v[m]:.2f}"[1:], ha="center", va="center", fontsize=7.5, color="white" if x > 0.55 else INK)
        ax.plot([-0.5, n - 0.5], [-0.5, n - 0.5], color=FAINT, lw=0.6)
        ax.set_xlim(-0.5, n - 0.5)
        ax.set_ylim(n - 0.5, -0.5)
        ax.set_aspect("equal")
        ax.set_xticks(range(n), [ROW[s] for s in spaces], rotation=38, ha="right", rotation_mode="anchor")
        ax.set_yticks(range(n), [ROW[s] for s in spaces])
        ax.tick_params(length=0, labelsize=7.5)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_title(BEDS[bed.name])
    below(fig, [(Line2D([], [], color=ORANGES(0.6), marker="s", ls="", ms=7), "above the diagonal: linear CKA"),
                (Line2D([], [], color=BLUES(0.6), marker="s", ls="", ms=7), "below the diagonal: overlap of the ten nearest anchors")], 2)
    save(fig, "similarity")


# ---------------------------------------------------------------- translation between open models


def fig_curves(beds: list[Bed]) -> None:
    fig, axes = panels(1, len(beds), 2.75, sharey=True)
    for ax, bed in zip(axes[0], beds):
        ks = bed.ks()
        pairs = bed.pairs()
        for s, t in pairs:  # spread: one thin line per ordered pair (orthogonal map, index translation)
            ys = [mean(bed.rel(r) for r in bed.pick(source=s, target=t, anchors="in-domain", adapter=MAIN, direction="forward", k=k)) for k in ks]
            ax.plot(ks, ys, color=FAINT, lw=0.5, zorder=1)
        for adapter in ("ridge", "procrustes"):
            for direction, style in (("forward", "-"), ("backward", DASH)):
                ys = [mean(bed.rel(r) for r in bed.pick(anchors="in-domain", adapter=adapter, direction=direction, k=k) if bed.open_pair(r)) for k in ks]
                ax.plot(ks, ys, ls=style, color=MAP_COLOR[adapter], lw=1.5, marker="o", ms=2.8, zorder=3)
        for direction, marker in (("forward", "s"), ("backward", "D")):
            mk = sorted({r["k"] for r in bed.pick(adapter="mlp", direction=direction)})
            ys = [mean(bed.rel(r) for r in bed.pick(anchors="in-domain", adapter="mlp", direction=direction, k=k) if bed.open_pair(r)) for k in mk]
            ax.plot(mk, ys, marker, color=MAP_COLOR["mlp"], ms=4.4, mfc="white", mew=1.1, ls="none", zorder=4)
        ax.axhline(mean(bed.stay(s, t) for s, t in pairs), color=INK, lw=0.8, ls=":")
        ax.axhline(1.0, color=INK, lw=0.5)
        dim = mode(bed.native[m]["dim"] for m in bed.open)  # from here on an orthogonal map has more anchors than dimensions
        ax.axvline(dim, color=MUTED, lw=0.5, zorder=1)
        ax.text(dim * 1.13, 0.03, f"$k$ = {dim:,},\nthe dimension", fontsize=6.5, color=MUTED, va="bottom", linespacing=1.15)
        k_axis(ax, ks)
        ax.set_title(BEDS[bed.name])
        grid(ax)
    axes[0][0].set_ylabel("nDCG@10 in % of full re-embed")
    axes[0][0].set_ylim(0, 1.1)
    percent(axes[0][0])
    below(fig, [(key(BLUE, marker="o", ms=2.8), "orthogonal, index translation"), (key(ORANGE, marker="o", ms=2.8), "ridge, index translation"),
                (key(GREEN, "", "s", filled=False), "residual network, index translation"),
                (key(BLUE, DASH, "o", ms=2.8), "orthogonal, query translation"), (key(ORANGE, DASH, "o", ms=2.8), "ridge, query translation"),
                (key(GREEN, "", "D", filled=False), "residual network, query translation"),
                (key(FAINT, lw=0.8), "single pairs (orthogonal, index)"), (key(INK, ":", lw=0.8), "stay on the old model (mean)")], 3)
    save(fig, "curves")


def fig_matrix(bed: Bed) -> None:
    k = bed.kmax()
    rows = bed.closed + bed.open
    cols = bed.open
    lo, hi = 0.6, 1.0
    fig, axes = panels(1, 2, 0.33 * len(rows) + 1.05, sharey=True)
    for ax, direction in zip(axes[0], ("forward", "backward")):
        for r in bed.pick(anchors="in-domain", adapter=MAIN, k=k, direction=direction):
            i, j, v = rows.index(r["source"]), cols.index(r["target"]), bed.rel(r)
            x = 0.08 + 0.88 * (min(max(v, lo), hi) - lo) / (hi - lo)
            beats = r["source"] in bed.open and v >= bed.stay(r["source"], r["target"])
            ax.add_patch(plt.Rectangle((j - 0.47, i - 0.46), 0.94, 0.92, color=BLUES(x), lw=0))
            ax.text(j, i, f"{100 * v:.0f}" + ("*" if beats else ""), ha="center", va="center", color="white" if x > 0.55 else INK, fontsize=8)
        ax.set_xlim(-0.5, len(cols) - 0.5)
        ax.set_ylim(len(rows) - 0.5, -0.5)
        ax.tick_params(length=0)
        ax.set_xticks(range(len(cols)), [NAMES[c] for c in cols], rotation=30, ha="right", rotation_mode="anchor")
        ax.set_yticks(range(len(rows)), [NAMES[r] for r in rows])
        ax.set_xlabel("target space (new model)")
        ax.set_title(("Index translation" if direction == "forward" else "Query translation") + f", $k$ = {k:,}")
        for sp in ax.spines.values():
            sp.set_visible(False)
    axes[0][0].set_ylabel("source space (old model)")
    save(fig, f"matrix-{bed.name}")


def fig_stay(beds: list[Bed]) -> None:
    """Translated index against the old model's own index, pair by pair, with the interval of the query sample."""
    pairs = beds[0].pairs()
    gap = 1.3  # room for the heading of the second group
    ys = [i + (0 if same_family(*p) else gap) for i, p in enumerate(pairs)]
    within = sum(same_family(*p) for p in pairs)
    fig, axes = panels(1, len(beds), 4.35, sharey=True, sharex=True)
    for ax, bed in zip(axes[0], beds):
        rows = top(bed)
        for p, y in zip(pairs, ys):
            r = rows[p]
            lo, hi = 100 * r["stay_lo"], 100 * r["stay_hi"]
            diff = 100 * (r["ndcg10"] - bed.native[p[0]]["ndcg10"])
            ax.plot([lo, hi], [y, y], color=BLUE, lw=1.3, zorder=2)
            ax.plot(diff, y, "o", ms=4.4, mfc="white" if lo <= 0 <= hi else BLUE, mec=BLUE, mew=1.0, zorder=3)
        ax.axvline(0, color=INK, lw=0.7, zorder=1)
        ax.set_title(BEDS[bed.name])
        ax.tick_params(axis="y", length=0)
        grid(ax, "x")
    first = axes[0][0]
    first.set_yticks(ys, [arrow(*p) for p in pairs], fontsize=7.5)
    first.set_ylim(ys[-1] + 0.7, -1.9)
    for ax in axes[0]:
        ax.axhline(within - 0.5 + gap / 2 - 0.55, color=GRID, lw=0.6)
    first.text(0.03, -1.05, "within the XLM-R family", transform=first.get_yaxis_transform(), fontsize=7.5, color=MUTED, va="center")
    first.text(0.03, within + gap / 2 - 0.45, "across families", transform=first.get_yaxis_transform(), fontsize=7.5, color=MUTED, va="center")
    axes[0][len(beds) // 2].set_xlabel("nDCG@10 of the translated index minus nDCG@10 of the old model, in points")
    below(fig, [(key(BLUE, marker="o"), "below the old model beyond the uncertainty of the query sample"),
                (key(BLUE, marker="o", filled=False), "tied with the old model")], 2)
    save(fig, "stay")


def fig_overlap(beds: list[Bed]) -> None:
    """Agreement with the new model's top ten against retrieval quality, for a translated and for the old index."""
    fig, axes = panels(1, len(beds), 2.5, sharey=True, sharex=True)
    for ax, bed in zip(axes[0], beds):
        rows = top(bed)
        old = [(bed.native_overlap[p]["overlap10"], bed.stay(*p)) for p in rows if p in bed.native_overlap]
        new = [(r["overlap10"], bed.rel(r)) for r in rows.values()]
        ax.axhline(1.0, color=INK, lw=0.5)
        ax.scatter(*zip(*old), s=20, marker="D", facecolor="white", edgecolor=ORANGE, lw=1.0, zorder=3)
        ax.scatter(*zip(*new), s=22, marker="o", facecolor=BLUE, edgecolor="white", lw=0.5, zorder=4)
        ax.set_title(BEDS[bed.name])
        ax.set_xlabel("share of the re-embed's top ten, %")
        grid(ax, "both")
        percent(ax, "x")
    axes[0][0].set_xlim(0.3, 0.9)
    axes[0][0].set_ylabel("nDCG@10 in % of full re-embed")
    percent(axes[0][0])
    below(fig, [(key(BLUE, "", "o"), "translated index, queries of the new model"),
                (key(ORANGE, "", "D", filled=False), "old model's own index and queries")], 2)
    save(fig, "overlap")


def fig_fidelity(beds: list[Bed]) -> None:
    """How faithfully a map reproduces query vectors against how well the translated queries retrieve."""
    fig, axes = panels(1, len(beds), 2.5, sharey=True, sharex=True)
    for ax, bed in zip(axes[0], beds):
        pts = {}
        for adapter in ("procrustes", "ridge"):
            rows = top(bed, "backward", adapter)
            cos = {(r["source"], r["target"]): r["cos_queries_bwd"] for r in bed.fidelity if r["adapter"] == adapter and "cos_queries_bwd" in r}
            pts[adapter] = {p: (cos[p], bed.rel(r)) for p, r in rows.items() if p in cos}
        for p in pts["procrustes"]:
            if p in pts["ridge"]:
                ax.plot(*zip(pts["procrustes"][p], pts["ridge"][p]), color=FAINT, lw=0.5, zorder=1)
        ax.scatter(*zip(*pts["ridge"].values()), s=20, marker="D", facecolor=ORANGE, edgecolor="white", lw=0.5, zorder=3)
        ax.scatter(*zip(*pts["procrustes"].values()), s=22, marker="o", facecolor=BLUE, edgecolor="white", lw=0.5, zorder=4)
        ax.axhline(1.0, color=INK, lw=0.5)
        ax.set_title(BEDS[bed.name])
        ax.set_xlabel("cosine to the true query vector")
        grid(ax, "both")
    axes[0][0].set_ylabel("nDCG@10 in % of full re-embed")
    percent(axes[0][0])
    below(fig, [(key(BLUE, "", "o"), "orthogonal map"), (key(ORANGE, "", "D"), "ridge regression"),
                (key(FAINT, lw=0.8), "the same pair of spaces")], 3)
    save(fig, "fidelity")


def fig_controls(beds: list[Bed]) -> None:
    """Two controls for the orthogonal map, pair by pair: centring, and the role of the anchors."""
    fig, axes = panels(2, len(beds), 4.5)
    for ax, bed in zip(axes[0], beds):
        centred = top(bed)
        plain = {(r["source"], r["target"]): r for r in bed.of("uncentred", direction="forward", k=bed.kmax())}
        pts = {p: (bed.rel(centred[p]), bed.rel(plain[p])) for p in centred if p in plain}
        identity(ax, 0.0, 1.08)
        ax.scatter(*zip(*pts.values()), s=22, marker="o", facecolor=BLUE, edgecolor="white", lw=0.5, zorder=3)
        worst = min(pts, key=lambda p: pts[p][1] - pts[p][0])
        ax.annotate(arrow(*worst), pts[worst], xytext=(-6, 0), textcoords="offset points", ha="right", va="center", fontsize=7, color=MUTED,
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8})
        ax.set_title(BEDS[bed.name])
        ax.set_xlabel("with centring")
    axes[0][0].set_ylabel("without centring")
    for ax, bed in zip(axes[1], beds):
        for adapter, marker, size in (("ridge", "D", 20), ("procrustes", "o", 22)):
            roles = {role: {(r["source"], r["target"]): bed.rel(r) for r in bed.of("role", role=role, adapter=adapter, k=bed.kmax())}
                     for role in ("document", "query")}
            pts = [(roles["document"][p], roles["query"][p]) for p in roles["document"] if p in roles["query"]]
            ax.scatter(*zip(*pts), s=size, marker=marker, facecolor=MAP_COLOR[adapter], edgecolor="white", lw=0.5, zorder=3 if adapter == "ridge" else 4)
        identity(ax, 0.0, 1.08)
        ax.set_xlabel("anchors in the document role")
    axes[1][0].set_ylabel("anchors in the query role")
    for ax in axes.flat:
        percent(ax, "x")
        percent(ax, "y")
        grid(ax, "both")
    below(fig, [(key(BLUE, "", "o"), "orthogonal map"), (key(ORANGE, "", "D"), "ridge regression"), (key(FAINT, lw=0.8), "no difference")], 3)
    save(fig, "controls")


# ---------------------------------------------------------------- weak old model, mixed index, commercial spaces


def fig_upgrade(beds: list[Bed]) -> None:
    fig, axes = panels(1, len(beds), 2.6, sharey=True)
    for ax, bed in zip(axes[0], beds):
        stay = next(iter(bed.of("upgrade-native", space=WEAK)), None)
        if not stay:
            continue
        ks = sorted({r["k"] for r in bed.of("upgrade", source=WEAK, anchors="in-domain")})
        ax.axhline(mean(bed.native[m]["ndcg10"] for m in bed.open), color=INK, lw=0.8)
        ax.axhline(stay["ndcg10"], color=INK, lw=0.8, ls=":")
        ax.axhline(bed.bm25["ndcg10"], color=MUTED, lw=0.8, ls=LEXICAL)
        for adapter, direction, style in (("ridge", "forward", "-"), ("procrustes", "backward", DASH), ("procrustes", "forward", "-")):
            ys = [mean(r["ndcg10"] for r in bed.of("upgrade", source=WEAK, anchors="in-domain", adapter=adapter, direction=direction, k=k)) for k in ks]
            ax.plot(ks, ys, ls=style, color=MAP_COLOR[adapter], lw=1.5, marker="o", ms=2.8, zorder=3)
        k_axis(ax, ks)
        ax.set_title(BEDS[bed.name])
        grid(ax)
    axes[0][0].set_ylabel("nDCG@10")
    axes[0][0].set_ylim(0, 1.0)
    below(fig, [(key(BLUE, marker="o", ms=2.8), "orthogonal, index translation"), (key(ORANGE, marker="o", ms=2.8), "ridge, index translation"),
                (key(BLUE, DASH, "o", ms=2.8), "orthogonal, query translation"),
                (key(INK, lw=0.8), "full re-embed (mean of the five)"), (key(INK, ":", lw=0.8), "stay on MiniLM-L12"),
                (key(MUTED, LEXICAL, lw=0.8), "BM25")], 3)
    save(fig, "upgrade")


def fig_mixed(beds: list[Bed]) -> None:
    fig, axes = panels(2, len(beds), 4.0, sharex=True, sharey="row")
    shares = [0, 0.1, 0.5, 0.9, 1]
    for col, bed in enumerate(beds):
        full = top(bed)
        mixed = {(r["source"], r["target"], r["share"]): r for r in bed.of("mixed")}
        quality = {p: [1.0] + [bed.rel(mixed[(*p, s)]) for s in shares[1:-1]] + [bed.rel(full[p])] for p in full if (*p, 0.5) in mixed}
        inside = {p: [0.0] + [mixed[(*p, s)]["translated_in_top10"] for s in shares[1:-1]] + [1.0] for p in quality}
        for ax, lines in ((axes[0][col], quality), (axes[1][col], inside)):
            for ys in lines.values():
                ax.plot(shares, ys, color=FAINT, lw=0.5, zorder=1)
            ax.plot(shares, np.mean(list(lines.values()), axis=0), color=BLUE, lw=1.5, marker="o", ms=3.2, zorder=3)
            ax.set_xticks(shares, ["0", "10", "50", "90", "100"])
            grid(ax)
        axes[0][col].axhline(1.0, color=INK, lw=0.5)
        axes[0][col].set_title(BEDS[bed.name])
        axes[1][col].plot([0, 1], [0, 1], color=INK, lw=0.8, ls=":", zorder=2)
        axes[1][col].set_xlabel("translated share of the index, %")
        for tick, ha in zip(axes[1][col].get_xticklabels()[-2:], ("right", "left")):  # 90 and 100 lie close together
            tick.set_ha(ha)
    axes[0][0].set_ylabel("nDCG@10, % of re-embed")
    axes[1][0].set_ylabel("translated in top ten, %")
    percent(axes[0][0])
    percent(axes[1][0])
    below(fig, [(key(BLUE, marker="o", ms=3.2), "mean over the pairs"), (key(FAINT, lw=0.8), "single pairs"),
                (key(INK, ":", lw=0.8), "share in the top ten equal to share in the index")], 3)
    save(fig, "mixed")


def fig_closed(beds: list[Bed]) -> None:
    beds = [b for b in beds if b.closed]
    fig, axes = panels(1, len(beds), 2.6, sharey=True)
    for ax, bed in zip(axes[0], beds):
        src = bed.closed[0]
        ks = bed.ks()
        spread = [[bed.rel(r) for r in bed.pick(anchors="in-domain", adapter=MAIN, direction="forward", k=k) if bed.open_pair(r)] for k in ks]
        ax.fill_between(ks, [min(v) for v in spread], [max(v) for v in spread], color="#ececec", lw=0, zorder=1)
        ax.plot(ks, [mean(v) for v in spread], color=MUTED, lw=1.0, zorder=2)
        for t in bed.open:
            ys = [mean(bed.rel(r) for r in bed.pick(source=src, target=t, anchors="in-domain", adapter=MAIN, direction="forward", k=k)) for k in ks]
            ax.plot(ks, ys, color=BLUE, lw=0.5, alpha=0.55, zorder=3)
        for direction, style in (("backward", DASH), ("forward", "-")):
            ys = [mean(bed.rel(r) for r in bed.pick(source=src, anchors="in-domain", adapter=MAIN, direction=direction, k=k)) for k in ks]
            ax.plot(ks, ys, ls=style, color=BLUE, lw=1.5, marker="o", ms=2.8, zorder=4)
        ax.axhline(1.0, color=INK, lw=0.5)
        k_axis(ax, ks)
        ax.set_title(f"{NAMES[src]} on {BEDS[bed.name]}")
        grid(ax)
    axes[0][0].set_ylabel("nDCG@10 in % of full re-embed")
    axes[0][0].set_ylim(0, 1.1)
    percent(axes[0][0])
    below(fig, [(key(BLUE, marker="o", ms=2.8), "index translation, mean of five targets"), (key(BLUE, DASH, "o", ms=2.8), "query translation, mean"),
                (key(BLUE, lw=0.6), "index translation, single targets"),
                (key(MUTED, lw=1.0), "pairs of open models, mean"), (Patch(color="#ececec", lw=0), "pairs of open models, range")], 3)
    save(fig, "closed")


# ---------------------------------------------------------------- anchors


def fig_anchor_source(beds: list[Bed]) -> None:
    fig, axes = panels(1, len(beds), 2.6, sharey=True)
    for ax, bed in zip(axes[0], beds):
        alt = ALT[bed.name]
        both = {(r["source"], r["target"]) for r in bed.pick(anchors=alt) if bed.open_pair(r)}
        for label, color in ((alt, ORANGE), ("in-domain", BLUE)):
            for direction, style in (("backward", DASH), ("forward", "-")):
                ks = bed.ks(label)
                ys = [mean(bed.rel(r) for r in bed.pick(anchors=label, adapter=MAIN, direction=direction, k=k) if (r["source"], r["target"]) in both) for k in ks]
                ax.plot(ks, ys, ls=style, color=color, lw=1.5, marker="o", ms=2.8)
        ax.axhline(1.0, color=INK, lw=0.5)
        k_axis(ax, sorted(set(bed.ks("in-domain")) | set(bed.ks(alt))), skip=())
        ax.set_title(BEDS[bed.name])
        ax.legend([key(BLUE), key(ORANGE)], ["in-domain anchors", f"{EXTERNAL[alt]} anchors"], loc="lower right", fontsize=7.5)
        grid(ax)
    axes[0][0].set_ylabel("nDCG@10 in % of full re-embed")
    axes[0][0].set_ylim(0, 1.1)
    percent(axes[0][0])
    below(fig, [(key(INK), "index translation"), (key(INK, DASH), "query translation")], 2)
    save(fig, "anchor-source")


def predict_points(bed: Bed, direction: str = "forward") -> list[dict]:
    k = bed.kmax()
    out = []
    for r in bed.pick(anchors="in-domain", adapter=MAIN, k=k, direction=direction):
        sim = bed.sim.get(("in-domain", r["source"], r["target"]))
        if sim:
            out.append({"bed": bed.name, "pair": (r["source"], r["target"]), "rel": bed.rel(r), **{m: sim[m] for m in ("rsa", "cka", "knn")}})
    return out


def fig_predict(beds: list[Bed]) -> None:
    """Three similarities of the anchor matrices and the hit rate of translated held-out anchors against the outcome."""
    measures = [("knn", "overlap of the ten nearest anchors"), ("rsa", "RSA (Spearman)"), ("cka", "linear CKA"),
                ("acc1", "held-out anchors nearest to their counterpart, %")]
    fig, axes = panels(2, 2, 4.5, sharey=True)
    for ax, (m, label) in zip(axes.flat, measures):
        for bed in beds:
            pts = predict_points(bed)
            if m == "acc1":
                hit = {(r["source"], r["target"]): r["acc1"] for r in bed.of("retrieval", anchors="in-domain")}
                pts = [dict(p, acc1=hit[p["pair"]]) for p in pts if p["pair"] in hit]
            mk, col, size = MARKS[bed.name]
            ax.scatter([p[m] for p in pts], [p["rel"] for p in pts], marker=mk, s=size, facecolor=col, edgecolor="white", lw=0.5, zorder=3)
        ax.axhline(1.0, color=INK, lw=0.5)
        ax.set_xlabel(label)
        grid(ax, "both")
    percent(axes[1][1], "x")
    for row in axes:
        row[0].set_ylabel("nDCG@10 in % of full re-embed")
    percent(axes[0][0])
    below(fig, bed_keys(beds), 3)
    save(fig, "predict")


# ---------------------------------------------------------------- hybrid search


def fig_hybrid(beds: list[Bed]) -> None:
    """Dense, lexical and fused retrieval: mean and range over the pairs (translated) or the models (re-embedded)."""
    labels = ["Re-embedded index", "fused with BM25, equal weights", "fused with BM25, tuned weight",
              "Translated index", "fused with BM25, equal weights", "fused with BM25, tuned weight", "BM25 alone"]
    ys = [0, 1, 2, 3.5, 4.5, 5.5, 7]
    fig, axes = panels(1, len(beds), 2.75, sharey=True)

    def mark(ax, values, y, color, marker="o"):
        values = list(values)
        ax.plot([min(values), max(values)], [y, y], color=color, lw=1.3, zorder=2)
        ax.plot(mean(values), y, marker, ms=4.6, mfc=color, mec="white", mew=0.6, zorder=3)

    for ax, bed in zip(axes[0], beds):
        native = {r["space"]: r for r in bed.of("hybrid-native")}
        mark(ax, (bed.native[m]["ndcg10"] for m in bed.open), ys[0], INK)
        mark(ax, (native[m]["fused"] for m in bed.open), ys[1], INK)
        mark(ax, (native[m]["tuned"] for m in bed.open), ys[2], INK)
        k = bed.kmax()
        sets = [("in-domain", k, BLUE, "o", -0.17 if bed.name in ALT else 0)]
        if bed.name in ALT:
            sets.append((ALT[bed.name], min(k, bed.kmax(ALT[bed.name])), ORANGE, "D", 0.17))
        for anchors, size, color, marker, shift in sets:
            rows = bed.of("hybrid", anchors=anchors, k=size)
            for field, y in zip(("bridge", "fused", "tuned"), ys[3:6]):
                mark(ax, (r[field] for r in rows), y + shift, color, marker)
        ax.axvline(bed.bm25["ndcg10"], color=MUTED, lw=0.8, ls=LEXICAL, zorder=1)
        ax.plot(bed.bm25["ndcg10"], ys[6], "o", ms=4.6, mfc=MUTED, mec="white", mew=0.6, zorder=3)
        ax.set_title(BEDS[bed.name])
        ax.set_xlabel("nDCG@10")
        ax.tick_params(axis="y", length=0)
        ax.margins(x=0.12)
        grid(ax, "x")
    axes[0][0].set_yticks(ys, labels)
    axes[0][0].set_ylim(7.6, -0.6)
    for tick, y in zip(axes[0][0].get_yticklabels(), ys):
        tick.set_color(INK if y in (0, 3.5, 7) else MUTED)
    below(fig, [(key(INK, marker="o"), "re-embedded: the five models"), (key(BLUE, marker="o"), "translated with in-domain anchors"),
                (key(ORANGE, marker="D"), "translated with external anchors"), (key(MUTED, LEXICAL, lw=0.8), "BM25")], 2)
    save(fig, "hybrid")


# ---------------------------------------------------------------- overviews


def fig_glance(beds: list[Bed]) -> None:
    """Every setting of the study on one scale: mean and range over the pairs, in per cent of a full re-embed."""
    labels = ["Index translation", "Query translation", "Index translation with 1,000 anchors", "with external anchors",
              "from a commercial space", "into a mixed index, nine tenths translated", "from the weak MiniLM-L12"]
    ys = [0, 1, 2.45, 3.45, 4.45, 5.45, 6.45]

    def settings(bed: Bed) -> list[list[float]]:
        k, alt = bed.kmax(), ALT.get(bed.name)
        ka = min(k, bed.kmax(alt)) if alt and bed.pick(anchors=alt) else 0  # as many external anchors as in-domain ones
        own = lambda **want: [bed.rel(r) for r in bed.pick(adapter=MAIN, **want) if bed.open_pair(r)]
        return [
            own(anchors="in-domain", k=k, direction="forward"),
            own(anchors="in-domain", k=k, direction="backward"),
            own(anchors="in-domain", k=1000, direction="forward"),
            own(anchors=alt, k=ka, direction="forward"),
            [bed.rel(r) for r in bed.pick(anchors="in-domain", adapter=MAIN, k=k, direction="forward") if not bed.open_pair(r)],
            [bed.rel(r) for r in bed.of("mixed", share=0.9)],
            [bed.rel(r) for r in bed.of("upgrade", source=WEAK, anchors="in-domain", adapter=MAIN, direction="forward", k=k)],
        ]

    fig, axes = panels(1, 1, 3.15)
    ax = axes[0][0]
    for i, bed in enumerate(beds):
        mk, col, size = MARKS[bed.name]
        shift = 0.25 * (i - (len(beds) - 1) / 2)
        for y, values in zip(ys, settings(bed)):
            if values:
                ax.plot([min(values), max(values)], [y + shift, y + shift], color=col, lw=0.9, zorder=2)
                ax.scatter(mean(values), y + shift, marker=mk, s=size, facecolor=col, edgecolor="white", lw=0.5, zorder=3)
    ax.axvline(1.0, color=INK, lw=0.5, zorder=1)
    ax.axhline((ys[1] + ys[2]) / 2, color=GRID, lw=0.6)
    ax.set_yticks(ys, labels)
    for tick, y in zip(ax.get_yticklabels(), ys):
        tick.set_color(INK if y < ys[3] else MUTED)
    ax.set_ylim(ys[-1] + 0.6, -0.6)
    ax.set_xlim(0, 1.04)
    ax.set_xticks(np.arange(0, 1.01, 0.1))
    ax.set_xlabel("nDCG@10 in % of full re-embed")
    ax.tick_params(axis="y", length=0)
    percent(ax, "x")
    grid(ax, "x")
    below(fig, bed_keys(beds) + [(key(MUTED, lw=0.9), "lowest to highest pair")], 4)
    save(fig, "glance")


def fig_testbeds(beds: list[Bed]) -> None:
    """What each testbed consists of, to scale: the passages that are searched and the anchor sets that are not."""
    start, height, thin = 190_000, 0.5, 0.2
    own_note = {"wiki-de": "of judged pages", "miracl-de": "judged", "archive": "of the archive"}
    said = {"va": "center", "fontsize": 7.5}
    fig, axes = panels(1, 1, 0.55 * len(beds) + 0.45)
    ax = axes[0][0]
    for y, bed in enumerate(beds):
        size = sizes(bed)
        back = BACKGROUND.get(bed.name, 0)
        own = size["corpus"] - back
        if back:
            ax.add_patch(plt.Rectangle((0, y - height / 2), back, height, color=FAINT, lw=0))
            ax.text(back / 2, y, f"{back:,} background", ha="center", color=INK, **said)
        ax.add_patch(plt.Rectangle((back, y - height / 2), own, height, color=MUTED, lw=0))
        wide = own > 25_000  # room for the number inside the block
        if wide:
            ax.text(back + own / 2, y, f"{own:,}", ha="center", color="white", **said)
        ax.text(back + own + 2_500, y, own_note[bed.name] if wide else f"{own:,} {own_note[bed.name]}", color=INK, **said)
        sets = size["anchors"]
        for i, (label, count) in enumerate(sets.items()):
            at = y + 0.27 * (i - (len(sets) - 1) / 2)
            ax.add_patch(plt.Rectangle((start, at - thin / 2), count, thin, color=BLUE if label == "in-domain" else ORANGE, lw=0))
            ax.text(start + max(sets.values()) + 2_500, at, f"{count:,} {EXTERNAL.get(label, label)}", color=INK, **said)
    ax.text(0, -0.42, "searched passages", fontsize=7.5, color=MUTED, va="bottom")
    ax.text(start, -0.42, "anchor passages, never searched", fontsize=7.5, color=MUTED, va="bottom")
    ax.set_yticks(range(len(beds)), [f"{BEDS[b.name]}\n{sizes(b)['queries']} queries\nrelevant: {RELEVANCE[b.name]}" for b in beds], linespacing=1.15)
    ax.set_ylim(len(beds) - 0.55, -0.75)
    ax.set_xlim(0, 282_000)
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    save(fig, "testbeds")


# ---------------------------------------------------------------- reading aids for the main results


def fig_ceiling(beds: list[Bed]) -> None:
    """The old model is the ceiling: what it scores when kept against what its translated index scores."""
    fig, axes = panels(1, len(beds), 2.75, sharex=True, sharey=True)
    for ax, bed in zip(axes[0], beds):
        rows = top(bed)
        identity(ax, 0.0, 1.0)
        ax.scatter([bed.native[s]["ndcg10"] for s, _ in rows], [r["ndcg10"] for r in rows.values()], s=15, marker="o",
                   facecolor=BLUE, edgecolor="white", lw=0.4, zorder=4)
        weak = next(iter(bed.of("upgrade-native", space=WEAK)), None)
        if weak:
            moved = bed.of("upgrade", source=WEAK, anchors="in-domain", adapter=MAIN, direction="forward", k=bed.kmax())
            ax.scatter([weak["ndcg10"]] * len(moved), [r["ndcg10"] for r in moved], s=14, marker="D", facecolor=ORANGE, edgecolor="white", lw=0.4, zorder=3)
        ax.set_title(BEDS[bed.name])
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1], ["0", "", "0.5", "", "1"])
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1], ["0", "", "0.5", "", "1"])
        grid(ax, "both")
    axes[0][0].set_ylabel("nDCG@10 of its translated index")
    axes[0][len(beds) // 2].set_xlabel("nDCG@10 of the old model, kept as it is")
    axes[0][0].text(0.05, 0.94, "above the line: the\ntranslated index is better", fontsize=7, color=MUTED, va="top", linespacing=1.15)
    below(fig, [(key(BLUE, "", "o"), "one of the five open models as the old model"), (key(ORANGE, "", "D"), "MiniLM-L12 as the old model"),
                (key(FAINT, lw=0.8), "no difference")], 3)
    save(fig, "ceiling")


def fig_depth(beds: list[Bed]) -> None:
    """Three depths of one ranking: a translation loses more at the top of the list than further down."""
    metrics = [("ndcg10", "nDCG@10"), ("recall10", "Recall@10"), ("recall100", "Recall@100")]
    fig, axes = panels(1, len(beds), 2.55, sharey=True)
    for ax, bed in zip(axes[0], beds):
        for direction, style, shift in (("backward", DASH, 0.09), ("forward", "-", -0.09)):
            rows = top(bed, direction).values()
            values = [[bed.rel(r, m) for r in rows] for m, _ in metrics]
            xs = np.arange(len(metrics)) + shift
            ax.plot(xs, [mean(v) for v in values], ls=style, color=BLUE, lw=1.5, zorder=3)
            for x, v in zip(xs, values):
                ax.plot([x, x], [min(v), max(v)], color=BLUE, lw=0.9, zorder=2)
                ax.plot(x, mean(v), "o", ms=4.4, mfc=BLUE if direction == "forward" else "white", mec=BLUE, mew=1.0, zorder=4)
        ax.axhline(1.0, color=INK, lw=0.5)
        ax.set_xticks(range(len(metrics)), [label for _, label in metrics])
        ax.set_xlim(-0.45, len(metrics) - 0.55)
        ax.tick_params(axis="x", labelsize=7.5)
        ax.set_title(BEDS[bed.name])
        grid(ax)
    axes[0][0].set_ylabel("in % of full re-embed")
    axes[0][0].set_ylim(0.6, 1.03)
    percent(axes[0][0])
    below(fig, [(key(BLUE, marker="o"), "index translation"), (key(BLUE, DASH, "o", filled=False), "query translation"),
                (key(BLUE, lw=0.9), "lowest to highest pair")], 3)
    save(fig, "depth")


def fig_paths(beds: list[Bed]) -> None:
    """Two ways to a re-embedded index: replace the translated vectors in place, or build the new index beside the old one."""
    translated = [1, 0.9, 0.5, 0.1, 0]  # share of the index that still holds translated vectors
    done = [1 - x for x in translated]
    fig, axes = panels(1, len(beds), 2.55, sharey=True)
    for ax, bed in zip(axes[0], beds):
        full = mean(bed.rel(r) for r in top(bed).values())
        place = [full] + [mean(bed.rel(r) for r in bed.of("mixed", share=x)) for x in translated[1:-1]] + [1.0]
        ax.axhline(1.0, color=INK, lw=0.5)
        ax.plot([0, 1, 1], [full, full, 1.0], color=BLUE, lw=1.5, zorder=3)
        ax.plot(done, place, color=ORANGE, lw=1.5, marker="o", ms=3.2, zorder=4)
        ax.plot([0, 1], [full, 1.0], "o", ms=3.2, color=BLUE, zorder=5)
        ax.set_xticks(done, ["0", "10", "50", "90", "100"])
        for tick, ha in zip(ax.get_xticklabels()[:2], ("right", "left")):  # 0 and 10 lie close together
            tick.set_ha(ha)
        ax.set_title(BEDS[bed.name])
        grid(ax)
    axes[0][len(beds) // 2].set_xlabel("share of the collection already re-embedded, %")
    axes[0][0].set_ylabel("nDCG@10 in % of full re-embed")
    axes[0][0].set_ylim(0.6, 1.03)
    percent(axes[0][0])
    below(fig, [(key(BLUE, marker="o", ms=3.2), "build the new index beside the translated one, then switch"),
                (key(ORANGE, marker="o", ms=3.2), "re-embed in place, inside the translated index")], 1)
    save(fig, "paths")


def fig_cost(beds: list[Bed]) -> None:
    """What the anchors cost: the share of the collection that the new model has to embed, against what the translation then reaches."""
    fig, axes = panels(1, 1, 2.7)
    ax = axes[0][0]
    ends: set[int] = set()
    for bed in beds:
        size = sizes(bed)
        ks = bed.ks()
        xs = [k / (size["corpus"] + size["anchors"]["in-domain"]) for k in ks]
        spread = [[bed.rel(r) for r in bed.pick(anchors="in-domain", adapter=MAIN, direction="forward", k=k) if bed.open_pair(r)] for k in ks]
        mk, col, _ = MARKS[bed.name]
        ax.fill_between(xs, [min(v) for v in spread], [max(v) for v in spread], color=col, alpha=0.13, lw=0, zorder=1)
        ax.plot(xs, [mean(v) for v in spread], color=col, lw=1.5, marker=mk, ms=4.6, mec="white", mew=0.5, zorder=3)
        if ks[-1] not in ends:  # name the largest budget once
            ax.annotate(f"$k$ = {ks[-1]:,}", (xs[-1], mean(spread[-1])), xytext=(-4, 7), textcoords="offset points", ha="right", fontsize=7, color=MUTED)
            ends.add(ks[-1])
    ax.axhline(1.0, color=INK, lw=0.5)
    ax.plot(1.0, 1.0, "o", ms=4.6, mfc=INK, mec="white", mew=0.5, zorder=4)
    ax.set_xscale("log")
    ticks = [0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
    ax.set_xticks(ticks, [f"{100 * x:g}" for x in ticks])
    ax.minorticks_off()
    ax.set_xlim(0.0005, 1.25)
    ax.set_ylim(0, 1.1)
    ax.set_xlabel("in-domain anchors embedded with the new model, in % of the collection (log scale)")
    ax.set_ylabel("nDCG@10 in % of full re-embed")
    percent(ax)
    grid(ax, "both")
    below(fig, [(key(MARKS[b.name][1], marker=MARKS[b.name][0], ms=4.6), BEDS[b.name]) for b in beds]
          + [(Patch(color=FAINT, lw=0), "lowest to highest pair"), (key(INK, "", "o"), "full re-embed")], 5)
    save(fig, "cost")


def fig_choice(beds: list[Bed]) -> None:
    """One source space and its four possible targets, ordered by anchor similarity (left) and by the measured result (right)."""
    fig, axes = panels(len(beds), len(beds[0].open), 1.2 * len(beds) + 0.75)
    for row, bed in zip(axes, beds):
        measured = top(bed)
        for ax, s in zip(row, bed.open):
            targets = [t for t in bed.open if t != s]
            alike = sorted(targets, key=lambda t: -bed.sim[("in-domain", s, t)]["knn"])
            result = sorted(targets, key=lambda t: -bed.rel(measured[(s, t)]))
            for i, t in enumerate(alike):
                j = result.index(t)
                ax.plot([0, 1], [i, j], color=BLUE if i == j else ORANGE, lw=1.4, marker="o", ms=3.4, mec="white", mew=0.5, zorder=3 if i == j else 4)
                ax.text(1.13, j, f"{100 * bed.rel(measured[(s, t)]):.1f}", fontsize=6.5, color=MUTED, va="center")
            ax.set_yticks(range(len(alike)), [ROW[t] for t in alike], fontsize=6.5)
            ax.set_ylim(len(targets) - 0.55, -0.55)
            ax.set_xlim(-0.12, 1.75)
            ax.set_xticks([0, 1], ["similarity", "result"] if bed is beds[-1] else ["", ""], fontsize=6.5)
            for tick, ha in zip(ax.get_xticklabels(), ("right", "left")):
                tick.set_ha(ha)
            ax.tick_params(length=0)
            for sp in ax.spines.values():
                sp.set_visible(False)
            if bed is beds[0]:
                ax.set_title(f"from {ROW[s]}", fontsize=8)
        row[0].set_ylabel(BEDS[bed.name])
    below(fig, [(key(BLUE, marker="o", ms=3.4), "same rank by similarity and by result"), (key(ORANGE, marker="o", ms=3.4), "rank differs")], 2)
    save(fig, "choice")


# ---------------------------------------------------------------- explanations from the vectors of Wiki-de (explain.py)


def explained() -> dict | None:
    path = RESULTS / "explain.json"
    return json.load(open(path)) if path.exists() else None


def fig_offset(ex: dict) -> None:
    """How far the vectors of a space lean one way: the length of their mean, and the cosine of two unrelated passages."""
    rows = ex["offset"]
    fig, axes = panels(1, 1, 0.23 * len(rows) + 0.95)
    ax = axes[0][0]
    for i, r in enumerate(rows):
        color = BLUE if r["space"] in MODELS else MUTED
        ax.plot([0, r["length"]], [i, i], color=FAINT, lw=1.2, zorder=2)
        ax.plot(r["mean_cos"], i, "o", ms=4.2, mfc="white", mec=color, mew=1.0, zorder=3)
        ax.plot(r["length"], i, "o", ms=4.6, mfc=color, mec="white", mew=0.6, zorder=4)
        ax.text(r["length"] + 0.018, i, f"{r['length']:.2f}", fontsize=7.5, va="center", color=INK)
    ax.axhline(sum(r["space"] in MODELS for r in rows) - 0.5, color=GRID, lw=0.6)
    ax.set_yticks(range(len(rows)), [ROW[r["space"]] for r in rows])
    ax.set_ylim(len(rows) - 0.4, -0.6)
    ax.set_xlim(0, 1.0)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel(f"over {rows[0]['n']:,} anchor vectors, each of unit length")
    grid(ax, "x")
    below(fig, [(key(BLUE, "", "o"), "length of the mean vector"), (key(BLUE, "", "o", filled=False), "mean cosine of two anchors"),
                (key(MUTED, "", "o"), "weak old model and commercial space")], 3)
    save(fig, "offset")


def fig_real_spaces(ex: dict) -> None:
    """The same held-out anchors in two real spaces, and where the orthogonal map puts them in the second."""
    sp = ex["spaces"]
    old, new, moved = (np.array(sp[part]) for part in ("in_source", "in_target", "translated"))
    reach = 1.1 * max(float(np.abs(a).max()) for a in (old, new, moved))
    marked = list(dict.fromkeys(int(i) for i in (old[:, 0].argmin(), old[:, 1].argmax(), old[:, 0].argmax(), old[:, 1].argmin())))
    fig, axes = panels(1, 2, 3.2)
    left, right = axes[0]
    left.scatter(*old.T, s=17, facecolor=MUTED, edgecolor="white", lw=0.4, zorder=3)
    for a, b in zip(new, moved):
        right.plot([a[0], b[0]], [a[1], b[1]], color=BLUE, lw=0.7, zorder=2)
    right.scatter(*moved.T, s=19, facecolor="white", edgecolor=BLUE, lw=0.9, zorder=3)
    right.scatter(*new.T, s=13, facecolor=INK, edgecolor="white", lw=0.4, zorder=4)
    for ax, points, space, share in ((left, old, sp["source"], sp["variance_source"]), (right, moved, sp["target"], sp["variance_target"])):
        for n, i in enumerate(marked, 1):  # the same passages, numbered in both panels
            away = points[i] / max(float(np.linalg.norm(points[i])), 1e-9)
            ax.annotate(str(n), points[i], xytext=tuple(9 * away), textcoords="offset points", ha="center", va="center", fontsize=7.5, color=INK,
                        bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.6}, zorder=6)
        ax.set_xlim(-reach, reach)
        ax.set_ylim(-reach, reach)
        ax.set_aspect("equal")
        ax.set_title(f"{ROW[space]} ({'source' if ax is left else 'target'} space)")
        ax.set_xlabel(f"first two principal components, {100 * share:.1f}% of the variance")
        grid(ax, "both")
    below(fig, [(key(MUTED, "", "o"), "vector of the old model"), (key(INK, "", "o"), "vector of the new model"),
                (key(BLUE, marker="o", filled=False, lw=0.7), "translated vector, joined to its counterpart")], 3)
    save(fig, "real-spaces")


def fig_damping(ex: dict) -> None:
    """Cosine between a query and its relevant passages: the new model's own vectors against translated ones."""
    pairs = ex["damping"]
    kinds = (("relevant", "every relevant passage"), ("best", "best relevant passage of a query"))
    fig, axes = panels(len(kinds), len(pairs), 4.1, sharex=True, sharey="row")
    for col, d in enumerate(pairs):
        edges = np.array(d["bins"])
        share = lambda name: np.array(d["counts"][name]) / sum(d["counts"][name])
        for ax, (kind, label) in zip(axes[:, col], kinds):
            ax.stairs(share(f"{kind}_native"), edges, fill=True, color="#dcdcdc", lw=0, zorder=2)
            ax.stairs(share(f"{kind}_native"), edges, color=INK, lw=0.8, zorder=4)
            ax.stairs(share(f"{kind}_translated"), edges, fill=True, color=BLUE, alpha=0.7, lw=0, zorder=3)
            if kind == "best":
                ax.stairs(share("rival_native"), edges, color=ORANGE, lw=1.3, zorder=5)
            else:
                ax.axvline(d["mean"]["rival_native"], color=ORANGE, lw=1.0, ls=DASH, zorder=5)
            ax.text(0.03, 0.93, label, transform=ax.transAxes, fontsize=7.5, color=MUTED, va="top")
            ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0, symbol=""))
            grid(ax)
        axes[0][col].set_title(f"{arrow(d['source'], d['target'])}, $k$ = {d['k']:,}")
        axes[-1][col].set_xlabel("cosine to the query")
    for ax in axes[:, 0]:
        ax.set_ylabel("share, %")
    axes[0][0].set_xlim(0.45, 0.95)
    below(fig, [(Patch(facecolor="#dcdcdc", edgecolor=INK, lw=0.8), "vector of the new model"), (Patch(color=BLUE, alpha=0.7, lw=0), "translated vector"),
                (key(ORANGE, lw=1.3), "best passage that is not relevant, new model (dashed: its mean)")], 3)
    save(fig, "damping")


def fig_fit_order(ex: dict) -> None:
    """Closer is not better ordered: cosine to the true vector against the neighbours that a translated vector keeps."""
    rows = ex["fit"]["pairs"]
    shown = (ex["spaces"]["source"], ex["spaces"]["target"])
    looks = {"ridge": ("D", ORANGE, 20, 3), "procrustes": ("o", BLUE, 22, 4)}
    parts = (("anchors", f"{ex['fit']['held']:,} held-out anchors, searched among each other"),
             ("queries", f"{ex['fit']['queries']} queries, searched in {ex['fit']['passages']:,} passages"))
    fig, axes = panels(1, 2, 3.0, sharex=True, sharey=True)
    for ax, (part, title) in zip(axes[0], parts):
        at = {m: {(r["source"], r["target"]): (r[f"cos_{part}"], r[f"near_{part}"]) for r in rows if r["adapter"] == m} for m in looks}
        for p in at["procrustes"]:
            ax.plot(*zip(at["procrustes"][p], at["ridge"][p]), color=INK if p == shown else FAINT, lw=0.8 if p == shown else 0.5, zorder=2 if p == shown else 1)
        for m, (marker, color, size, z) in looks.items():
            ax.scatter(*zip(*at[m].values()), s=size, marker=marker, facecolor=color, edgecolor="white", lw=0.5, zorder=z)
            ax.scatter(*at[m][shown], s=size + 6, marker=marker, facecolor=color, edgecolor=INK, lw=0.9, zorder=6)
            ax.scatter(*np.mean(list(at[m].values()), axis=0), s=3.2 * size, marker=marker, facecolor="white", edgecolor=color, lw=1.4, zorder=5)
        ax.set_title(title)
        ax.set_xlabel("cosine to the true vector")
        grid(ax, "both")
    axes[0][0].set_ylabel("ten nearest kept, %")
    axes[0][0].set_ylim(0, 0.8)
    percent(axes[0][0])
    below(fig, [(key(BLUE, "", "o"), "orthogonal map"), (key(ORANGE, "", "D"), "ridge regression"), (key(FAINT, lw=0.8), "the same pair of spaces"),
                (Line2D([], [], color=BLUE, ls="", marker="o", ms=7.5, mfc="white", mec=BLUE, mew=1.4), "mean of the 20 pairs"),
                (Line2D([], [], color=INK, lw=0.8, marker="o", ms=4.8, mfc=BLUE, mec=INK, mew=0.9), arrow(*shown))], 3)
    save(fig, "fit-order")


def fig_tie(ex: dict) -> None:
    """What a tie is: the difference to the old model query by query, and the mean of resampled query sets with its 95% interval."""
    pairs = ex["tie"]
    jitter = np.random.default_rng(SEED)
    number = lambda x: f"{x:.1f}".replace("-", "$-$")
    fig, axes = panels(2, len(pairs), 3.7, sharex="row", sharey="row", height_ratios=[1, 1.45])
    for (strip, dist), d in zip(axes.T, pairs):
        diff = 100 * np.array(d["diff"])
        lo, hi, centre = 100 * d["lo"], 100 * d["hi"], 100 * d["mean"]
        strip.scatter(diff, jitter.uniform(-0.38, 0.38, len(diff)), s=7, facecolor=BLUE, edgecolor="none", alpha=0.35, zorder=3)
        strip.axvline(0, color=INK, lw=0.7, zorder=1)
        strip.set_title(arrow(d["source"], d["target"]))
        strip.set_xlabel(f"{int((diff < 0).sum())} queries lower, {int((diff == 0).sum())} equal, {int((diff > 0).sum())} higher", fontsize=7.5, color=MUTED)
        edges = 100 * np.array(d["edges"])
        share = np.array(d["counts"]) / sum(d["counts"])
        dist.stairs(share, edges, fill=True, color=BLUE, alpha=0.3, lw=0, zorder=2)
        dist.stairs(np.where((edges[:-1] >= lo) & (edges[1:] <= hi), share, 0), edges, fill=True, color=BLUE, alpha=0.75, lw=0, zorder=3)
        dist.axvline(0, color=INK, lw=0.7, zorder=1)
        dist.plot([lo, hi], [1.16 * share.max()] * 2, color=BLUE, lw=1.3, zorder=4)
        dist.plot(centre, 1.16 * share.max(), "o", ms=4.4, mfc="white" if lo <= 0 <= hi else BLUE, mec=BLUE, mew=1.0, zorder=5)
        dist.text((lo + hi) / 2, 1.25 * share.max(), f"{number(lo)} to {number(hi)}", ha="center", va="bottom", fontsize=7.5, color=INK,
                  bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8}, zorder=6)
        for ax in (strip, dist):
            ax.set_yticks([])
            ax.spines["left"].set_visible(False)
            grid(ax, "x")
    axes[0][0].set_ylim(-0.6, 0.6)
    axes[1][0].set_ylim(0, 1.5 * max(max(d["counts"]) / sum(d["counts"]) for d in pairs))
    axes[0][0].text(0.0, 1.0, "single queries", transform=axes[0][0].transAxes, fontsize=7.5, color=MUTED, va="top")
    axes[1][0].text(0.0, 1.0, f"mean of {pairs[0]['resamples']:,}\nresampled query sets", transform=axes[1][0].transAxes, fontsize=7.5, color=MUTED,
                    va="top", linespacing=1.15)
    axes[1][len(pairs) // 2].set_xlabel("nDCG@10 of the translated index minus nDCG@10 of the old model, in points")
    below(fig, [(Patch(color=BLUE, alpha=0.75, lw=0), "middle 95% of the resampled means"),
                (key(BLUE, marker="o"), "interval below zero: below the old model"), (key(BLUE, marker="o", filled=False), "interval includes zero: a tie")], 3)
    save(fig, "tie")


def draw(beds: list[Bed]) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig_glance(beds)
    fig_testbeds(beds)
    fig_native(beds)
    fig_similarity(beds)
    fig_curves(beds)
    for b in beds:
        fig_matrix(b)
    fig_depth(beds)
    fig_stay(beds)
    fig_ceiling(beds)
    fig_overlap(beds)
    fig_fidelity(beds)
    fig_controls(beds)
    fig_upgrade(beds)
    fig_mixed(beds)
    fig_paths(beds)
    fig_closed(beds)
    fig_cost(beds)
    fig_anchor_source([b for b in beds if b.name in ALT and b.pick(anchors=ALT[b.name])])
    fig_predict(beds)
    fig_choice([b for b in beds if b.name in CHOICE])
    fig_hybrid(beds)
    ex = explained()  # written by explain.py; without it the explanatory figures are left as they are
    if ex:
        fig_offset(ex)
        fig_real_spaces(ex)
        fig_damping(ex)
        fig_fit_order(ex)
        fig_tie(ex)
