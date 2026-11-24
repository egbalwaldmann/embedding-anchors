"""How many passages does each model's token limit cut short?

    uv run python experiments/token_stats.py <testbed> [...]

Writes results/tokens.jsonl: per testbed and model the token limit used by
embed.py and, on a sample of 3,000 corpus passages, the share that exceeds it.
"""
from __future__ import annotations

import json
import sys

import numpy as np
from sentence_transformers import SentenceTransformer

from common import DATA, MODELS, PRIVATE, RESULTS, SEED, read_jsonl
from embed import MAX_TOKENS


def main(testbeds: list[str]) -> None:
    rows = []
    samples = {}
    for testbed in testbeds:
        corpus = read_jsonl((PRIVATE if testbed == "archive" else DATA) / testbed / "corpus.jsonl")
        pick = np.random.default_rng(SEED).permutation(len(corpus))[:3000]
        samples[testbed] = [corpus[i]["text"] for i in pick]
    for model, spec in MODELS.items():
        st = SentenceTransformer(spec["hf"], device="cpu")
        for testbed, texts in samples.items():
            limit = min(MAX_TOKENS.get(testbed, 512), st.max_seq_length or 512)
            lengths = np.array([len(x) for x in st.tokenizer([spec["d"] + t for t in texts], truncation=False)["input_ids"]])
            rows.append({"testbed": testbed, "model": model, "limit": int(limit), "truncated": float((lengths > limit).mean()),
                         "tokens_median": float(np.median(lengths))})
            print(rows[-1], flush=True)
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / "tokens.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
