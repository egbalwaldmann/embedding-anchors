"""Assemble the public anchor release and, on request, upload it to the Hugging Face Hub.

    uv run python experiments/release_anchors.py                    # build data/release/anchors-v0.1
    uv run python experiments/release_anchors.py --upload <repo>    # also upload (private dataset repo)
    uv run python experiments/release_anchors.py --kaggle <repo>    # also write a folder for the Kaggle CLI
    uv run python experiments/release_anchors.py --croissant        # only write croissant.json for the built release

The release holds the two anchor corpora, the document-role vectors of the open
models, one Embedding Space Card per space, one worked adapter with its manifest,
and the specification. It is built from the public Wiki-de testbed only; nothing
from a private collection is read.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator

from common import DATA, MODELS, RESULTS, ROOT

VERSION = "v0.1"
OUT = DATA / "release" / f"anchors-{VERSION}"
SOURCE = DATA / "wiki-de"  # public testbed: Wikipedia passages only
PARTS = {"de": "anchors", "en": "anchors_en"}
MAX_TOKENS = 512
ADAPTER = ("bge-m3", "me5-large")  # the worked example: one orthogonal map, fitted on all German anchors

# Pinned revisions of the weights the vectors were computed with, and the models' licences.
SPACES = {
    "bge-m3": ("baai", "BAAI", "5617a9f61b028005a4858fdac845db406aefb181", "MIT", ":dense"),
    "me5-large": ("intfloat", "intfloat", "3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3", "MIT", ""),
    "arctic-l-v2": ("snowflake", "Snowflake", "ac6544c8a46e00af67e330e85a9028c66b8cfd9a", "Apache-2.0", ""),
    "qwen3-0.6b": ("qwen", "Qwen", "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3", "Apache-2.0", ""),
    "embeddinggemma-2": ("google", "Google", "f9972ac22e696a105c482202646979e33e4b5a1e", "Apache-2.0", ""),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def place(src: Path, dst: Path) -> None:
    """Hard link where possible, so the release costs no extra disk."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def save_npz(path: Path, **arrays: np.ndarray) -> None:
    """Like np.savez, but with fixed time stamps, so the same arrays give the same checksum."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        for name, array in arrays.items():
            buf = io.BytesIO()
            np.lib.format.write_array(buf, np.ascontiguousarray(array, dtype=np.float32), allow_pickle=False)
            z.writestr(zipfile.ZipInfo(name + ".npy", date_time=(1980, 1, 1, 0, 0, 0)), buf.getvalue())


def adapter(base: str, cards: dict[str, dict], corpus: dict) -> str:
    """Fit the worked example and write its weights and manifest; the measurements come from results/wiki-de.jsonl."""
    s, t = ADAPTER
    X, Y = (np.load(DATA / "emb" / "wiki-de" / f"{m}.anchors.npy") for m in (s, t))
    mx, my = X.mean(0), Y.mean(0)
    U, _, Vt = np.linalg.svd((X - mx).T @ (Y - my), full_matrices=False)
    name = f"{cards[s]['model']['name']}--{cards[t]['model']['name']}.orthogonal"
    folder = OUT / "adapters"
    folder.mkdir(exist_ok=True)
    save_npz(folder / f"{name}.npz", W=U @ Vt, mean_source=mx, mean_target=my)

    rows = [json.loads(line) for line in open(RESULTS / "wiki-de.jsonl")]
    native = {r["space"]: round(r["ndcg10"], 4) for r in rows if r["kind"] == "native"}

    def bridged(direction: str, old: str, new: str) -> float:
        return round(next(r["ndcg10"] for r in rows if r["kind"] == "bridge" and r["adapter"] == "procrustes"
                          and r["anchors"] == "in-domain" and r["k"] == len(X) and r["direction"] == direction
                          and r["source"] == old and r["target"] == new), 4)

    def evaluation(mode: str, value: float) -> dict:
        return {"benchmark": "Wiki-de (Publish the Anchors, 2026)", "language": "de", "mode": mode, "metric": "nDCG@10",
                "bridged": value, "native_target": native[t], "native_source": native[s]}

    manifest = {
        "spec_version": "0.1",
        "source_space": cards[s]["space_id"],
        "target_space": cards[t]["space_id"],
        "map": {"type": "orthogonal", "weights_url": f"{base}/adapters/{name}.npz",
                "weights_sha256": sha256(folder / f"{name}.npz"), "format": "npz", "centred": True, "output_normalized": True},
        "fit": {"corpus_id": f"anchors-{VERSION}-de", "corpus_sha256": corpus["de"]["sha"], "pairs": len(X),
                "source_role": "document", "target_role": "document", "languages": ["de"]},
        "evaluation": [
            # stored vectors of the source model, searched with queries of the target model
            evaluation("index-translation", bridged("forward", s, t)),
            # queries of the source model, searched against an index of the target model
            evaluation("query-translation", bridged("backward", t, s)),
        ],
        "license": "CC-BY-SA-4.0",
        "created": "2026-11-23",
        "author": "Egbal Waldmann",
    }
    errors = list(Draft202012Validator(json.load(open(ROOT / "spec" / "adapter-manifest.schema.json"))).iter_errors(manifest))
    assert not errors, [e.message for e in errors]
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    (folder / f"{name}.manifest.json").write_text(text, encoding="utf8")
    (ROOT / "spec" / "examples" / f"adapter-manifest.{name}.json").write_text(text, encoding="utf8")
    return name


def build(repo: str) -> None:
    schema = json.load(open(ROOT / "spec" / "embedding-space-card.schema.json"))
    validator = Draft202012Validator(schema)
    base = f"https://huggingface.co/datasets/{repo}/resolve/main"

    corpus, sums = {}, []
    for lang, part in PARTS.items():
        dst = OUT / "corpus" / f"anchors-{VERSION}.{lang}.jsonl"
        place(SOURCE / f"{part}.jsonl", dst)
        rows = [json.loads(line) for line in open(dst, encoding="utf8")]
        assert all(set(r) == {"id", "text"} for r in rows) and len({r["id"] for r in rows}) == len(rows)
        corpus[lang] = {"n": len(rows), "sha": sha256(dst), "rows": rows}
        sums.append(f"{corpus[lang]['sha']}  {dst.name}")
    (OUT / "corpus" / "SHA256SUMS").write_text("\n".join(sums) + "\n")

    table, cards = [], {}
    for model, (publisher_id, publisher, revision, licence, variant) in SPACES.items():
        hf = MODELS[model]["hf"]
        name = hf.split("/")[1]
        folder = OUT / "spaces" / name
        entries, dim = [], None
        for lang, part in PARTS.items():
            src = DATA / "emb" / "wiki-de" / f"{model}.{part}.npy"
            vec = np.load(src, mmap_mode="r")
            assert vec.shape[0] == corpus[lang]["n"] and vec.dtype == np.float32, (model, lang, vec.shape, vec.dtype)
            assert abs(float(np.linalg.norm(vec[:1000], axis=1).mean()) - 1.0) < 1e-3, (model, lang)
            dim = vec.shape[1]
            dst = folder / f"document.{lang}.npy"
            place(src, dst)
            entries.append({
                "corpus_id": f"anchors-{VERSION}-{lang}",
                "corpus_sha256": corpus[lang]["sha"],
                "role": "document",
                "url": f"{base}/spaces/{name}/document.{lang}.npy",
                "format": "npy",
                "vectors_sha256": sha256(dst),
            })
        role = lambda prefix: {"prefix": prefix} if prefix else {}
        card = {
            "spec_version": "0.1",
            "space_id": f"{publisher_id}/{name}@{revision[:8]}{variant}",
            "model": {"publisher": publisher, "name": name, "revision": revision, "license": licence,
                      "url": f"https://huggingface.co/{hf}"},
            "dimensions": dim,
            "native_dimensions": dim,
            "truncation": {"method": "none"},
            "similarity": "cosine",
            "normalized": True,
            "input": {"roles": {"document": role(MODELS[model]["d"]), "query": role(MODELS[model]["q"])},
                      "max_tokens": MAX_TOKENS, "overflow": "truncate"},
            "anchors": entries,
        }
        errors = list(validator.iter_errors(card))
        assert not errors, (model, [e.message for e in errors])
        (folder / "card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
        cards[model] = card
        prefix = "`" + MODELS[model]["d"].replace("|", "\\|") + "`" if MODELS[model]["d"] else "none"
        table.append(f"| `{name}` (`{card['space_id']}`) | {dim} | {prefix} |")

    example = adapter(base, cards, corpus)

    (OUT / "spec").mkdir(exist_ok=True)
    for f in ("SPEC.md", "embedding-space-card.schema.json", "adapter-manifest.schema.json"):
        shutil.copy2(ROOT / "spec" / f, OUT / "spec" / f)

    pages = len({r["id"].split("_")[1] for r in corpus["de"]["rows"]})
    text = (ROOT / "spec" / "dataset-card.md").read_text(encoding="utf8")
    for key, value in {"{n_de}": f"{corpus['de']['n']:,}", "{n_en}": f"{corpus['en']['n']:,}", "{pages_de}": f"{pages:,}",
                       "{space_rows}": "\n".join(table), "{repo}": repo, "{adapter}": example, "{{": "{", "}}": "}"}.items():
        text = text.replace(key, value)
    (OUT / "README.md").write_text(text, encoding="utf8")

    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    total = sum(p.stat().st_size for p in files)
    for p in files:
        print(f"{p.stat().st_size / 2**20:8.1f} MB  {p.relative_to(OUT)}")
    print(f"{len(files)} files, {total / 2**20:.0f} MB in {OUT}")


def upload(repo: str) -> None:
    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
    api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=str(OUT),
                      commit_message=f"Anchors {VERSION}: corpus, document-role vectors of five open models, cards, one adapter with manifest, specification")
    info = api.dataset_info(repo)
    print("uploaded:", f"https://huggingface.co/datasets/{repo}", "| private:", info.private, "| files:", len(info.siblings))


# The JSON-LD context of Croissant 1.0, the MLCommons metadata format that dataset hubs and ML tools read.
CROISSANT_CONTEXT = {
    "@language": "en", "@vocab": "https://schema.org/", "citeAs": "cr:citeAs", "column": "cr:column",
    "conformsTo": "dct:conformsTo", "cr": "http://mlcommons.org/croissant/", "rai": "http://mlcommons.org/croissant/RAI/",
    "data": {"@id": "cr:data", "@type": "@json"}, "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    "dct": "http://purl.org/dc/terms/", "examples": {"@id": "cr:examples", "@type": "@json"}, "extract": "cr:extract",
    "field": "cr:field", "fileProperty": "cr:fileProperty", "fileObject": "cr:fileObject", "fileSet": "cr:fileSet",
    "format": "cr:format", "includes": "cr:includes", "isLiveDataset": "cr:isLiveDataset", "jsonPath": "cr:jsonPath",
    "key": "cr:key", "md5": "cr:md5", "parentField": "cr:parentField", "path": "cr:path", "recordSet": "cr:recordSet",
    "references": "cr:references", "regex": "cr:regex", "repeated": "cr:repeated", "replace": "cr:replace",
    "samplingRate": "cr:samplingRate", "equivalentProperty": "cr:equivalentProperty",
    "sc": "https://schema.org/", "separator": "cr:separator", "source": "cr:source", "subField": "cr:subField",
    "transform": "cr:transform",
}


def croissant(repo: str) -> None:
    """Describe the built release in Croissant 1.0 (croissant.json), from the files as they are."""
    base = f"https://huggingface.co/datasets/{repo}/resolve/main"
    files, records = [], []
    for lang, language in (("de", "German"), ("en", "English")):
        path = OUT / "corpus" / f"anchors-{VERSION}.{lang}.jsonl"
        fid = f"corpus-{lang}"
        files.append({"@type": "cr:FileObject", "@id": fid, "name": fid, "description": f"{language} anchor passages, one JSON object per line.",
                      "contentUrl": f"{base}/corpus/{path.name}", "encodingFormat": "application/jsonlines", "sha256": sha256(path)})
        records.append({"@type": "cr:RecordSet", "@id": f"anchors_{lang}", "name": f"anchors_{lang}",
                        "description": f"The {language} anchor corpus. Row i of every space's document.{lang}.npy is the vector of line i.",
                        "key": {"@id": f"anchors_{lang}/id"},
                        "field": [{"@type": "cr:Field", "@id": f"anchors_{lang}/{col}", "name": col, "description": desc, "dataType": "sc:Text",
                                   "source": {"fileObject": {"@id": fid}, "extract": {"column": col}}}
                                  for col, desc in (("id", "Passage identifier: dump, language, Wikipedia page id and passage number."),
                                                    ("text", "Passage text as embedded, after the model's document prefix."))]})
    files += [
        {"@type": "cr:FileSet", "@id": "vectors", "name": "vectors", "description": "Document-role vectors per space and language, float32, unit length, NumPy format.",
         "containedIn": {"@id": "repo"}, "encodingFormat": "application/x-npy", "includes": "spaces/*/document.*.npy"},
        {"@type": "cr:FileSet", "@id": "cards", "name": "cards", "description": "Embedding Space Card of each space.",
         "containedIn": {"@id": "repo"}, "encodingFormat": "application/json", "includes": "spaces/*/card.json"},
        {"@type": "cr:FileSet", "@id": "adapters", "name": "adapters", "description": "A worked orthogonal adapter and its Adapter Manifest.",
         "containedIn": {"@id": "repo"}, "encodingFormat": "application/octet-stream", "includes": "adapters/*"},
    ]
    files.insert(0, {"@type": "cr:FileObject", "@id": "repo", "name": "repo", "description": "The dataset repository on the Hugging Face Hub.",
                     "contentUrl": f"https://huggingface.co/datasets/{repo}", "encodingFormat": "git+https", "sha256": "main"})
    doc = {
        "@context": CROISSANT_CONTEXT, "@type": "sc:Dataset", "conformsTo": "http://mlcommons.org/croissant/1.0",
        "name": f"Embedding Anchors {VERSION}",
        "description": "Public anchor passages from German and English Wikipedia and the vectors that five open embedding models assign to them, "
                       "with an Embedding Space Card per space and one worked adapter. Paired vectors let anyone fit and measure a map between two spaces.",
        "license": "https://creativecommons.org/licenses/by-sa/4.0/", "url": f"https://huggingface.co/datasets/{repo}",
        "version": VERSION.lstrip("v") + ".0", "datePublished": "2026-11-23", "inLanguage": ["de", "en"],
        "keywords": ["text embeddings", "vector search", "model migration", "interoperability", "retrieval"],
        "creator": {"@type": "sc:Person", "name": "Egbal Waldmann", "url": "https://orcid.org/0000-0003-2958-5121"},
        "citeAs": "@misc{waldmann2026anchors, author = {Waldmann, Egbal}, title = {Publish the Anchors: A Minimal Interoperability Standard "
                  "for Text Embedding Spaces, with a Cross-Vendor German Migration Study}, year = {2026}, doi = {10.5281/zenodo.24484736}}",
        "distribution": files, "recordSet": records,
    }
    (OUT / "croissant.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("croissant:", OUT / "croissant.json")


def kaggle(repo: str) -> Path:
    """Same files in a second folder with Kaggle's metadata file; upload with the Kaggle CLI."""
    out = OUT.with_name(OUT.name + "-kaggle")
    if out.exists():
        shutil.rmtree(out)
    for src in sorted(p for p in OUT.rglob("*") if p.is_file()):
        place(src, out / src.relative_to(OUT))
    card = (out / "README.md").read_text(encoding="utf8").split("---", 2)[2].lstrip()  # without the Hub's front matter
    start, end = card.index("```python"), card.index("```", card.index("```python") + 9) + 3
    usage = f'''```python
import numpy as np
import kagglehub

root = kagglehub.dataset_download("{repo}")
X = np.load(f"{{root}}/spaces/bge-m3/document.de.npy")                  # source space
Y = np.load(f"{{root}}/spaces/multilingual-e5-large/document.de.npy")   # target space

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
```'''
    card = card[:start] + usage + card[end:]
    (out / "README.md").unlink()  # the file may be a hard link to the Hub's card, which must stay as it is
    (out / "README.md").write_text(card, encoding="utf8")
    meta = {
        "title": f"Embedding Anchors {VERSION}",
        "subtitle": "Public anchor texts and their vectors for five open embedding models",
        "id": repo,
        "licenses": [{"name": "CC-BY-SA-4.0"}],
        "keywords": ["nlp", "text", "transformers"],
        "description": card,
    }
    (out / "dataset-metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("kaggle folder:", out)
    return out


if __name__ == "__main__":
    repo = sys.argv[2] if len(sys.argv) > 2 else "egbalwaldmann/embedding-anchors"
    if len(sys.argv) > 1 and sys.argv[1] == "--croissant":  # describe the release as it is, without building it again
        croissant(repo)
        sys.exit()
    build(repo)
    croissant(repo)
    if len(sys.argv) > 1 and sys.argv[1] == "--upload":
        upload(repo)
    if len(sys.argv) > 1 and sys.argv[1] == "--kaggle":  # then: kaggle datasets create -p <folder> --dir-mode zip
        kaggle(sys.argv[2])
