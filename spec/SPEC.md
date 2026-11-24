# Embedding Space Card, Anchor Embeddings and Adapter Manifest

Specification, version 0.1 (draft)

The key words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.

## 1. Purpose

Vectors from two embedding models cannot be compared. This specification does not make them comparable. It makes three things explicit and machine-readable, so that anyone can find out whether and how well an index can be carried from one model to another:

1. what defines an embedding space (the *Embedding Space Card*),
2. paired data between any two published spaces (the *anchor embeddings*),
3. how well a given map between two spaces works (the *Adapter Manifest*).

## 2. Terms

- **Space.** The set of vectors produced by one encoder in one configuration. Two vectors are directly comparable if and only if they come from the same space.
- **Role.** The way a text enters the encoder, typically `document` or `query`. Roles of one card share one space but may use different prefixes or task types.
- **Anchor corpus.** A fixed, public, versioned list of texts.
- **Anchor embeddings.** The vectors of an anchor corpus in one space and one role.
- **Adapter.** A map in one direction: it reads vectors of its source space and writes vectors of its target space.
- **Index translation.** A use of an adapter: stored vectors of the source space are mapped into the target space and searched with native queries of the target space.
- **Query translation.** The other use: queries embedded in the source space are mapped into the target space and searched against an index stored in the target space. The model that is being replaced is then the target of the adapter, not its source.

## 3. Embedding Space Card

A card is a JSON document that validates against `embedding-space-card.schema.json`.

1. A card MUST carry a `space_id` of the form `<publisher>/<model>@<revision>[:<variant>]`.
2. The publisher MUST issue a new `space_id` whenever old and new vectors are no longer directly comparable. This includes a change of weights behind an unchanged model name, a change of output dimensions, a change of truncation or normalisation, and a change of a prefix or task type that is part of a role.
3. A card MUST state the output dimensions, the similarity measure, whether vectors are unit length as published, and every role with its prefix or task type. The roles of one card are those whose vectors are meant to be compared with each other, typically `document` and `query`. A task type that is not meant to be searched against them is a different space and needs its own card.
4. If the output is shorter than the native output of the encoder, the card MUST state how it was shortened and whether the result was renormalised.
5. A card SHOULD state the token limit and what happens to longer inputs.
6. `compatible_with` MAY list other spaces whose vectors the publisher guarantees to be directly comparable. A space MUST NOT be listed there on the strength of an adapter.
7. A system that stores vectors SHOULD store the `space_id` with them and SHOULD refuse to compare vectors with different `space_id`s unless an adapter is applied.

## 4. Anchor corpus

1. An anchor corpus is a UTF-8 JSON Lines file. Every line is an object with the fields `id` (string, unique within the corpus) and `text` (string).
2. The order of the lines is part of the corpus. Row *i* of every embedding file refers to line *i*.
3. A corpus is identified by a `corpus_id` and the SHA-256 of the file. A published corpus MUST NOT change. A corrected or extended corpus gets a new `corpus_id`.
4. The texts MUST be public and redistributable.

## 5. Anchor embeddings

1. For every space it publishes, a publisher MUST publish the embeddings of the anchor corpus in the `document` role. A publisher MAY publish them in further roles of the card.
2. The vectors MUST be produced exactly as the card describes: same revision, same dimensions, same prefix or task type, same token limit, same normalisation. A text enters the encoder as `prefix + text` with nothing else added.
3. An embedding file holds one matrix of shape (number of anchors, dimensions) in 32-bit floating point, in the order of the corpus. Allowed formats are NumPy `.npy`, Parquet and safetensors.
4. The card lists each file under `anchors` with the `corpus_id`, the SHA-256 of the corpus, the role, a URL and SHOULD list the SHA-256 of the file.
5. Third parties MAY publish anchor embeddings of a space they did not create. They MUST then say, wherever they publish them, that the vectors do not come from the model's provider.

## 6. Adapter Manifest

A manifest is a JSON document that validates against `adapter-manifest.schema.json`.

1. A manifest MUST name the source and target `space_id`, the type of map, a URL and SHA-256 of its weights, the anchor corpus it was fitted on (or `private` for pairs from a private collection) and the number of pairs. It SHOULD state whether the vectors were centred before the map was fitted (`centred`); the means then belong to the weights.
2. A manifest MUST contain at least one evaluation. An evaluation names a benchmark, the mode (`index-translation` or `query-translation`), a retrieval metric and the value reached through the adapter (`bridged`). It gives the same metric with documents and queries both embedded in the target space (`native_target`) and in the source space (`native_source`).
3. The native value of the space the queries were embedded in is the reference of a full re-embed and MUST be given: `native_target` for index translation, `native_source` for query translation. The other native value is that of the model whose stored vectors are searched; it SHOULD be given where it can be measured.
4. An adapter without an evaluation is not conformant. Fit quality, such as the cosine between mapped and true vectors, is not an evaluation.
5. An adapter does not make two spaces compatible in the sense of section 3.6.

## 7. Conformance

- A **card** conforms if it validates against the schema and satisfies section 3.
- A **space** conforms if it has a conforming card and anchor embeddings according to section 5 for at least one public anchor corpus.
- An **adapter** conforms if it has a manifest according to section 6.

## 8. Security considerations

Text can be reconstructed from embeddings, and a map between two spaces carries such an attack from one space to the other. Anchor embeddings make maps cheap to fit. They contain public texts only and reveal nothing about any private collection, but operators should treat a vector index with the same care as the text it was computed from, whether or not anchors are published for its space.

## 9. Versioning

This document and both schemas carry the version `0.1` in `spec_version`. Changes that invalidate existing cards or manifests will raise the first number after 1.0; until then any change may do so.
