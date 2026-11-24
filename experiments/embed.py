"""Embed a testbed's texts with one open model and cache the vectors.

    uv run python experiments/embed.py <testbed> <model> [part ...]

Parts are JSONL files in the testbed folder (corpus, anchors, queries, ...).
Queries get the model's query prompt, everything else the document prompt.
A part written as `<part>@query` embeds the texts of <part> in the query role.
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from common import ALL, DATA, PRIVATE, device, emb_path, read_jsonl

# Wikipedia passages are short and are read up to 512 tokens. Archive passages are long, so there
# every model reads up to its own limit, capped at 2,048 tokens.
MAX_TOKENS = {"archive": 2048}


def main(testbed: str, model: str, parts: list[str]) -> None:
    folder = (PRIVATE if testbed == "archive" else DATA) / testbed
    parts = parts or sorted(p.stem for p in folder.glob("*.jsonl"))

    def done(part: str) -> int:
        path = emb_path(testbed, model, part)
        return len(np.load(path, mmap_mode="r")) if path.exists() else 0

    # Part files only ever grow at the end, so a shorter cache is extended, not redone.
    source = lambda p: folder / f"{p.partition('@')[0]}.jsonl"
    sizes = {p: sum(1 for _ in open(source(p), encoding="utf8")) for p in parts}
    todo = [p for p in parts if done(p) < sizes[p]]
    if not todo:
        return
    spec = ALL[model]
    st = SentenceTransformer(spec["hf"], device=device(), trust_remote_code=False)
    limit = MAX_TOKENS.get(testbed, 512)
    st.max_seq_length = min(limit, st.max_seq_length or limit)
    for part in todo:
        have = done(part)
        rows = read_jsonl(source(part))[have:]
        prompt = spec["q"] if part.startswith("queries") or part.endswith("@query") else spec["d"]
        texts = [prompt + r["text"] for r in rows]
        # Longest first keeps padding low; restore the order afterwards.
        order = np.argsort([-len(t) for t in texts])
        t0 = time.time()
        # Long inputs go through in small batches and slices; releasing the MPS cache after each
        # slice keeps memory flat, which otherwise grows with every new sequence length.
        batch, step = (32, 4096) if limit <= 512 else (8, 256)
        chunks = []
        for i in range(0, len(order), step):
            chunks.append(
                st.encode(
                    [texts[j] for j in order[i : i + step]],
                    batch_size=batch,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                )
            )
            if st.device.type == "mps":
                torch.mps.empty_cache()
            if os.environ.get("EA_VERBOSE"):
                mem = torch.mps.driver_allocated_memory() / 2**30 if st.device.type == "mps" else 0
                print(f"  {part} {i + step}/{len(order)} {time.time() - t0:.0f}s {mem:.1f} GB", flush=True)
        vec = np.concatenate(chunks)
        out = np.empty_like(vec)
        out[order] = vec
        path = emb_path(testbed, model, part)
        path.parent.mkdir(parents=True, exist_ok=True)
        if have:
            out = np.concatenate([np.load(path), out])
        np.save(path, out.astype(np.float32))
        print(f"{testbed} {model} {part}: {out.shape} in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
