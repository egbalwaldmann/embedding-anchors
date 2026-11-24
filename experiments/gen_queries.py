"""Write known-item questions for sampled passages with a local language model.

    EA_PRIVATE=<dir> uv run python experiments/gen_queries.py archive [n]

One passage per document is sampled; a local model (Ollama) writes one German
question that the passage answers. The passage is the query's only relevant
item. Nothing leaves the machine.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request

import numpy as np

from common import DATA, PRIVATE, SEED, read_jsonl, write_jsonl

MODEL = "gemma4:12b"
PROMPT = """Du bekommst einen Abschnitt aus einem deutschen Dokument. Schreibe genau eine Frage auf Deutsch, die ein Mensch in eine Suche eintippen würde, um genau diesen Abschnitt zu finden.

Regeln:
- Die Frage muss sich aus dem Abschnitt beantworten lassen.
- Formuliere in eigenen Worten und übernimm keine längeren Wortfolgen aus dem Abschnitt.
- Nenne die konkrete Sache, um die es geht, damit die Frage ohne den Abschnitt verständlich ist.
- Höchstens 25 Wörter. Gib nur die Frage aus, sonst nichts.

Abschnitt:
\"\"\"
{text}
\"\"\"
"""


def prompt(folder) -> str:
    """A collection may bring its own wording in <folder>/query_prompt.txt; the archive of the paper does."""
    own = folder / "query_prompt.txt"
    return own.read_text(encoding="utf8") if own.exists() else PROMPT


def ask(text: str, template: str = PROMPT) -> str:
    body = json.dumps(
        {"model": MODEL, "prompt": template.format(text=text), "stream": False, "think": False,
         "options": {"temperature": 0.3, "seed": SEED, "num_predict": 120}}
    ).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", body, {"Content-Type": "application/json"})
    out = json.load(urllib.request.urlopen(req, timeout=300))["response"].strip()
    out = out.splitlines()[0].strip().strip('"„“')
    return out


def main(testbed: str, n: int) -> None:
    folder = (PRIVATE if testbed == "archive" else DATA) / testbed
    corpus = read_jsonl(folder / "corpus.jsonl")
    rng = np.random.default_rng(SEED)
    seen_docs, picks = set(), []
    for i in rng.permutation(len(corpus)):
        r = corpus[i]
        doc = r.get("doc", r["id"])
        letters = len(re.findall(r"[A-Za-zÄÖÜäöüß]", r["text"]))
        if doc in seen_docs or len(r["text"]) < 400 or letters < 0.6 * len(r["text"]):
            continue
        seen_docs.add(doc)
        picks.append(r)
        if len(picks) >= int(n * 1.15):
            break
    queries, qrels = [], {}
    template = prompt(folder)
    for r in picks:
        q = ask(r["text"], template)
        if not q.endswith("?") or not (4 <= len(q.split()) <= 30):
            continue
        qid = f"q{len(queries):04d}"
        queries.append({"id": qid, "text": q})
        qrels[qid] = {r["id"]: 1}
        if len(queries) % 25 == 0:
            print(len(queries), flush=True)
        if len(queries) >= n:
            break
    write_jsonl(folder / "queries.jsonl", queries)
    json.dump(qrels, open(folder / "qrels.json", "w"))
    print("queries", len(queries))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 300)
