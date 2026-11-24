---
license: cc-by-sa-4.0
language:
- de
- en
pretty_name: Embedding Anchors v0.1
tags:
- embeddings
- text-embeddings
- interoperability
- model-migration
- retrieval
size_categories:
- 10K<n<100K
configs:
- config_name: corpus
  data_files:
  - split: de
    path: corpus/anchors-v0.1.de.jsonl
  - split: en
    path: corpus/anchors-v0.1.en.jsonl
---

# Embedding Anchors v0.1

A fixed list of public texts, and the vectors that several embedding models assign to them.

A vector index is tied to the model that wrote it: vectors from two models cannot be compared, so changing the model normally means embedding every document again. If two models have embedded the *same* texts, those vectors are paired data, and a map between the two spaces can be fitted and measured. This dataset provides such pairs for a first set of open models, in the layout proposed by the *Embedding Space Card* specification (`spec/SPEC.md`).

The proposal behind it is simple: every provider of an embedding model publishes, for every model version, a card that describes the space and the embeddings of a common anchor corpus. This dataset is a third-party start on that. None of the vectors here were published by the providers of the models.

## Contents

| Path | Content |
| --- | --- |
| `corpus/anchors-v0.1.de.jsonl` | {n_de} German Wikipedia passages (`id`, `text`) |
| `corpus/anchors-v0.1.en.jsonl` | {n_en} English Wikipedia passages (`id`, `text`) |
| `corpus/SHA256SUMS` | checksums of the two corpus files |
| `spaces/<space>/card.json` | Embedding Space Card of the space |
| `spaces/<space>/document.de.npy` | vectors of the German anchors, document role, float32, row *i* = line *i* of the corpus |
| `spaces/<space>/document.en.npy` | vectors of the English anchors, document role |
| `adapters/{adapter}.npz` | one worked adapter: an orthogonal map from `bge-m3` into `multilingual-e5-large` (`W`, `mean_source`, `mean_target`) |
| `adapters/{adapter}.manifest.json` | its Adapter Manifest, with the measured retrieval results |
| `spec/` | specification text and JSON Schemas for the card and the adapter manifest |

## Spaces

| Space | Dimensions | Document prefix |
| --- | --- | --- |
{space_rows}

Every text was embedded as `prefix + text`, read up to 512 tokens, and the vectors are unit length.

## Use

```python
import numpy as np
from huggingface_hub import hf_hub_download

def anchors(space, lang="de"):
    path = hf_hub_download("{repo}", f"spaces/{{space}}/document.{{lang}}.npy", repo_type="dataset")
    return np.load(path)

X = anchors("bge-m3")                      # source space
Y = anchors("multilingual-e5-large")       # target space

# Orthogonal map from the source into the target space, fitted on 5,000 pairs.
k = 5000
mx, my = X[:k].mean(0), Y[:k].mean(0)
U, _, Vt = np.linalg.svd((X[:k] - mx).T @ (Y[:k] - my), full_matrices=False)
W = U @ Vt

def translate(Z):
    out = (Z - mx) @ W + my
    return out / np.linalg.norm(out, axis=1, keepdims=True)

# Held-out check: how close are translated source vectors to the true target vectors?
print((translate(X[k:]) * Y[k:]).sum(1).mean())
```

A high cosine on held-out anchors does not show that retrieval works. In our measurements a least-squares map reproduced held-out vectors better than the orthogonal map and still retrieved worse. Measure retrieval on your own queries before relying on a map.

## The worked adapter

`adapters/` holds one map as an example of the third part of the specification. It was fitted on all {n_de} German anchors and takes `bge-m3` vectors into the space of `multilingual-e5-large`:

```python
a = np.load(hf_hub_download("{repo}", "adapters/{adapter}.npz", repo_type="dataset"))
out = (Z - a["mean_source"]) @ a["W"] + a["mean_target"]
out /= np.linalg.norm(out, axis=1, keepdims=True)
```

Its manifest records what the map delivers on a German Wikipedia retrieval testbed, next to the result of the two models on their own: once for an index of `bge-m3` vectors that is translated and searched with `multilingual-e5-large` queries, and once for `bge-m3` queries that are translated and searched against a `multilingual-e5-large` index. Both stay a little below either model on its own. The map is an illustration of the format, not a recommendation to use it.

## How the corpus was built

The passages come from the Wikipedia dump of November 2023 as chunked in `CohereLabs/wikipedia-2023-11-embed-multilingual-v3`: the first {n_de} passages of German shard 100 and the first {n_en} passages of English shard 0. Title and text are joined by a line break. The identifiers are those of that release, so the Cohere `embed-multilingual-v3.0` vectors of the same passages can be read from it row by row.

## Limits of this version

- Document role only, which is the role the specification requires.
- The German passages are consecutive passages of {pages_de} articles, not a random sample of Wikipedia.
- Wikipedia is a general-purpose corpus. For a specialised collection, pairs made from the collection itself can be expected to give better maps than these anchors.
- Two languages, five open models.

## Licence

The texts are from Wikipedia and are available under CC BY-SA 4.0. The vectors and cards in this dataset are released under the same licence.
