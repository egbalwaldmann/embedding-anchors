# Publish the Anchors

[![paper](https://github.com/egbalwaldmann/embedding-anchors/actions/workflows/paper.yml/badge.svg)](https://github.com/egbalwaldmann/embedding-anchors/actions/workflows/paper.yml)

A minimal interoperability standard for text embedding spaces, and a measurement of how well a vector index can be carried from one embedding model to another without embedding the documents again.

A vector index is tied to the model that wrote it. This repository proposes that providers publish two things with every model version:

1. an **Embedding Space Card** that states what must be identical for two vectors to be comparable, and
2. the embeddings of a **public anchor corpus**.

With both published, anyone can fit a map between two spaces, including spaces whose model is no longer served, and record how well it works in an **Adapter Manifest** that must contain a measurement.

The paper is in [`paper/`](paper/): [PDF](paper/publish-the-anchors.pdf), [Markdown](paper/publish-the-anchors.md) for screen readers and language models, its main findings as [JSON](paper/claims.json) and a [graphical abstract](paper/graphical-abstract.png). The interactive companion page is in [`site/`](site/); [`llms.txt`](llms.txt) maps the repository for language models.

## Try it in five minutes

The anchor release is enough to see a translation between two embedding spaces at work. No model has to be run: the vectors of 20,000 German Wikipedia passages are there for both spaces.

```sh
pip install numpy huggingface_hub
```

```python
import numpy as np
from huggingface_hub import hf_hub_download

def anchors(space, lang="de"):
    path = hf_hub_download("egbalwaldmann/embedding-anchors", f"spaces/{space}/document.{lang}.npy", repo_type="dataset")
    return np.load(path)

X = anchors("bge-m3")                      # source space
Y = anchors("multilingual-e5-large")       # target space

# Orthogonal map from the source into the target space, fitted on 5,000 anchor pairs.
k = 5000
mx, my = X[:k].mean(0), Y[:k].mean(0)
U, _, Vt = np.linalg.svd((X[:k] - mx).T @ (Y[:k] - my), full_matrices=False)
W = U @ Vt

def translate(Z):
    out = (Z - mx) @ W + my
    return out / np.linalg.norm(out, axis=1, keepdims=True)

# 15,000 passages the map has never seen: how close are their translated vectors to the true ones?
print((translate(X[k:]) * Y[k:]).sum(1).mean())            # 0.856

# And does a translated vector find its own counterpart among 2,000 others?
T, Yh = translate(X[k:k + 2000]), Y[k:k + 2000]
print(((T @ Yh.T).argmax(1) == np.arange(2000)).mean())    # 0.994
```

A mean cosine of 0.86 looks modest and a hit rate of 99% looks perfect. Neither says how well the translated index retrieves; the paper shows why, and what does.

## Layout

| Path | Content |
| --- | --- |
| `spec/` | Specification text (`SPEC.md`) and JSON Schemas for the Embedding Space Card and the Adapter Manifest, with example cards and one example manifest |
| `experiments/` | Code for the migration study |
| `results/` | Result files; every result number, table and figure in the paper is generated from them |
| `paper/` | Typst source, generated figures, the PDF, a Markdown version, the main findings as JSON (`claims.json`) and the abstract as plain text (`abstract.txt`) |
| `site/` | Static companion page with interactive figures |

## Checked on every push

A GitHub workflow (`.github/workflows/paper.yml`) regenerates every number, table and figure from the result files on each push, fails if a number in the paper differs from what the results give, and compiles the PDF. It runs no model; the embeddings and evaluations below are the expensive part.

## Reproducing the public testbeds

Requirements: [uv](https://docs.astral.sh/uv/), Python 3.12 or newer, [Typst](https://typst.app/), about 15 GB of disk. The runs in the paper were done on an Apple M3 Max; any machine with a GPU supported by PyTorch works. Set `EA_DEVICE=cpu` to run a model on the CPU.

```sh
uv sync
uv run python experiments/prep_public.py            # Wiki-de (Cohere Wikipedia release) and MIRACL-de: corpus, anchors, queries
uv run python experiments/prep_wiki_positives.py    # Wiki-de: pages that MIRACL-de judges relevant (downloads 208 shards, one at a time)
for t in wiki-de miracl-de; do
  for m in bge-m3 me5-large arctic-l-v2 qwen3-0.6b embeddinggemma-2; do
    uv run python experiments/embed.py $t $m
  done
done
uv run python experiments/similarity.py wiki-de
uv run python experiments/similarity.py wiki-de anchors_en
uv run python experiments/similarity.py miracl-de
uv run python experiments/evaluate.py wiki-de       # writes results/wiki-de.jsonl
uv run python experiments/evaluate.py miracl-de     # writes results/miracl-de.jsonl
uv run python experiments/token_stats.py wiki-de miracl-de   # share of passages cut by the token limit
for t in wiki-de miracl-de; do
  uv run python experiments/embed.py $t minilm-l12 corpus anchors queries   # a much weaker old model as a source
  for m in me5-large arctic-l-v2 qwen3-0.6b embeddinggemma-2; do
    uv run python experiments/embed.py $t $m anchors@query                   # the anchors in the query role
  done
  uv run python experiments/evaluate_extra.py $t    # writes results/$t.extra.jsonl
done
uv run python experiments/explain.py                # numbers behind the explanatory figures, from the public Wiki-de vectors
uv run python experiments/report.py                 # writes paper/fig/*.svg and paper/generated.typ
uv run python experiments/site_data.py              # data for the companion page in site/
typst compile --root . --pdf-standard ua-1 --pdf-standard a-2a paper/main.typ paper/publish-the-anchors.pdf   # accessible (PDF/UA-1) and archival (PDF/A-2a)
uv run python experiments/text_version.py          # paper/publish-the-anchors.md and paper/claims.json (needs pandoc)
```

`site/` is a static companion page that lets readers explore these results; open it with any static server, for example `python -m http.server -d site`.

## The anchor release

`experiments/release_anchors.py` assembles the public anchor corpus (20,000 German and 20,000 English Wikipedia passages), the document-role vectors of the five open models, one Embedding Space Card per space and one worked adapter with its Adapter Manifest into `data/release/`, validates cards and manifest against the schemas and, with `--upload <repo>`, uploads the folder to a dataset repository on the Hugging Face Hub. It also writes `croissant.json`, a description of the release in [Croissant 1.0](https://mlcommons.org/croissant/), the metadata format that dataset hubs and ML tools read (a copy is in `spec/croissant.json`). It reads the public Wiki-de testbed only.

## The archive testbed

The third testbed is a private document archive. Its texts and vectors are not part of this repository and will not be released; `results/archive.jsonl` contains aggregate retrieval metrics only. `experiments/prep_archive.py` and `experiments/gen_queries.py` show how the testbed was built, so the procedure can be repeated on another private collection: set `EA_PRIVATE` to a directory outside the repository and run the same steps with the testbed name `archive`.

## Kurzfassung auf Deutsch

Eine Suche über Bedeutungen speichert zu jedem Textstück einen Vektor. Diese Vektoren schreibt ein Embedding-Modell, und nur mit diesem Modell lassen sie sich vergleichen. Wer das Modell wechselt, muss bisher alle Texte neu einbetten.

Der Artikel schlägt vor, dass Anbieter zu jeder Modellversion zwei Dinge veröffentlichen: eine maschinenlesbare Karte, die den Vektorraum beschreibt, und die Vektoren eines festen öffentlichen Ankerkorpus. Mit den Ankern zweier Modelle kann jeder eine Abbildung zwischen den beiden Räumen anpassen und nachmessen, wie gut sie trägt.

Gemessen an zwei deutschen Wikipedia-Testbetten und einer privaten deutschen Dokumentensammlung, zwischen fünf offenen Modellen und aus zwei kommerziellen Räumen: Ein übersetzter Index behält im Mittel 95,7 %, 95,1 % und 88,0 % der Suchqualität eines neu eingebetteten. Er ist fast immer schlechter als das alte Modell und nie besser. Übersetzen hält einen Index durchsuchbar, wenn sein Modell nicht mehr verfügbar ist; es ersetzt das Neu-Einbetten nicht.

## Licence

| Part | Licence |
| --- | --- |
| Code (`experiments/`) | MIT, see `LICENSE` |
| Paper (`paper/`) and specification (`spec/`) | CC BY 4.0 |
| Anchor corpus and its vectors (released separately) | CC BY-SA 4.0, because the texts come from Wikipedia |

## Citation

```bibtex
@misc{waldmann2026anchors,
  author = {Waldmann, Egbal},
  title  = {Publish the Anchors: A Minimal Interoperability Standard for Text Embedding Spaces, with a Cross-Vendor German Migration Study},
  year   = {2026},
  doi    = {10.5281/zenodo.24484736}
}
```

The repository is archived at Software Heritage as `swh:1:snp:13a23ea46d6aca44c347e43fa3d3eed5ec5e171f` ([browse](https://archive.softwareheritage.org/swh:1:snp:13a23ea46d6aca44c347e43fa3d3eed5ec5e171f)).
