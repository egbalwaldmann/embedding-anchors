"""The paper as plain text for readers and tools that do not read PDF: Markdown and a list of its claims.

    uv run python experiments/text_version.py

Writes paper/publish-the-anchors.md (from Typst's HTML export, converted with pandoc) and
paper/claims.json (the main findings with their numbers, taken from paper/generated.typ).
Needs typst and pandoc on the path. Runs in seconds.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

from common import ROOT

PAPER = ROOT / "paper"
TITLE = "Publish the Anchors: A Minimal Interoperability Standard for Text Embedding Spaces, with a Cross-Vendor German Migration Study"
AUTHOR = "Egbal Waldmann"
ORCID = "https://orcid.org/0000-0003-2958-5121"
DOI = "10.5281/zenodo.24484736"
CODE = "https://github.com/egbalwaldmann/embedding-anchors"
ANCHORS = "https://huggingface.co/datasets/egbalwaldmann/embedding-anchors"
KEYWORDS = ["text embeddings", "vector search", "model migration", "interoperability", "retrieval",
            "AI engineering", "artificial intelligence"]


def numbers() -> dict[str, str]:
    text = (PAPER / "generated.typ").read_text(encoding="utf8")
    return dict(re.findall(r'^\s*"([^"]+)": "([^"]*)",?$', text, flags=re.M))


def markdown() -> str:
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "paper.html"
        subprocess.run(["typst", "compile", "--root", str(ROOT), "--features", "html", "--format", "html",
                        str(PAPER / "main.typ"), str(html)], check=True, capture_output=True)
        body = subprocess.run(["pandoc", "-f", "html", "-t", "gfm", "--wrap=none", str(html)],
                              check=True, capture_output=True, text=True).stdout
    body = re.sub(r"<div>\s*(Contents|List of Figures|List of Tables|List of Listings)\s*</div>\s*", "", body)
    body = re.sub(r'<span id="[^"]*"></span>\s*', "", body)
    body = re.sub(r"<div>\s*</div>\s*", "", body)
    while True:  # spans may be nested
        plain = re.sub(r"<span[^>]*>((?:(?!<span).)*?)</span>", r"\1", body, flags=re.S)
        if plain == body:
            break
        body = plain
    body = re.sub(r'<div id="app-[^"]*">\s*(Appendix [^\n]+?)\s*</div>', r"## \1", body)  # appendix headings
    body = re.sub(r'<div class="section" role="doc-bibliography">\s*', "", body)
    body = re.sub(r"\s*</div>\s*$", "", body)
    body = re.sub(r'<a href="#loc-\d+"[^>]*>(.*?)</a>', r"\1", body)  # citations stay as [n]
    body = re.sub(r"\[([^\]]+)\]\(#gl-[^)]+\)", r"\1", body)  # links into the glossary become plain words
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    abstract = (PAPER / "abstract.txt").read_text(encoding="utf8").strip()
    head = "\n".join([
        f"# {TITLE}",
        "",
        f"{AUTHOR} ([ORCID]({ORCID}), [LinkedIn](https://www.linkedin.com/in/egbalwaldmann)), AI Engineer, Potsdam, Germany. Preprint, November 2026.",
        "",
        f"DOI: [{DOI}](https://doi.org/{DOI}) · Code and specification: {CODE} · Anchor corpus: {ANCHORS} · Interactive figures: https://anchors.egbalwaldmann.com",
        "",
        "This is a text version of the PDF, made for screen readers, search and language models. "
        "Figures are given by their captions and descriptions; numbers and wording are those of the PDF.",
        "",
        "## Abstract",
        "",
        abstract,
        "",
        f"Keywords: {', '.join(KEYWORDS)}",
        "",
    ])
    return head + "\n" + body + "\n"


def claims(n: dict[str, str]) -> dict:
    def pct(*keys: str) -> list[float]:
        return [float(n[k]) for k in keys]

    beds = ["Wiki-de", "MIRACL-de", "Archive"]
    found = [
        ("translation-keeps", "With an orthogonal map fitted on all in-domain anchor pairs, a translated index keeps this share of the nDCG@10 of a full re-embed.",
         dict(zip(beds, pct("wiki.top.procrustes.fwd.mean", "miracl.top.procrustes.fwd.mean", "archive.top.procrustes.fwd.mean"))), "percent of full re-embed", "sec-open"),
        ("query-translation-keeps", "Translating queries into the old space instead keeps this share.",
         dict(zip(beds, pct("wiki.top.procrustes.bwd.mean", "miracl.top.procrustes.bwd.mean", "archive.top.procrustes.bwd.mean"))), "percent of full re-embed", "sec-open"),
        ("never-beats-old-model", f"Of {n['all.beats-stay.of']} measured combinations, none is better than keeping the old model beyond the noise of the query sample.",
         {"combinations": int(n["all.beats-stay.of"].replace(",", "")), "better_beyond_noise": 0}, "count", "sec-open"),
        ("old-model-is-ceiling", "A translated index inherits the limits of the model that wrote it: from a much weaker old model it stays below that model.",
         {"combinations": int(n["all.x.upgrade.of"].replace(",", "")), "worse_beyond_noise": int(n["all.x.upgrade.below"].replace(",", ""))}, "count", "sec-upgrade"),
        ("thousand-anchors", "With 1,000 anchor pairs the orthogonal map keeps this share of a full re-embed.",
         dict(zip(beds, pct("wiki.in-domain.procrustes.fwd.1000.mean", "miracl.in-domain.procrustes.fwd.1000.mean", "archive.in-domain.procrustes.fwd.1000.mean"))), "percent of full re-embed", "sec-open"),
        ("mixed-index-worse", "An index with nine tenths of its vectors translated and the rest re-embedded is worse than a fully translated one.",
         dict(zip(beds, pct("wiki.x.mixed.90.mean", "miracl.x.mixed.90.mean", "archive.x.mixed.90.mean"))), "percent of full re-embed", "sec-mixed"),
        ("public-anchors-cost", "Wikipedia anchors in place of anchors from the archive itself cost this many percentage points of a full re-embed on the Archive, pair by pair.",
         {"Archive": float(n["archive.alt.loss.mean"])}, "percentage points", "sec-anchors"),
        ("query-role-not-needed", "Anchors embedded in the query role change orthogonal query translation by this many points of nDCG@10 (hundredths), within or near the noise.",
         dict(zip(beds, pct("wiki.x.c.query-role-vs-document-role.procrustes.diff", "miracl.x.c.query-role-vs-document-role.procrustes.diff", "archive.x.c.query-role-vs-document-role.procrustes.diff"))), "points of nDCG@10", "sec-open"),
        ("similarity-does-not-forecast", "The rank correlation between neighbour overlap of two anchor matrices and the outcome of translation is positive within a testbed, but no measure gives the size of the loss.",
         dict(zip(beds, pct("wiki.predict.knn.fwd", "miracl.predict.knn.fwd", "archive.predict.knn.fwd"))), "Spearman rank correlation", "sec-predict"),
        ("hybrid-helps", "On the Archive, a translated index fused with BM25 is above BM25 alone.",
         {"bm25": float(n["archive.bm25.ndcg"]), "translated_alone": float(n["archive.x.hy.in-domain.10000.bridge"]), "fused": float(n["archive.x.hy.in-domain.10000.fused"])}, "nDCG@10", "sec-hybrid"),
    ]
    return {
        "title": TITLE, "author": AUTHOR, "orcid": ORCID, "doi": DOI, "code": CODE, "anchors": ANCHORS,
        "measure": "nDCG@10; 'percent of full re-embed' is nDCG@10 relative to embedding documents and queries with the new model",
        "testbeds": {"Wiki-de": "German Wikipedia, 305 human queries", "MIRACL-de": "German MIRACL with passage judgements, 305 queries",
                     "Archive": "a private archive of German documents, 300 generated questions; only aggregates are released"},
        "claims": [{"id": i, "statement": s, "values": v, "unit": u, "section": sec} for i, s, v, u, sec in found],
        "proposal": {"Embedding Space Card": "what must be identical for two vectors to be comparable",
                     "anchor corpus": "public passages whose embeddings every provider publishes for every model version",
                     "Adapter Manifest": "ties a map between two spaces to a measured retrieval result"},
    }


if __name__ == "__main__":
    (PAPER / "publish-the-anchors.md").write_text(markdown(), encoding="utf8")
    (PAPER / "claims.json").write_text(json.dumps(claims(numbers()), indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("wrote paper/publish-the-anchors.md and paper/claims.json")
