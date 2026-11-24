"""Add the Wikipedia pages that MIRACL-de judges relevant to the wiki-de testbed.

MIRACL passage ids are "<pageid>#<n>", the Cohere dump uses
"20231101.de_<pageid>_<n>". Page ids are stable across dumps, so relevance
transfers at page level: a query's relevant pages are the pages of its
positive MIRACL passages. All Cohere passages of those pages are pulled from
the 208 German shards (each shard is downloaded, filtered and deleted).
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

from common import DATA, read_jsonl, write_jsonl

REPO = "CohereLabs/wikipedia-2023-11-embed-multilingual-v3"
OUT = DATA / "wiki-de"
TMP = DATA / "tmp-shards"


def page_of(cohere_id: str) -> str:
    return cohere_id.split("_")[1]


def scan(shard: int, pages: set[str]):
    part = TMP / f"pos-{shard:04d}.npz"
    if part.exists():
        return shard
    path = hf_hub_download(REPO, f"de/{shard:04d}.parquet", repo_type="dataset", local_dir=TMP)
    ids = pq.read_table(path, columns=["_id"])["_id"].to_pylist()
    hit = [i for i, x in enumerate(ids) if page_of(x) in pages]
    if hit:
        t = pq.read_table(path).take(hit)
        texts = [(ti + "\n" + tx).strip() for ti, tx in zip(t["title"].to_pylist(), t["text"].to_pylist())]
        np.savez(
            part,
            ids=np.array(t["_id"].to_pylist()),
            texts=np.array(texts, dtype=object),
            emb=np.asarray(t["emb"].to_pylist(), dtype=np.float32),
        )
    else:
        np.savez(part, ids=np.array([]), texts=np.array([], dtype=object), emb=np.zeros((0, 1024), np.float32))
    os.remove(path)
    return shard


def main() -> None:
    qrels = json.load(open(DATA / "miracl-de" / "qrels.json"))
    pages = {doc.split("#")[0] for rel in qrels.values() for doc, r in rel.items() if r > 0}
    print("relevant pages", len(pages), flush=True)
    TMP.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        for s in ex.map(lambda s: scan(s, pages), range(208)):
            if s % 10 == 0:
                print("shard", s, flush=True)

    base = read_jsonl(OUT / "corpus.jsonl")
    base_emb = np.load(DATA / "emb" / "wiki-de" / "cohere-v3.corpus.npy")
    seen = {r["id"] for r in base}
    rows, embs = list(base), [base_emb]
    for s in range(208):
        z = np.load(TMP / f"pos-{s:04d}.npz", allow_pickle=True)
        keep = [i for i, x in enumerate(z["ids"]) if x not in seen]
        rows += [{"id": str(z["ids"][i]), "text": str(z["texts"][i])} for i in keep]
        embs.append(z["emb"][keep])
        seen.update(str(z["ids"][i]) for i in keep)
    write_jsonl(OUT / "corpus.jsonl", rows)
    np.save(DATA / "emb" / "wiki-de" / "cohere-v3.corpus.npy", np.concatenate(embs))
    # Page-level qrels and the query file for this testbed.
    have = {page_of(r["id"]) for r in rows}
    page_qrels = {
        q: sorted({d.split("#")[0] for d, r in rel.items() if r > 0} & have) for q, rel in qrels.items()
    }
    page_qrels = {q: p for q, p in page_qrels.items() if p}
    json.dump(page_qrels, open(OUT / "qrels_pages.json", "w"))
    queries = [q for q in read_jsonl(DATA / "miracl-de" / "queries.jsonl") if q["id"] in page_qrels]
    write_jsonl(OUT / "queries.jsonl", queries)
    print("corpus", len(rows), "queries with a relevant page", len(queries), flush=True)


if __name__ == "__main__":
    main()
