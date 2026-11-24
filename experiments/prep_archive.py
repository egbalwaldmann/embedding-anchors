"""Build the private case-study testbed from a database export.

    EA_PRIVATE=<dir> uv run python experiments/prep_archive.py <snapshot.zip>
    EA_PRIVATE=<dir> uv run python experiments/prep_archive.py --resplit

Reads only the passage table (id, document id, text, stored vector) from the
export. Passages without a stored vector, very short passages and exact
duplicates are dropped. The collection holds many documents in several
copies, so near-duplicates are grouped by the cosine similarity of their
stored vectors (single linkage) and one passage per group is kept.
Whole documents are then held out as in-domain anchors, so that no anchor
shares a document, or a near-duplicate, with the search corpus.

`--resplit` rebuilds the split from an earlier split's files when the export
itself is no longer at hand.
"""
from __future__ import annotations

import io
import json
import sys
import zipfile

import numpy as np
import torch
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from common import PRIVATE, SEED, normalize, read_jsonl, write_jsonl

MIN_CHARS = 100
N_ANCHOR = 10_000
NEAR_DUPLICATE = 0.97


def read_export(path: str):
    rows, vecs, seen = [], [], set()
    dropped = {"zero": 0, "short": 0, "duplicate": 0}
    with zipfile.ZipFile(path) as z, z.open("chunks/documents.jsonl") as f:
        for line in io.TextIOWrapper(f, encoding="utf8"):
            c = json.loads(line)
            v = np.asarray(c["embedding"], dtype=np.float32)
            text = c["text"].strip()
            if not np.any(v):
                dropped["zero"] += 1
            elif len(text) < MIN_CHARS:
                dropped["short"] += 1
            elif text in seen:
                dropped["duplicate"] += 1
            else:
                seen.add(text)
                rows.append({"id": c["_id"], "doc": c["documentId"], "text": text})
                vecs.append(v)
    return rows, np.stack(vecs), dropped


def read_split():
    """The passages of an earlier split, before any near-duplicate was removed."""
    folder, emb = PRIVATE / "archive", PRIVATE / "emb" / "archive"
    old = json.load(open(folder / "stats.json"))
    parts = ["anchors", "corpus"] + (["near_duplicates"] if (folder / "near_duplicates.jsonl").exists() else [])
    rows = [r for p in parts for r in read_jsonl(folder / f"{p}.jsonl")]
    vecs = np.concatenate([np.load(emb / f"gemini-001.{p}.npy") for p in parts])
    return rows, vecs, {k: old["dropped"][k] for k in ("zero", "short", "duplicate")}


def near_duplicate_groups(vecs: np.ndarray) -> np.ndarray:
    """Group label per passage: passages linked by a cosine above the threshold share a label."""
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    V = torch.tensor(normalize(vecs), device=dev)
    I, J = [], []
    for i in range(0, len(V), 2048):
        a, b = torch.nonzero(V[i : i + 2048] @ V.T > NEAR_DUPLICATE, as_tuple=True)
        I.append((a + i).cpu().numpy())
        J.append(b.cpu().numpy())
    I, J = np.concatenate(I), np.concatenate(J)
    n = len(V)
    return connected_components(coo_matrix((np.ones(len(I)), (I, J)), shape=(n, n)), directed=False)[1]


def main(path: str) -> None:
    rows, vecs, dropped = read_split() if path == "--resplit" else read_export(path)
    indexed = len(rows) + sum(dropped.values())
    exact = len(rows)
    groups = near_duplicate_groups(vecs)
    first = np.unique(groups, return_index=True)[1]
    keep = np.zeros(len(rows), bool)
    keep[first] = True
    extra, extra_vecs = [r for r, k in zip(rows, keep) if not k], vecs[~keep]
    rows, vecs = [r for r, k in zip(rows, keep) if k], vecs[keep]
    dropped["near_duplicate"] = len(extra)

    rng = np.random.default_rng(SEED)
    docs = sorted({r["doc"] for r in rows})
    rng.shuffle(docs)
    by_doc: dict[str, int] = {}
    for r in rows:
        by_doc[r["doc"]] = by_doc.get(r["doc"], 0) + 1
    held, n = set(), 0
    for d in docs:
        if n >= N_ANCHOR:
            break
        if by_doc[d] <= 50:  # keep very long documents in the corpus
            held.add(d)
            n += by_doc[d]
    a = [i for i, r in enumerate(rows) if r["doc"] in held]
    c = [i for i, r in enumerate(rows) if r["doc"] not in held]
    out = PRIVATE / "archive"
    write_jsonl(out / "anchors.jsonl", [rows[i] for i in a])
    write_jsonl(out / "corpus.jsonl", [rows[i] for i in c])
    write_jsonl(out / "near_duplicates.jsonl", extra)  # kept aside so that the split can be rebuilt
    emb = PRIVATE / "emb" / "archive"
    emb.mkdir(parents=True, exist_ok=True)
    np.save(emb / "gemini-001.anchors.npy", vecs[a])
    np.save(emb / "gemini-001.corpus.npy", vecs[c])
    np.save(emb / "gemini-001.near_duplicates.npy", extra_vecs)
    norms = np.linalg.norm(vecs, axis=1)
    stats = {
        "indexed": indexed,
        "after_exact_filters": exact,
        "passages": len(rows),
        "documents": len(docs),
        "corpus": len(c),
        "anchors": len(a),
        "dropped": dropped,
        "near_duplicate_threshold": NEAR_DUPLICATE,
        "dim": int(vecs.shape[1]),
        "norm_mean": float(norms.mean()),
        "norm_min": float(norms.min()),
        "norm_max": float(norms.max()),
        "chars_median": float(np.median([len(r["text"]) for r in rows])),
    }
    json.dump(stats, open(out / "stats.json", "w"), indent=1)
    print(stats)


if __name__ == "__main__":
    main(sys.argv[1])
