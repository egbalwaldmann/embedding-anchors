"""Download and subsample the two public testbeds.

T1  miracl-de : MIRACL German dev queries + qrels; corpus = all judged passages
               plus 100k random passages. Separate 20k passages as anchors.
T2  wiki-de   : German Wikipedia passages with Cohere embed-multilingual-v3
               vectors (CohereLabs/wikipedia-2023-11-embed-multilingual-v3).
               100k corpus passages, 20k in-domain anchors (other shard),
               20k English anchors (cross-lingual anchor condition).
"""
from __future__ import annotations

import gzip
import json
import random

import numpy as np
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

from common import DATA, SEED, write_jsonl

N_CORPUS = 100_000
N_ANCHOR = 20_000


def miracl() -> None:
    out = DATA / "miracl-de"
    if (out / "corpus.jsonl").exists():
        return
    topics = hf_hub_download("miracl/miracl", "miracl-v1.0-de/topics/topics.miracl-v1.0-de-dev.tsv", repo_type="dataset")
    qrels = hf_hub_download("miracl/miracl", "miracl-v1.0-de/qrels/qrels.miracl-v1.0-de-dev.tsv", repo_type="dataset")
    queries = [dict(zip(("id", "text"), line.rstrip("\n").split("\t"))) for line in open(topics, encoding="utf8")]
    rel: dict[str, dict[str, int]] = {}
    judged: set[str] = set()
    for line in open(qrels, encoding="utf8"):
        qid, _, docid, r = line.split()
        rel.setdefault(qid, {})[docid] = int(r)
        judged.add(docid)
    rng = random.Random(SEED)
    keep: dict[str, dict] = {}
    pool: list[dict] = []
    # Reservoir-sample distractors and anchors over all 32 shards.
    seen = 0
    for i in range(32):
        path = hf_hub_download("miracl/miracl-corpus", f"miracl-corpus-v1.0-de/docs-{i}.jsonl.gz", repo_type="dataset")
        with gzip.open(path, "rt", encoding="utf8") as f:
            for line in f:
                d = json.loads(line)
                if d["docid"] in judged:
                    keep[d["docid"]] = d
                    continue
                seen += 1
                if len(pool) < N_CORPUS + N_ANCHOR:
                    pool.append(d)
                else:
                    j = rng.randrange(seen)
                    if j < N_CORPUS + N_ANCHOR:
                        pool[j] = d
        print(f"shard {i}: judged found {len(keep)}/{len(judged)}", flush=True)
    rng.shuffle(pool)
    corpus = list(keep.values()) + pool[:N_CORPUS]
    anchors = pool[N_CORPUS:]
    fmt = lambda d: {"id": d["docid"], "text": (d["title"] + "\n" + d["text"]).strip()}
    write_jsonl(out / "corpus.jsonl", [fmt(d) for d in corpus])
    write_jsonl(out / "anchors.jsonl", [fmt(d) for d in anchors])
    write_jsonl(out / "queries.jsonl", queries)
    json.dump(rel, open(out / "qrels.json", "w"))
    print("miracl-de", len(corpus), len(anchors), len(queries))


def cohere_shard(lang: str, shard: int, n: int, name: str) -> None:
    out = DATA / "wiki-de"
    if (out / f"{name}.jsonl").exists():
        return
    path = hf_hub_download(
        "CohereLabs/wikipedia-2023-11-embed-multilingual-v3", f"{lang}/{shard:04d}.parquet", repo_type="dataset"
    )
    t = pq.read_table(path).slice(0, n)
    rows = [
        {"id": i, "text": (ti + "\n" + tx).strip()}
        for i, ti, tx in zip(t["_id"].to_pylist(), t["title"].to_pylist(), t["text"].to_pylist())
    ]
    write_jsonl(out / f"{name}.jsonl", rows)
    emb = np.asarray(t["emb"].to_pylist(), dtype=np.float32)
    (DATA / "emb" / "wiki-de").mkdir(parents=True, exist_ok=True)
    np.save(DATA / "emb" / "wiki-de" / f"cohere-v3.{name}.npy", emb)
    print("wiki-de", name, emb.shape)


if __name__ == "__main__":
    cohere_shard("de", 0, N_CORPUS, "corpus")
    cohere_shard("de", 100, N_ANCHOR, "anchors")
    cohere_shard("en", 0, N_ANCHOR, "anchors_en")
    miracl()
