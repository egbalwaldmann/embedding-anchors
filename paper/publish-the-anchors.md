# Publish the Anchors: A Minimal Interoperability Standard for Text Embedding Spaces, with a Cross-Vendor German Migration Study

Egbal Waldmann ([ORCID](https://orcid.org/0000-0003-2958-5121)), AI Engineer, Potsdam, Germany. Preprint, November 2026.

DOI: [10.5281/zenodo.24484736](https://doi.org/10.5281/zenodo.24484736) · Code and specification: https://github.com/egbalwaldmann/embedding-anchors · Anchor corpus: https://huggingface.co/datasets/egbalwaldmann/embedding-anchors

This is a text version of the PDF, made for screen readers, search and language models. Figures are given by their captions and descriptions; numbers and wording are those of the PDF.

## Abstract

A vector index is tied to the embedding model that wrote it: vectors from two models cannot be compared, so a model change means embedding every document again. Maps fitted on paired vectors translate between some spaces and fail for others, and operators cannot tell in advance which case applies, because nothing about an embedding space is published in a comparable form. We propose a minimal standard that makes the question answerable without asking providers to change their models: an Embedding Space Card that states what must be identical for two vectors to be comparable, a public anchor corpus whose embeddings every provider publishes for every model version, and an Adapter Manifest that ties a map between two spaces to a measured retrieval result. We measure translation on two German Wikipedia testbeds and a private German archive, between five open models and from two commercial spaces. With an orthogonal map fitted on up to 20,000 anchor pairs from the collection, a translated index keeps on average 95.7%, 95.1% and 88.0% of the nDCG@10 of a full re-embed. It is almost always worse than keeping the old model and never better beyond the noise of the query sample, even when the old model is much weaker: a translated index inherits the limits of the model that wrote it. An index that mixes translated and re-embedded vectors is worse than a fully translated one. Anchors in the query role do not help, so the standard asks for the document role only. Wikipedia anchors cost 7.9 percentage points on the archive, a gap no longer visible once the translated index is fused with BM25 under a tuned weight. Neither the similarity of two anchor matrices nor the accuracy of a map on held-out anchors predicts the size of the loss, so the manifest requires a measurement. Translation keeps an index searchable when its model is gone. It is not a substitute for re-embedding and not an upgrade.

Keywords: text embeddings, vector search, model migration, interoperability, retrieval, AI engineering, artificial intelligence

## 1 Introduction

Retrieval over embeddings is a standard building block of applications built on foundation models, above all of retrieval-augmented generation [1]. Dense retrieval stores one vector per passage and answers a query by comparing its vector with the stored ones. The comparison is only meaningful if both vectors come from the same model in the same configuration. Change the model, and the stored vectors become unusable: the new query vectors live in a different space ([Figure 1](#fig-problem)). The standard remedy is to embed the whole corpus again.

**Figure 1.** What a change of model does to a stored index. As long as documents and queries are embedded by the same model, comparing vectors finds the passages that answer a query. A query from another model lives in a different space, and the comparison means nothing.

Providers say so plainly. Google documents that the spaces of `gemini-embedding-001` and its successor are incompatible and that all data must be re-embedded [2]. Jina states that v3 vectors cannot search v2 vectors and the reverse [3]. The one shipped exception is narrow: Voyage 4 offers a shared space across the models of one generation of one vendor [4], and the vendor’s migration guide treats embeddings from all other model pairs as not comparable [5].

The cost is not only compute. In the private document archive that motivates this paper (about 27,800 passages of German text), a change of embedding provider left the index effectively unsearchable until every passage had been embedded again; an index that held vectors of both models returned nothing useful. Two months later a spending limit stopped the embedding API altogether, and new documents could be stored but not made searchable. Both incidents have the same root: the index depends on one model that only its provider can run.

> The index depends on one model that only its provider can run.

Research offers a way out that is still unsettled. A map fitted on paired vectors can carry one space into another. For two upgrades, each between similar models, this recovers 95–99% of the recall of a full re-embed [6], and even unpaired translation is possible [7]. Against this, simple maps work for some model pairs and fail sharply for others [8], and a recent large study finds that adapter bridges, within and across families, almost always perform worse than staying with the old model, and that reuse of the old index defers the re-embed and does not avoid it [9].

For an operator, the practical problem is that the outcome cannot be known beforehand. Whether a map between space $`A`$ and space $`B`$ works is an empirical property of that pair and of the collection, and today the only way to find out is to embed a sample of one’s own data with both models. An operator who still holds the texts can do half of this after the old model is gone: the stored vectors are the old model’s side of the pairs, and embedding the same texts with a candidate model supplies the other side. We did so for the production index of the archive.

What cannot be recovered without the old model is everything that needs a new vector from it: a query in the old space, and with it the reference point of simply staying; pairs in the query role; and pairs for an index whose texts are not at hand. Nor can anything be said about a candidate model before a sample has been embedded with it, or about a map that somebody else has fitted on data that are not public.

Before the measurements reported here, several things were open. For German text, for stored vectors of commercial models and for a specialised collection, translation between embedding spaces had not been measured. It was not known whether a translated index can reach the old model it comes from, how many pairs a map needs, whether public anchors can stand in for pairs from the collection, or whether the outcome can be told in advance without a retrieval test. The experiments could have come out either way on each of these, and on two of them, the upgrade from a weak model and the forecast from anchors, the answer is negative.

This paper makes three contributions.

1.  **A minimal standard** ([Section 3](#sec-proposal)) that asks providers for one publication per model version: a machine-readable description of the space and the embeddings of a fixed public anchor corpus. With anchors published, anyone can fit a map between any two spaces from public data alone, compare candidate target spaces before embedding anything, and check a map that someone else has fitted; this includes spaces whose model is no longer served. The standard does not require models to be compatible; it makes compatibility measurable.
2.  **A cross-vendor, German-language measurement** ([Section 4](#sec-experiments)). Earlier migration studies use open models and English text. We measure translation between five open multilingual models from three architectural families and from two commercial spaces (Cohere `embed-multilingual-v3.0`, Google `gemini-embedding-001`) into open ones, on two German Wikipedia testbeds with human queries and on a private German archive. A much weaker old model serves as a further source, and we measure the state a running migration passes through, an index that holds translated and re-embedded vectors side by side.
3.  **Evidence on the design of the anchor corpus**: how many anchors are needed, whether generic public anchors can stand in for in-domain pairs, whether anchors in another language transfer, whether anchors are needed in the query role, and how much of the loss a lexical retriever recovers in hybrid search.

The paper first places the proposal in the literature, then states it ([Section 3](#sec-proposal)), describes the experiments ([Section 4](#sec-experiments)) and their results, and ends with what follows for operators and for the standard ([Section 6](#sec-discussion)). The terms and abbreviations of the paper are collected in [Appendix E](#app-terms), which also explains how model names, testbeds and abbreviations are set; readers who have not worked with embeddings may start with [Appendix A](#app-background), and a German abstract is in [Appendix F](#app-german).

## 2 Related Work

**Aligning embedding spaces.** Linear maps between independently trained word-embedding spaces were introduced for translation [10], constrained to orthogonal maps [11] and later learned without parallel data [12]. For sentence embeddings, vec2vec learns translations without paired data [7], and mini-vec2vec reaches similar quality with a linear map at far lower cost [13]. Embedding-Converter trains a converter between models to avoid re-embedding [14]. Maystre et al. prove that two sets of embeddings whose pairwise dot products approximately agree are approximately related by an orthogonal map, with a tight bound on the alignment error [15]. Hamideche et al. test nine models and find that linear translators work for some pairs and fail for others [8].

**Why alignment might be possible at all.** The Platonic Representation Hypothesis argues that representations of large models converge [16]. A re-analysis finds that the global convergence largely disappears once similarity scores are calibrated against a permutation null that removes the effect of model width and depth, and that only local neighbourhood similarity retains significant agreement [17]. Relative representations describe each item by its similarities to a fixed anchor set, which makes independently trained spaces comparable [18], and closed-form translations between encoders can be estimated from paired anchors [19]. Our proposal turns the anchor idea into a publication requirement.

**Compatibility by training.** Backward-compatible training makes a new model’s features directly comparable with the old ones, which its authors report as achieved without sacrificing accuracy [20], while later work finds that it can significantly hinder the new model [21]. Forward-compatible training stores side information with each item to ease later transformation [21]. Query drift compensation projects the queries of an updated model into the old space [22]. These methods need control over training and therefore work only within one provider; the shared space of the Voyage 4 models is a shipped case of compatibility within one provider [4]. Matryoshka training gives compatibility across dimensions of one model, not across models [23].

**Migration adapters for vector databases.** Drift-Adapter maps new queries into the old index space with an orthogonal, low-rank or small residual network adapter fitted on a sample of re-embedded documents. It reports 95–99% of the recall of a full re-embed, measured against the new model’s own nearest neighbours, for two upgrades between similar models (MiniLM to MPNet, which the author places in one architectural family, and CLIP ViT-B to ViT-L); for a change of architecture, from GloVe to MPNet, the same paper reports 59–72% [6]. Zhao et al. replay complete migrations for sixteen model pairs on a one-million-passage MS MARCO subsample and a code corpus, with scale replays on all 8.8 million passages for three pairs. Adapter bridges perform below the old model on every pair but one of the fifteen that are not an identity control, including pairs within a family; only the bridge between two language-model embedders of one family clears it, by a margin the authors consider too small to count as an improvement [9]. Both studies use open models and, for text, English corpora; Drift-Adapter adds an image set and Zhao et al. a code corpus. Neither covers commercial spaces, other languages, or public versus in-domain anchors. Zhao et al. include lexical candidates in some migration strategies, but do not study hybrid search as a way to recover what a bridge loses.

**Standardisation.** Model cards [24] and datasheets for datasets [25] established short structured documents that travel with a model or a dataset; the card proposed here is such a document for the one property they do not cover, the identity of the vector space. The Chrome team’s Semantic Embedder API explainer proposes metadata with an embedding-space identifier so that developers know when to re-index, and asks whether a standard for embedding spaces is needed, comparable to codecs or language codes [26]. The same proposal has been submitted to the W3C Web Machine Learning Community Group and names the same identifier as part of the metadata [27]. Observability conventions and benchmark metadata name the model but do not describe the space. We found no adapter format with a required measurement and no shared anchor corpus.

**Security.** Text can be reconstructed from embeddings [28], even without any training or leaked pairs of embeddings and text, given only query access to the target model [29], and translation between spaces carries such attacks from one space to another [7]. Published anchors lower the cost of exactly this translation; we return to the trade-off in [Section 6](#sec-discussion).

## 3 Proposal: Cards, Anchors, Manifests

The proposal has three parts ([Figure 2](#fig-overview)). Each is useful alone; together they let an operator answer, before committing to a migration, whether an index can be carried into another space and at what loss. JSON Schemas are in the repository, and [Appendix B](#app-examples) shows a card and a manifest. [Figure 5](#fig-documents) sets out what the two documents hold.

> The standard does not require models to be compatible. It makes compatibility measurable.

**Figure 2.** The standard and what it is for. (a) Every provider embeds the same public anchor corpus and publishes the vectors with an Embedding Space Card the two matrices are paired data, on which anyone can fit a map and record its measured result in an Adapter Manifest. (b) Index translation maps the stored vectors once and searches them with native queries of the new model. (c) Query translation leaves the index as it is and maps every query. Orange marks the space of the old model, blue that of the new one.

### 3.1 Embedding Space Card

Two vectors are comparable if and only if they come from the same *space*. A space is narrower than a model name. The same model yields different spaces when the output is truncated to another dimension, when a different task type or prefix is used, or when the weights behind a stable model name change. The card states everything that defines the space:

- `space_id`: a stable identifier of the form `publisher/model@revision:variant` ([Figure 3](#fig-space-id)). Any change that makes old and new vectors incomparable requires a new identifier.
- model identity: publisher, name, pinned revision, optionally a hash of the weights;
- geometry: dimensions, native dimensions, how truncation was done and whether vectors were renormalised, similarity measure, whether vectors are unit length;
- input handling: per role the prefix or task type, the token limit and what happens beyond it. A card lists the roles whose vectors are meant to be compared with each other, typically document and query; a task type that is not meant to be searched against them, such as classification, is a different space with its own card;
- `compatible_with`: other spaces the publisher guarantees to be directly comparable, which covers compatibility by training;
- `anchors`: where the embeddings of public anchor corpora in this space can be downloaded.

**Figure 3.** The parts of a space identifier, here that of bge-m3 in the anchor release. Vectors with different identifiers are not comparable, unless the card of one space lists the other under `compatible_with`.

A vector database that stores the `space_id` with each index can refuse to mix spaces. That alone would have turned the silent failure described in the introduction into an error message.

### 3.2 Anchor corpus

An anchor corpus is a fixed, public, versioned list of text passages with a checksum. The requirement the standard places on a provider is this: *for every model version, publish the card and the embeddings of the anchor corpus* in the document role. For a provider this costs one batch job per release. For everyone else it creates paired data between any two spaces that were ever published, without access to either model: the pairs for spaces $`A`$ and $`B`$ are simply the two published matrices, row by row ([Figure 4](#fig-intuition)).

**Figure 4.** The same anchor texts as points in two spaces, drawn in two dimensions. Each model arranges the texts in its own way. Where the two arrangements have nearly the same shape, a turn and a shift fitted on the anchors lay one over the other and carry every other vector along. This works only approximately: the translated vector of a document lands near the vector the new model would write, not on it.

> For a provider this costs one batch job per release.

This has three consequences. Maps can be fitted by third parties, published and checked by anyone. A space remains translatable after its model is retired, even for an index whose texts are no longer at hand, because the anchors outlive the API. And compatibility can be roughly estimated before any text is embedded or any map is fitted, from the two anchor matrices alone, for example by comparing their pairwise similarity structure ([Section 5.7](#sec-predict)).

The requirement covers one role. A provider may publish the anchors in further roles of the card, but in our experiments anchors embedded in the query role did not improve the translation of queries ([Section 4](#sec-experiments)), and a standard that wants to be adopted should not ask for more than it can justify.

Published anchors do not replace an operator’s own pairs. Where the texts and a new model are at hand, the operator can make pairs from the collection itself, which are the better basis ([Section 4](#sec-experiments)); public anchors are the common yardstick and the fallback. How large the corpus must be, and whether one generic corpus serves specialised domains and several languages, are empirical questions. Our experiments address them for German. One provider has in effect already published anchors: Cohere released its embeddings of the full Wikipedia in many languages [30]. Our public anchors are drawn from that release, so one commercial space is covered from the start.

### 3.3 Adapter Manifest

An adapter is a map from a source space to a target space. The manifest records the two `space_id`s, the type of map, a checksum of its weights, the anchor corpus and number of pairs it was fitted on, and at least one *measurement*: a named benchmark, the mode of use, and the retrieval metric for the system served through the adapter next to the same metric after a full re-embed and, where available, when staying on the old model. An adapter without a measurement is not conformant. This is deliberate. The literature shows that maps between some pairs do not work, and a format that lets them circulate without numbers would spread failures.

> An adapter without a measurement is not conformant.

**Figure 5.** The two documents of the standard with their fields, named as in the JSON Schemas. A card describes one space. A manifest names two cards, the map between them, the anchors it was fitted on and at least one measured result. Which native value is the reference of a full re-embed depends on the mode ([Figure 6](#fig-direction)).

The manifest distinguishes two modes. In *index translation* the stored document vectors are mapped once into the new space and searched with native queries of the new model. In *query translation* the old index stays and each query of the new model is mapped into the old space. The first changes the index, the second adds a step to every query. With an orthogonal map the two modes are nearly the same computation: the map of one direction is the transpose of the other and a rotation leaves cosines unchanged, so the modes differ only through the centring of the two spaces and, where the dimensions differ, through the projection; how much that matters is an empirical question. Maps with more freedom have no such symmetry. A map has one direction: the manifest names the space it reads and the space it writes, and each measurement names the mode it was taken in ([Figure 6](#fig-direction)). We call a system that serves through an adapter, in either mode, a *bridge*.

**Figure 6.** The direction of a map against the mode it serves in. For index translation the map carries the old space into the new one. For query translation it runs the other way, and the old model is its target. In both cases the native value of the space the queries come from is the reference of a full re-embed, and the other one is staying on the old model.

## 4 Experiments

### 4.1 Questions

1.  Between open models of different families, how much retrieval quality survives index translation and query translation, compared with a full re-embed and with staying on the old model?
2.  How well do stored vectors of two commercial spaces translate into open spaces?
3.  How many anchor pairs are needed?
4.  Can public anchors (Wikipedia) replace in-domain pairs, and do anchors in another language transfer?
5.  Does the similarity structure of two anchor matrices predict whether a map will work?
6.  How much of the loss does hybrid search with a lexical retriever recover?
7.  Do anchors embedded in the query role improve the translation of queries?
8.  Does a bridge pay off as an upgrade from a much weaker old model?
9.  What happens in an index that holds translated and re-embedded vectors side by side?

### 4.2 Spaces

**Table 1.** The embedding spaces of the study. The five open models at the top are the target of every translation and, between themselves, also its source. The two commercial spaces enter as sources through stored document vectors, Cohere v3 on Wiki-de and Gemini-001 on the Archive. MiniLM-L12 is the deliberately weak old model of [Section 5.3](#sec-upgrade). Revisions and prompts are in [Appendix C](#app-models).

| **Space** | **Model** | **Architecture** | **Dim.** |
|----|----|----|----|
| bge-m3 | `BAAI/bge-m3` | XLM-R encoder | 1,024 |
| mE5-large | `intfloat/multilingual-e5-large` | XLM-R encoder | 1,024 |
| arctic-l-v2 | `Snowflake/snowflake-arctic-embed-l-v2.0` | XLM-R encoder | 1,024 |
| Qwen3-0.6B | `Qwen/Qwen3-Embedding-0.6B` | decoder language model | 1,024 |
| EmbGemma-2 | `google/embeddinggemma-2` | Gemma encoder | 768 |
| Cohere v3 | `embed-multilingual-v3.0` | not published | 1,024 |
| Gemini-001 | `gemini-embedding-001` | not published | 1,536 |
| MiniLM-L12 | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | MiniLM encoder | 384 |

Five open multilingual models run locally ([Table 1](#tab-spaces)): bge-m3 (`BAAI/bge-m3`), mE5-large (`intfloat/multilingual-e5-large`) and arctic-l-v2 (`Snowflake/snowflake-arctic-embed-l-v2.0`), which are XLM-R encoders, the third built on the pretrained encoder of the first; Qwen3-0.6B (`Qwen/Qwen3-Embedding-0.6B`, a decoder language model); and EmbGemma-2 (`google/embeddinggemma-2`, a Gemma encoder with 768 dimensions). Two commercial spaces enter through stored document vectors only ([Figure 7](#fig-available)): Cohere `embed-multilingual-v3.0` (from the public Wikipedia release [30]; the released vectors have 1,024 dimensions and, as we found, unit length) and Google `gemini-embedding-001`, the model of the archive’s production index, truncated by the API to 1,536 dimensions and used without a task type. Each model is used with the query and document prompts its model card prescribes. As a deliberately weak old model we add MiniLM-L12 (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; 384 dimensions, input cut at 128 tokens) [31]. It serves only as the source of a translation and is not part of any mean over the open models.

**Figure 7.** Which vectors were at hand for each space. For the two commercial spaces there are no query vectors and therefore no reference for staying. For Gemini-001 there are no vectors of the public Wikipedia anchors either, which is what a provider publishing anchors would supply.

### 4.3 Testbeds

**Table 2.** The three testbeds. Queries are human-written on the two Wikipedia testbeds and generated on the Archive. On Wiki-de any passage of a page judged relevant counts. The external anchor sets and the in-domain anchors of Wiki-de hold 20,000 passages each; no anchor passage is part of a searched corpus.

| **Testbed** | **Passages** | **Queries** | **Relevance** | **In-domain anchors** | **External anchors** |
|----|----|----|----|----|----|
| Wiki-de | 135,575 | 305 | judged page | 20,000 | English Wikipedia |
| MIRACL-de | 103,103 | 305 | judged passage | 20,000 | – |
| Archive | 11,510 | 300 | one known passage | 10,000 | German Wikipedia |

**Figure 8.** The three testbeds drawn to scale: the passages that are searched, with the part that carries judgements, and the anchor sets beside them, which are never searched.

*Figure description: Bar chart, one row per testbed: the searched passages split into background and judged passages, with the number of queries and what counts as relevant; on the right the anchor sets, which are never searched.*

[Figure 8](#fig-testbeds) draws the three testbeds to scale.

**Wiki-de.** German Wikipedia passages from the Cohere release, which makes one commercial space available with public vectors: 100,000 passages from one shard as background, plus all passages of the pages that MIRACL-de [32] judges relevant for its 305 development queries, 135,575 passages from 17,177 pages in total. 305 queries have at least one relevant page in the corpus. According to the dataset card of the MIRACL corpus, passage identifiers have the form `X#Y`, where all passages with the same `X` come from one article; we found `X` to be the Wikipedia page identifier, which is stable across dumps and also appears in the identifiers of the Cohere release, so relevance transfers at page level; rankings are collapsed to pages before scoring. This testbed is easy by construction: about a quarter of its passages belong to relevant pages, the background is unrelated to the queries, and any passage of a relevant page counts as a hit. Anchors: the first 20,000 German passages of a different shard (in-domain; consecutive passages of 3,387 pages) and 20,000 English passages (cross-lingual). No anchor passage occurs in the corpus.

**MIRACL-de.** The German part of MIRACL with its original judgements at passage level [32]: all 3,103 passages that carry a judgement (3,144 judgements, 811 of them positive), plus 100,000 passages drawn uniformly from the rest of the German MIRACL corpus, 103,103 passages in total, and the same 305 development queries as in Wiki-de, here with their judgements at passage level. The judged passages were candidates that an ensemble of retrieval systems had ranked at the top for the query, so every query meets hard negatives, and only a passage judged relevant counts. Anchors: 20,000 further passages from the same uniform draw. This testbed has no commercial space.

**Archive.** A private archive of German documents, split into passages of up to 1,500 characters and embedded in production with `gemini-embedding-001`. Of the 27,809 passages in the index, 26,905 remain after removing passages without a stored vector, very short passages and exact duplicates. The archive holds many documents in several copies. Passages whose production vectors have a cosine above 0.97 are treated as near-duplicates, grouped by single linkage, and all but one of each group removed, which takes out another 5,395 passages and leaves 21,510 from 4,932 documents ([Figure 9](#fig-funnel)). Whole documents are held out as in-domain anchors (10,000 passages), so that no anchor shares a document with the 11,510 passages that are searched; the German Wikipedia anchors of Wiki-de serve as public anchors.

**Figure 9.** How the Archive testbed was cut from the production index: passages without a vector, very short passages and copies are removed, whole documents are held out as anchors, and the rest is searched.

The 300 queries are known-item questions: for one sampled passage from each of 300 documents, a language model running locally (Gemma 4, 12B) wrote one German question that the passage answers, and that passage is the query’s only relevant item. Such questions are easier than real user queries, they reward lexical overlap with the passage they were written from, and the model that wrote them belongs to the same family as one of the embedders (EmbGemma-2). Only aggregate numbers from this testbed are reported; no text from it is released.

**Input length.** The open models read Wikipedia passages up to 512 tokens, which cuts at most 0.5% of the passages on Wiki-de and 1.1% on MIRACL-de. Archive passages are longer in tokens; there each model reads up to its own limit, capped at 2,048 tokens. Only mE5-large, with a limit of 512 tokens, cuts a noticeable share (27.3% of the passages).

**Reference points.** A *full re-embed* embeds documents and queries with the new model. *Stay* keeps documents and queries in the old model’s space. For the two commercial spaces only stored document vectors were available, so the stay reference exists for the open models only. [Figure 10](#fig-serving) sets the ways of serving side by side.

**Figure 10.** Ways to serve a collection, by which model wrote the stored vectors and the query. Colour marks the space in which the two are compared: orange the old model’s, blue the new one’s. The mixed index is the subject of [Section 5.4](#sec-mixed), lexical search and its fusion with a dense ranking that of [Section 5.8](#sec-hybrid).

### 4.4 Adapters and measures

Three maps are fitted on $`k`$ anchor pairs, with $`k`$ from 100 to 20,000 as far as the anchor set reaches: an orthogonal map after centring, affine ridge regression, and a small residual network on top of the ridge solution. For query translation every map is fitted anew in the opposite direction. All anchors are passages embedded in the document role. Two controls repeat the fit, one on the same passages embedded with each model’s query prompt and one on uncentred matrices. Vectors have unit length before and after mapping, and retrieval is exact cosine search. [Figure 11](#fig-shapes) shows in a drawing what sets a rotation apart from a least-squares map and what centring does.

**Figure 11.** What distinguishes the maps, as a drawing in two dimensions and not a measurement. A rotation keeps the shape of the source space; fitted without centring it keeps the shape and misses the place. A least-squares map such as ridge regression may land closer on average and still bend the shape, so that neighbours change. The drawing leaves out that all vectors are scaled back to unit length.

[Figure 12](#fig-real-spaces) shows the orthogonal map on real vectors: sixty anchors that the map was not fitted on, in the space of bge-m3 and in that of mE5-large, where each translated vector lands close to the vector the new model writes for the same passage.

**Figure 12.** Sixty Wikipedia anchors held out from the fit, in two real spaces: as bge-m3 places them (left) and, in the space of mE5-large, as mE5-large places them and as the orthogonal map fitted on 19,000 other anchors places them (right). Each space is projected onto its own first two principal components, which hold little of the variance, so the picture shows the arrangement, not the distances. Four anchors are numbered in both panels.

*Figure description: Two scatter plots of the first two principal components. Left: sixty anchors in the space of bge-m3. Right: the same anchors in the space of mE5-large, each translated vector joined by a line to the vector that mE5-large writes for the same passage.*

We report nDCG@10 (normalised discounted cumulative gain over the first ten results, which rewards relevant items more the higher they are ranked) and Recall@10 (the share of the relevant items that appear among the first ten) against the relevance judgements and, as a label-free measure, the share of the full re-embed’s top ten that the bridged system returns. A bridge is compared with staying on the old model per query: the queries are resampled 2,000 times, and a difference in nDCG@10 whose 95% interval includes zero is called a tie ([Figure 14](#fig-tie)). Differences in nDCG@10 are given in points (hundredths), differences between relative values in percentage points. The lexical retriever is BM25, the standard ranking function over word counts. Hybrid runs fuse its ranking with the dense one by reciprocal rank fusion, with equal weights or with a weight tuned on the other half of the queries. [Appendix D](#app-methods) gives the maps, the fusion and the statistics in full.

To test whether the outcome can be predicted from published anchors alone, we compute three similarity measures between the two anchor matrices of a pair of spaces, on 2,000 anchors: the Spearman correlation of their pairwise cosine similarities (representational similarity analysis, RSA [33]), linear centred kernel alignment (CKA [34]), and the mean overlap of each anchor’s ten nearest anchors in the two spaces. All three are invariant to rotation and need no map ([Figure 13](#fig-measures)). [Figure 15](#fig-design) counts the combinations of pair, mode, map and anchor budget measured for the open models.

**Figure 13.** What the three similarity measures compare, as a drawing. None of them needs a map, and all three give the same value when one of the spaces is turned.

**Figure 14.** How a translated index is compared with the old model, for three pairs of spaces on Wiki-de. Top: the difference in nDCG@10 per query; most queries are unaffected. Bottom: the mean difference over 2,000 query sets drawn with replacement, and the interval that holds the middle 95% of them. An interval below zero means below the old model, one that includes zero is a tie.

*Figure description: Three columns, one per pair of spaces on Wiki-de. Top: the difference per query between the translated index and the old model, most of them zero. Bottom: the distribution of the mean difference over 2,000 resampled query sets with its 95% interval; the first two intervals lie below zero, the third includes zero.*

**Figure 15.** The measured combinations of the pairs of open models, testbed by testbed. These 2,920 combinations are the basis of the comparison with the old model in [Section 5.2](#sec-open).

## 5 Results

[Figure 16](#fig-glance) gathers the main results before the sections below take them apart.

**Figure 16.** The results at a glance: nDCG@10 in per cent of a full re-embed, mean and range over the pairs of spaces, orthogonal map. The top two rows use all in-domain anchors each row below changes one thing against the first. A testbed is missing where the setting was not measured on it.

*Figure description: Dot plot with one row per setting and one marker per testbed, nDCG at 10 in per cent of a full re-embed with the range over the pairs: index and query translation between 85 and 96 per cent, with 1,000 anchors lower, a mixed index and the weak MiniLM-L12 far lower.*

### 5.1 Reference points

**Table 3.** Retrieval quality of each open space after a full re-embed, and of BM25. For an old model these numbers are also the *stay* reference.

<table>
<thead>
<tr>
<th></th>
<th></th>
<th colspan="2"><strong>Wiki-de</strong></th>
<th colspan="2"><strong>MIRACL-de</strong></th>
<th colspan="2"><strong>Archive</strong></th>
</tr>
<tr>
<th><strong>Space</strong></th>
<th><strong>Dim.</strong></th>
<th><strong>nDCG@10</strong></th>
<th><strong>R@10</strong></th>
<th><strong>nDCG@10</strong></th>
<th><strong>R@10</strong></th>
<th><strong>nDCG@10</strong></th>
<th><strong>R@10</strong></th>
</tr>
</thead>
<tbody>
<tr>
<td>bge-m3</td>
<td>1,024</td>
<td>0.943</td>
<td>0.972</td>
<td>0.789</td>
<td>0.950</td>
<td>0.630</td>
<td>0.790</td>
</tr>
<tr>
<td>mE5-large</td>
<td>1,024</td>
<td>0.944</td>
<td>0.965</td>
<td>0.805</td>
<td>0.960</td>
<td>0.589</td>
<td>0.767</td>
</tr>
<tr>
<td>arctic-l-v2</td>
<td>1,024</td>
<td>0.951</td>
<td>0.977</td>
<td>0.801</td>
<td>0.960</td>
<td>0.659</td>
<td>0.813</td>
</tr>
<tr>
<td>Qwen3-0.6B</td>
<td>1,024</td>
<td>0.945</td>
<td>0.976</td>
<td>0.764</td>
<td>0.939</td>
<td>0.587</td>
<td>0.773</td>
</tr>
<tr>
<td>EmbGemma-2</td>
<td>768</td>
<td>0.944</td>
<td>0.977</td>
<td>0.775</td>
<td>0.951</td>
<td>0.633</td>
<td>0.787</td>
</tr>
<tr>
<td>BM25</td>
<td>–</td>
<td>0.787</td>
<td>0.843</td>
<td>0.464</td>
<td>0.662</td>
<td>0.605</td>
<td>0.790</td>
</tr>
</tbody>
</table>

**Figure 17.** The reference points of [Table 3](#tab-native) at a glance: nDCG@10 (filled) and Recall@10 (open) of each open model after a full re-embed, of the weak old model MiniLM-L12 ([Section 5.3](#sec-upgrade)) and of BM25.

*Figure description: Dot plot per testbed: nDCG at 10 and Recall at 10 of five open models, of the weak old model and of BM25.*

[Table 3](#tab-native) gives the reference points and [Figure 17](#fig-native) shows them side by side. On Wiki-de the five open models lie within 0.8 points of nDCG@10 of each other and close to the ceiling, well above BM25. MIRACL-de is harder and separates the models: they spread over 4.1 points, between 0.764 and 0.805. On the Archive the models spread over 7.2 points and BM25 lies among them, which is plausible for questions written from the passage they are meant to find.

Two re-embedded indexes do not return the same passages even without translation. The top tens of two different open models share on average 63.3% of their passages on Wiki-de, 80.9% on MIRACL-de and 48.2% on the Archive. The overlap figures below have to be read against this.

### 5.2 Translation between open models

**Figure 18.** Retrieval quality of a translated index (solid) and of translated queries (dashed), relative to a full re-embed, against the number of anchor pairs. Means over all ordered pairs of open models, in-domain anchors open markers: residual network. Grey lines: the individual pairs for orthogonal index translation. The unlabelled tick is 5,000. The vertical line marks 1,024 pairs, the dimension of most of the spaces, below which an orthogonal map is fitted on fewer pairs than it has directions. Dotted: staying on the old model, which averages close to 100%, since every model is source and target equally often.

*Figure description: Line chart per testbed: retrieval quality relative to a full re-embed rises with the number of anchor pairs and flattens after a few thousand; ridge regression falls behind for query translation.*

**Figure 19.** Wiki-de: nDCG@10 in per cent of a full re-embed for every pair of spaces, orthogonal map, 20,000 in-domain anchors. Empty cells are a space paired with itself; the colour scale is the same in [Figure 19](#fig-matrix-wiki), [Figure 20](#fig-matrix-miracl) and [Figure 21](#fig-matrix-archive). An asterisk marks a bridge whose nDCG@10 is at least that of the old model; the row of the commercial space has no such reference.

*Figure description: Two heat maps for Wiki-de with one cell per pair of source and target space, index translation and query translation; values between 90 and 100 per cent.*

**Figure 20.** MIRACL-de: as [Figure 19](#fig-matrix-wiki), with 20,000 in-domain anchors.

*Figure description: Two heat maps for MIRACL-de with one cell per pair of source and target space; values between 83 and 100 per cent.*

**Figure 21.** Archive: as [Figure 19](#fig-matrix-wiki), with 10,000 in-domain anchors.

*Figure description: Two heat maps for the Archive with one cell per pair of source and target space; values between 63 and 98 per cent.*

**Figure 22.** Index translation against staying on the old model, for every ordered pair of open models: the difference in nDCG@10 with its 95% interval from resampling the queries. Orthogonal map, all in-domain anchors. A filled marker is below the old model beyond the uncertainty of the query sample, an open marker is a tie.

*Figure description: Interval plot with one row per ordered pair of open models and one panel per testbed: the difference between the translated index and the old model is below zero or tied with zero for every pair.*

**Table 4.** Translation between the open models with the orthogonal map and all in-domain anchors, means over the ordered pairs. nDCG@10 in per cent of a full re-embed for index translation, its range over the pairs, and for query translation Recall@10 of index translation in per cent of a full re-embed (R@10); index translation between the three XLM-R encoders (family) and across families; and the difference between the translated and the re-embedded index in points of nDCG@10 with its 95% interval in brackets.

| **Testbed** | **Index** | **Range** | **Queries** | **R@10** | **Family** | **Across** | **Against re-embed** |
|----|----|----|----|----|----|----|----|
| Wiki-de | 95.7 | 92.0–99.0 | 94.7 | 98.1 | 98.5 | 94.6 | −4.0 \[−4.9, −3.2\] |
| MIRACL-de | 95.1 | 87.3–100.0 | 93.3 | 95.7 | 98.4 | 93.7 | −3.9 \[−4.8, −2.9\] |
| Archive | 88.0 | 79.0–98.4 | 85.1 | 93.3 | 92.5 | 86.0 | −7.5 \[−8.9, −6.1\] |

**Figure 23.** Index translation (filled) and query translation (open) at three depths of the result list, in per cent of a full re-embed: nDCG@10, Recall@10 and Recall@100. Means and range over the ordered pairs of open models, orthogonal map, all in-domain anchors.

*Figure description: Line chart per testbed: nDCG at 10, Recall at 10 and Recall at 100 in per cent of a full re-embed for index and query translation; the values rise towards 100 per cent from left to right.*

**A translated index is usable.** With the orthogonal map and all in-domain anchors, index translation keeps on average 95.7%, 95.1% and 88.0% of the nDCG@10 of a full re-embed on Wiki-de, MIRACL-de and the Archive, and query translation one to three percentage points less ([Table 4](#tab-open), [Figure 18](#fig-curves)). The pairs differ, most of all on the Archive, where the weakest keeps 79.0% ([Figure 19](#fig-matrix-wiki), [Figure 20](#fig-matrix-miracl), [Figure 21](#fig-matrix-archive)). Recall@10 survives better than nDCG@10, since a small change of the vectors more often reorders the top ten than it removes a relevant passage from them, and Recall@100 survives almost entirely ([Figure 23](#fig-depth)): what translation loses is mostly order, not passages. The family of the two models matters: between the three XLM-R encoders several points more survive than across families. On every testbed the translated index is below the re-embedded one beyond the uncertainty of the query sample.

**A translated index is not better than the old model.** For the best configuration, the orthogonal map with all in-domain anchors, index translation is below the old model’s nDCG@10 beyond the uncertainty of the query sample in 18 of 20 pairs on Wiki-de, 16 of 20 on MIRACL-de and 18 of 20 on the Archive, and tied with it in the others ([Figure 22](#fig-stay)).

> Of 2,920 measured combinations, none beat the old model beyond the noise.

The picture is the same over everything we measured. Of the 2,920 combinations of testbed, pair, mode, map, anchor set and anchor budget, which are not independent of each other, 6 reach the nDCG@10 of the old model: none of the 1,200 on Wiki-de, 6 of the 640 on MIRACL-de and none of the 1,080 on the Archive. The 6 are index translations from bge-m3 into the two other XLM-R encoders, which are stronger than bge-m3 there, and they exceed the old model by at most 0.3 points, far inside the uncertainty. In no combination is a bridge better than the old model beyond that uncertainty; it is worse beyond it in 1,176, 590 and 1,067 combinations on the three testbeds and tied in the remaining 24, 50 and 13.

Recall@10, for which we computed no intervals, is slightly more lenient: there a bridge exceeds the old model in 30 combinations on Wiki-de, 6 on MIRACL-de and 0 on the Archive, by at most 0.6 points. Where a bridge between open models scores above the full re-embed, the old model is the stronger of the two. For German text and five open models from three architectural families this agrees with Zhao et al., who find bridges below the old model on all but one of their pairs and a margin too small to count as an improvement on that one [9].

**Agreement with the new model’s own neighbours says little about retrieval quality.** The translated index returns on average 59.6% (Wiki-de), 76.2% (MIRACL-de) and 49.0% (Archive) of the ten passages that the re-embedded index returns. That is about as much as two independently embedded indexes share, and on the two Wikipedia testbeds slightly less ([Figure 24](#fig-overlap)). A bridged index finds relevant passages nearly as often as the new model, but to a considerable extent different ones, as any other model would. Results measured against a model’s own neighbours and results measured against relevance judgements are therefore not comparable.

> A translated index finds relevant passages nearly as often as the new model, but to a considerable extent different ones.

**Figure 24.** Share of the re-embedded index’s top ten that another index returns, against the nDCG@10 of that index relative to the re-embed. One point per ordered pair of open models. Blue: the old model’s index translated into the new space (orthogonal map, all in-domain anchors) and searched with the new model’s queries. Orange: the old model’s own index with its own queries.

*Figure description: Scatter plot per testbed: translated indexes and the old models' own indexes share a similar part of the re-embedded index's top ten; the old indexes lie near 100 per cent, the translated ones below.*

**Figure 25.** How faithfully a map reproduces query vectors against how well the translated queries retrieve: the mean cosine between mapped and true query vectors and the nDCG@10 relative to a full re-embed, for query translation with all in-domain anchors. A grey line joins the two maps of one ordered pair of open models.

*Figure description: Scatter plot per testbed: ridge regression reproduces query vectors with a higher cosine than the orthogonal map but retrieves worse.*

**Figure 26.** How close a map lands and how much of the order it keeps, on Wiki-de: the mean cosine between mapped and true vectors against the share of the ten nearest neighbours under the true vectors that are also among the ten nearest under the mapped ones. Left: 2,000 held-out anchors, maps fitted on 5,000 others. Right: the queries, searched among 20,000 passages. One point per ordered pair of open models and map; a grey line joins the two maps of one pair.

*Figure description: Two scatter plots for Wiki-de, cosine to the true vector against the share of the ten nearest neighbours kept. Left: held-out anchors, both maps around 60 per cent. Right: queries searched among 20,000 passages, ridge regression further right and lower than the orthogonal map.*

**The orthogonal map is the robust choice.** Ridge regression is better with few anchors: at 300 pairs it keeps 81.3% on Wiki-de against 73.2% for the orthogonal map. From 3,000 pairs onwards the orthogonal map is as good or better for index translation, and it is far better for query translation, where ridge falls to 79.3% on Wiki-de, 73.3% on MIRACL-de and 48.3% on the Archive. The two modes of the orthogonal map differ on average by 1.0, 1.8 and 2.9 points on the three testbeds, as little as its symmetry leads one to expect. The difference is small but it is not noise: averaged over the pairs, index translation is ahead of query translation by 0.9 points (95% interval 0.7 to 1.2), 1.4 points (95% interval 1.2 to 1.7) and 1.7 points (95% interval 1.4 to 2.1). Single pairs differ more, by up to 17.2 points on the Archive (arctic-l-v2 to mE5-large), so the centring is not always harmless.

Fit quality does not explain the failure of ridge. Measured by the mean cosine between mapped and true vectors, ridge is on average the more faithful map: on Wiki-de it reproduces passages it was not fitted on with a mean cosine of 0.81 against 0.76 for the orthogonal map, and queries with 0.75 against 0.72. It nevertheless ranks worse ([Figure 25](#fig-fidelity)). [Figure 26](#fig-fit-order) shows the same on Wiki-de for all twenty ordered pairs, measured as the share of the ten nearest neighbours that survive the map: among held-out anchors the two maps keep about the same share, among the passages that queries are searched in, the orthogonal map keeps more, although ridge lands closer. A least-squares map is free to change the distances between vectors, and a higher average cosine does not mean that neighbours keep their order; an orthogonal map between spaces of equal dimension leaves every distance of the source space as it was. How well a map fits is therefore no evidence of how well it retrieves, which is a further reason for the manifest to demand a retrieval measurement. The residual network on top of ridge repairs part of the damage and reaches the orthogonal map for index translation (96.0% at 20,000 pairs on Wiki-de), but not for query translation (90.3%).

> How well a map fits is no evidence of how well it retrieves.

**How many anchors.** On Wiki-de the curve flattens early: the orthogonal map reaches 91.0% with 1,000 pairs, 95.2% with 5,000 and 95.7% with 20,000. On MIRACL-de the same steps give 87.9%, 94.0% and 95.1%. On the Archive the curve is flatter at the start and still rising at the end of the anchor set, with 74.2% at 1,000 pairs, 86.7% at 5,000 and 88.0% at 10,000. A few thousand pairs carry most of what the orthogonal map delivers; how much that is depends on the collection. Below 1,000 pairs the result depends strongly on the pair.

**Table 5.** Three controls. Centring: nDCG@10 of orthogonal index translation without centring in per cent of a full re-embed (with centring: [Table 4](#tab-open)), and the number of ordered pairs that lose more than a point without it. Role: change of query translation in points of nDCG@10 when the maps are fitted on anchors in the query role instead of the document role, with its 95% interval in brackets. Draw: standard deviation, in percentage points, of the mean over the pairs across five further random draws of 1,000 and of 5,000 anchors.

| **Testbed** | **Uncentred** | **Worse** | **Role, orthogonal** | **Role, ridge** | **SD 1k** | **SD 5k** |
|----|----|----|----|----|----|----|
| Wiki-de | 89.1 | 9 of 20 | 0.1 \[−0.1, 0.4\] | −5.1 \[−5.8, −4.4\] | 0.28 | 0.05 |
| MIRACL-de | 86.0 | 14 of 20 | 0.2 \[−0.1, 0.6\] | −7.3 \[−8.0, −6.7\] | 0.28 | 0.18 |
| Archive | 74.5 | 14 of 20 | −0.6 \[−1.1, −0.1\] | −4.0 \[−4.7, −3.3\] | 0.48 | 0.39 |

**The draw of the anchors hardly matters.** Over five further random draws, the mean over the pairs for index translation has a standard deviation of at most half a percentage point, with 1,000 anchors as with 5,000 ([Table 5](#tab-controls)). A single pair varies more, by up to 2.3 points on the Archive with 1,000 anchors. The means reported here are stable; a difference of a point or two between two single pairs is not.

**Figure 27.** Two controls, one point per ordered pair of open models, nDCG@10 in per cent of a full re-embed with all in-domain anchors. Top: orthogonal index translation fitted without centring against the same map with centring; the pair that loses most is named. Bottom: query translation with maps fitted on anchors in the query role against anchors in the document role. A point on the diagonal is unchanged.

*Figure description: Six scatter plots against a diagonal. Top row: without centring single pairs fall far below the diagonal. Bottom row: anchors in the query role leave the orthogonal map on the diagonal and move ridge regression below it.*

**Figure 28.** How far the vectors of each space lie off the origin, on the 20,000 German anchors of Wiki-de: the length of their mean vector, where every vector has length 1, and the mean cosine between two anchors. Zero would mean vectors spread evenly around the origin. Centring removes this offset before the map is fitted.

*Figure description: Dot plot, one row per space: the length of the mean anchor vector lies between 0.29 and 0.83, and the mean cosine of two anchors between about 0.1 and 0.7.*

**Centring carries the orthogonal map.** Fitted on the uncentred anchor matrices, the same map is clearly worse on every testbed ([Table 5](#tab-controls); [Figure 27](#fig-controls), top), and single pairs collapse: arctic-l-v2 to mE5-large falls from 97.0% to 11.1% on the Archive. The vectors of an embedding model do not lie around the origin, the offset differs from model to model, and a rotation cannot move it ([Figure 28](#fig-offset)). Without centring, the two modes returned the same result for every pair of spaces with equal dimensions, as the symmetry of the map requires, so the difference between the modes reported above comes from the centring and from the projection between dimensions. An adapter manifest that says “orthogonal” therefore has to say whether and on what the map was centred.

**Anchors in the query role do not help** ([Figure 27](#fig-controls), bottom). With maps fitted on the same anchor passages embedded with the query prompts, orthogonal query translation hardly changes: nothing beyond the noise on the two Wikipedia testbeds and a small loss on the Archive ([Table 5](#tab-controls)). Single pairs move in both directions, between −10.7 and 5.0 percentage points on the Archive. Ridge regression, whose weakness on queries one might have blamed on the role of its anchors, gets worse with anchors in the query role on every testbed. These anchors are passages embedded as queries. Whether texts that look like queries would serve better is a different question, which a corpus of passages cannot answer; what the result does show is that the document role is a sufficient basis for the orthogonal map in both modes.

### 5.3 A much weaker old model

**Table 6.** MiniLM-L12 as the old model: nDCG@10 when staying on it, of its index translated into the five open spaces and of the open models’ queries translated into its space (means over the five open models, all in-domain anchors in brackets the share of staying), and the mean of the five open models after a full re-embed.

| **Testbed** | **Stay** | **Index, orthogonal** | **Index, ridge** | **Queries, orthogonal** | **Re-embed** |
|----|----|----|----|----|----|
| Wiki-de | 0.821 | 0.667 (81.2%) | 0.694 (84.5%) | 0.610 (74.3%) | 0.945 |
| MIRACL-de | 0.567 | 0.461 (81.4%) | 0.500 (88.2%) | 0.443 (78.2%) | 0.787 |
| Archive | 0.223 | 0.189 (84.5%) | 0.231 (103.6%) | 0.165 (73.8%) | 0.620 |

The five open models are of similar strength, so the comparison above cannot say whether a bridge pays off as an upgrade. If the new model is far better than the old one, an index that keeps most of the new model’s quality might beat staying. MiniLM-L12 is such an old model: its own nDCG@10 is 86.9% of the mean of the five open models on Wiki-de, 72.1% on MIRACL-de and 36.1% on the Archive, where its limit of 128 tokens covers only the beginning of a long passage ([Table 6](#tab-upgrade), [Figure 29](#fig-upgrade)).

**Figure 29.** MiniLM-L12 as the old model: nDCG@10 of its translated index and of translated queries against its own index, means over the five open models, against the number of in-domain anchor pairs. Horizontal lines: the mean of the five open models after a full re-embed, MiniLM-L12 kept as it is, and BM25.

*Figure description: Line chart per testbed: the translated index of the weak old model stays below that model's own retrieval quality at every number of anchor pairs, far below a full re-embed.*

Translation does not lift MiniLM-L12′s index above its own level ([Figure 29](#fig-upgrade)). With the orthogonal map and all in-domain anchors, the translated index reaches between 81.2% and 84.5% of what MiniLM-L12 delivers when it is simply kept, and translated queries against the old index less ([Table 6](#tab-upgrade)). Ridge regression does better than the orthogonal map for index translation here and comes level with staying on the Archive. That is of no practical use there: BM25 alone reaches 0.605 on the Archive, and fusing it with equal weights with so weak a dense ranking, translated (0.422) or not (0.425), pulls BM25 down. Of the 540 combinations of testbed, target, mode, map, anchor set and anchor budget, none is better than staying beyond the uncertainty of the query sample; 18 reach the old model’s nDCG@10, all of them on the Archive with at least 3,000 in-domain anchors, and 508 are worse beyond the uncertainty. Measured against the new model, the translated index keeps only 70.5%, 58.7% and 30.3% of a full re-embed.

The percentages of [Section 5.2](#sec-open) therefore describe pairs of comparable models, not a property of translation. A map rearranges the information that the stored vectors hold and adds none: what the old model did not separate stays unseparated in the new space. The quality of a translated index is bounded by the old model, whichever space it is translated into ([Figure 30](#fig-ceiling)).

**Figure 30.** The old model is the ceiling: nDCG@10 of the old model kept as it is against that of its index translated into a new space, one point per ordered pair; orthogonal map, all in-domain anchors. Above the diagonal the translated index would be better than staying. Points close to it lie within the uncertainty of the query sample ([Figure 22](#fig-stay)).

*Figure description: Three scatter plots against a diagonal, one per testbed: the nDCG at 10 of the old model kept as it is against that of its translated index; nearly all points lie on or below the diagonal, for the open models and for MiniLM-L12.*

> A map rearranges the information that the stored vectors hold and adds none.

### 5.4 A partly migrated index

**Table 7.** One index with translated and re-embedded vectors side by side: nDCG@10 in per cent of a full re-embed by the share of translated passages, means over the ordered pairs of open models (orthogonal map, all in-domain anchors a translated share of 100% is the fully translated index), and the share of translated passages in the top ten when half of the index is translated.

| **Testbed** | **10%** | **50%** | **90%** | **100%** | **In top ten at 50%** |
|-------------|---------|---------|---------|----------|-----------------------|
| Wiki-de     | 99.1    | 95.6    | 90.0    | 95.7     | 10.1%                 |
| MIRACL-de   | 95.7    | 82.3    | 77.4    | 95.1     | 25.6%                 |
| Archive     | 94.0    | 79.5    | 71.6    | 88.0     | 26.4%                 |

A migration that replaces vectors in place passes through a state in which translated and re-embedded vectors share one index. We built such indexes by taking a random 10, 50 or 90% of the passages from the translated index and the rest from the re-embedded index of the target model, and searched them with the target model’s queries ([Table 7](#tab-mixed), [Figure 31](#fig-mixed)).

**Figure 31.** An index that holds translated and re-embedded vectors side by side. Top: nDCG@10 in per cent of a full re-embed by the translated share of the index; a share of 0% is the re-embedded index, 100% the fully translated one. Bottom: the share of translated passages among the top ten. Orthogonal map, all in-domain anchors.

*Figure description: Line charts per testbed. Top: retrieval quality falls as the translated share of the index grows to 90 per cent and recovers at 100 per cent. Bottom: translated passages are under-represented in the top ten.*

A mixed index is worse than its composition suggests ([Figure 31](#fig-mixed)). With nine tenths of the passages translated it keeps 90.0%, 77.4% and 71.6% of a full re-embed, less than the fully translated index on every testbed ([Table 7](#tab-mixed)), and the weakest pair on the Archive falls to 18.8%. On MIRACL-de and the Archive the index with half of its passages translated is already below the fully translated one. The result lists show why. In the half-translated index, translated passages fill only between 10.1% and 26.4% of the top ten, not half of it. A translated vector has a cosine of about 0.8 with the vector the new model writes for the same passage, so its similarity to a native query is damped ([Figure 32](#fig-damping)), and a native passage is ranked ahead of a translated one whether or not it is the more relevant. In a fully translated index every passage carries the same handicap and the order survives. Re-embedding a translated index in place thus makes retrieval worse before it makes it better.

> Re-embedding a translated index in place makes retrieval worse before it makes it better.

**Figure 32.** Why native passages push translated ones down, for two pairs of spaces on Wiki-de: the cosine between a query of the new model and its relevant passages, as the new model embeds them (grey) and translated from the old space (blue). Top: every relevant passage. Bottom: the best relevant passage of each query, against the best passage that is not relevant, embedded by the new model (orange; here not the old model’s space). In a mixed index a translated relevant passage often loses to a native passage that is not relevant.

*Figure description: Histograms for two pairs on Wiki-de of the cosine between a query and its relevant passages. The translated vectors lie clearly to the left of the new model's own vectors, many of them below the best passage that is not relevant.*

### 5.5 From commercial into open spaces

**Table 8.** Translation from the two commercial spaces, of which only stored document vectors were available, into the open spaces: nDCG@10 in per cent of a full re-embed for index and query translation with the orthogonal map and in-domain anchors, and the share of the re-embed’s top ten that index translation returns. Cohere v3 on Wiki-de, Gemini-001 on the Archive.

| **Source** | **Target**  | **$`k`$** | **Index tr.** | **Query tr.** | **Overlap@10** |
|------------|-------------|-----------|---------------|---------------|----------------|
| Cohere v3  | bge-m3      | 1,000     | 97.2          | 96.4          | 65.7           |
|            |             | 20,000    | 98.5          | 98.5          | 71.1           |
|            | mE5-large   | 1,000     | 99.7          | 99.7          | 82.4           |
|            |             | 20,000    | 99.6          | 99.7          | 83.2           |
|            | arctic-l-v2 | 1,000     | 97.3          | 97.2          | 68.6           |
|            |             | 20,000    | 98.5          | 98.2          | 73.5           |
|            | Qwen3-0.6B  | 1,000     | 92.6          | 91.7          | 50.9           |
|            |             | 20,000    | 96.8          | 95.8          | 58.3           |
|            | EmbGemma-2  | 1,000     | 89.6          | 87.2          | 44.8           |
|            |             | 20,000    | 96.2          | 95.7          | 55.2           |
| Gemini-001 | bge-m3      | 1,000     | 60.2          | 55.8          | 36.1           |
|            |             | 10,000    | 82.2          | 80.3          | 45.1           |
|            | mE5-large   | 1,000     | 52.0          | 41.1          | 29.2           |
|            |             | 10,000    | 82.4          | 73.0          | 39.6           |
|            | arctic-l-v2 | 1,000     | 68.0          | 66.8          | 45.2           |
|            |             | 10,000    | 82.4          | 82.3          | 53.1           |
|            | Qwen3-0.6B  | 1,000     | 65.2          | 63.8          | 37.7           |
|            |             | 10,000    | 86.5          | 85.5          | 46.5           |
|            | EmbGemma-2  | 1,000     | 67.5          | 57.0          | 39.8           |
|            |             | 10,000    | 85.3          | 80.3          | 48.1           |

Stored vectors of the two commercial spaces can be translated into the open spaces as well, those of Cohere better than the average open pair and those of Gemini somewhat worse ([Table 8](#tab-closed), [Figure 33](#fig-closed)).

**Figure 33.** Translation from the two commercial spaces into the five open ones against the number of in-domain anchor pairs, orthogonal map. Grey: mean and range of index translation between the ordered pairs of open models on the same testbed.

*Figure description: Line chart for Cohere v3 on Wiki-de and Gemini-001 on the Archive: translation into five open spaces by number of anchor pairs, against the range of the open pairs.*

The public Cohere vectors reach 97.9% of a full re-embed on average over the five open targets (96.2–99.6%), and 95.3% with 1,000 anchors. That is above the average open pair, and one reason is visible in the anchors: the Cohere space is close to that of mE5-large, with a CKA of 0.96, the highest of any pair on this testbed ([Figure 35](#fig-similarity)). The archive’s production index, `gemini-embedding-001` at 1,536 dimensions, translates at 83.8% for index translation (82.2–86.5%) and 80.3% for query translation, below the mean of the open pairs on the same testbed and inside their range. For neither space could we compute the stay reference, so these numbers say what a translated index delivers, not whether it is worth giving up the old model.

### 5.6 Which anchors

**Figure 34.** In-domain anchors against external anchors, orthogonal map, ordered pairs of open models. Left: Wiki-de, German against English Wikipedia anchors. Right: the Archive, anchors from the archive against German Wikipedia anchors; the in-domain set ends at 10,000 pairs.

*Figure description: Line chart for Wiki-de and the Archive: in-domain anchors against English or German Wikipedia anchors by number of anchor pairs; the curves coincide on Wiki-de and separate on the Archive.*

**Anchors in another language cost little, anchors from another domain cost more** ([Figure 34](#fig-anchor-source)). For German Wikipedia retrieval, 20,000 English Wikipedia anchors give 95.3% against 95.7% with German ones; the weakest pair falls from 92.0% to 90.0%. For the Archive, 10,000 Wikipedia anchors give 80.1% against 88.0% with 10,000 passages from the archive itself, and the weakest pair falls from 79.0% to 61.2%; with 20,000 Wikipedia anchors the mean rises to 81.5%. Pair by pair, the Wikipedia anchors cost 7.9 percentage points of a full re-embed on average and up to 19.1 at equal size. In nDCG@10 itself and averaged over the pairs, the in-domain anchors are ahead by 4.9 points (95% interval 3.5 to 6.2) on the Archive and the German ones by 0.4 points (95% interval 0.0 to 0.8) on Wiki-de. A generic public corpus is thus clearly the weaker basis on a specialised collection, and size recovers only a small part of the difference. The two comparisons come from different testbeds and do not separate language from domain in a controlled way. For the Gemini index the comparison could not be made at all, because no vectors of the Wikipedia anchors exist in that space; this is the gap that published anchors would close.

### 5.7 What the anchors predict

**Figure 35.** Similarity of the anchor matrices of every pair of spaces, computed on 2,000 in-domain anchors without fitting a map: linear CKA above the diagonal, the mean overlap of the ten nearest anchors below it. Darker is more similar; each measure has its own scale, shared by the three panels.

*Figure description: Three triangular heat maps, one per testbed, with the similarity of every pair of spaces: linear CKA above the diagonal, neighbour overlap below.*

**Figure 36.** Similarity of two spaces, computed from 2,000 anchors without fitting a map, against the retrieval quality of orthogonal index translation between them, and, bottom right, how often a mapped held-out anchor is nearest to its own counterpart (map fitted on 5,000 anchors). One point per ordered pair of spaces.

*Figure description: Four scatter plots against retrieval quality after translation, one marker shape per testbed: three similarity measures, where the testbeds form separate clouds, and the accuracy on held-out anchors, which stands at 100 per cent for both Wikipedia testbeds.*

[Figure 35](#fig-similarity) shows two of the three measures for every pair of spaces. On the two Wikipedia testbeds the three XLM-R encoders share more of their neighbours with each other than with the other two open models; on the Archive this grouping is not visible. Within one testbed, the similarity of two anchor matrices correlates with the outcome of translation ([Figure 36](#fig-predict)). The rank correlation between nearest-neighbour overlap and relative nDCG@10 is 0.72 on Wiki-de (25 ordered pairs), 0.59 on MIRACL-de (20) and 0.58 on the Archive (25); for RSA it is 0.77, 0.68 and 0.47, for CKA 0.70, 0.48 and 0.49. The numbers of pairs are small and the ordered pairs are not independent, since both directions of a pair share one similarity value, so these are descriptions, not tests.

On the Archive the in-domain anchors are private. Similarities computed from the public Wikipedia anchors instead correlate with the same outcomes at 0.54 (nearest neighbours), 0.67 (RSA) and 0.50 (CKA) over the 20 ordered pairs of open models. Across testbeds the measures do not transfer: the same similarity value goes with a loss of a few per cent on Wiki-de and of more than a tenth on the Archive.

The correlations are also carried in part by differences between source spaces. An operator has one source and wants to choose a target; within one source space, over its four possible targets, the rank correlation averages between 0.44 for CKA and 0.64 for RSA on Wiki-de, between 0.16 and 0.72 on MIRACL-de and between 0.04 and 0.16 on the Archive, with neighbour overlap in between each time. [Figure 37](#fig-choice) shows what that means for the choice: ranked by neighbour overlap and ranked by the outcome, the four targets of a source often come out in a different order. Similarity read off published anchors is therefore a first indication of which spaces are close, and a weak guide to the choice of a target. It cannot tell how much will be lost on the operator’s own queries; that needs a measurement, which is why the manifest requires one.

A fourth candidate needs a map but no queries: fit the orthogonal map on 5,000 anchors and count how often a mapped anchor, out of 2,000 held out, is nearest to its own counterpart. On the anchors of the two Wikipedia testbeds this accuracy is saturated ([Figure 36](#fig-predict), bottom right). It lies between 99.4 and 100.0% for the pairs of Wiki-de and between 99.9 and 100.0% for those of MIRACL-de, although the retrieval outcomes of these pairs differ by more than ten points, and its rank correlation with the outcome is 0.62 and −0.05. On the in-domain anchors of the Archive it spreads from 63.7 to 98.7% and correlates with the outcome at 0.52, but within one source space only at 0.12. A map that fails this test will not retrieve; a map that passes it has shown very little.

> A map that fails on held-out anchors will not retrieve; a map that passes has shown very little.

**Figure 37.** Choosing a target from published anchors. For each source space, its four possible targets ranked by the similarity of the anchor matrices (left, overlap of the ten nearest anchors) and by the measured outcome of orthogonal index translation (right, nDCG@10 in per cent of a full re-embed). A crossing line is a target that the similarity ranks wrongly.

*Figure description: Slope charts, one per source space and testbed: the four possible targets ranked by anchor similarity on the left and by measured retrieval quality on the right; many lines cross, more on the Archive than on Wiki-de.*

### 5.8 Hybrid search

**Table 9.** nDCG@10 with and without fusion with BM25, means over the ordered pairs of open models; bridge is orthogonal index translation with $`k`$ in-domain anchors. Staying on the old model has the same means as the native columns, since every model is source and target equally often.

| **Testbed** | **$`k`$** | **BM25** | **Bridge** | **Bridge + BM25** | **Native** | **Native + BM25** |
|----|----|----|----|----|----|----|
| Wiki-de | 1,000 | 0.787 | 0.860 | 0.906 | 0.945 | 0.919 |
|  | 5,000 |  | 0.900 | 0.914 | 0.945 | 0.919 |
|  | 20,000 |  | 0.905 | 0.915 | 0.945 | 0.919 |
| MIRACL-de | 1,000 | 0.464 | 0.692 | 0.674 | 0.787 | 0.662 |
|  | 5,000 |  | 0.739 | 0.676 | 0.787 | 0.662 |
|  | 20,000 |  | 0.748 | 0.675 | 0.787 | 0.662 |
| Archive | 1,000 | 0.605 | 0.461 | 0.614 | 0.620 | 0.661 |
|  | 5,000 |  | 0.537 | 0.637 | 0.620 | 0.661 |

When the old model is gone, the alternative to a translated index is not an empty result list but lexical search, so BM25 is the bar a bridge has to clear ([Table 9](#tab-hybrid), [Figure 38](#fig-hybrid)).

**Figure 38.** nDCG@10 of dense retrieval alone and fused with BM25, with equal weights and with a weight tuned on the other half of the queries. Markers are means and bars the range, over the five open models for the re-embedded index and over the ordered pairs of open models for the translated one. Translation is orthogonal index translation with all in-domain anchors or with the same number of external anchors: English Wikipedia on Wiki-de, German Wikipedia on the Archive.

*Figure description: Dot plot per testbed with ranges: nDCG at 10 of the re-embedded and the translated index alone and fused with BM25 with equal and tuned weights, and of BM25 alone.*

**Figure 39.** How reciprocal rank fusion joins a dense and a lexical ranking, with an invented example. Passage A is second in one ranking and first in the other and comes out on top; F, found by one ranking only, falls behind.

Combining term-based and embedding-based retrieval is common practice in such systems [1]; [Figure 39](#fig-fusion) shows how two rankings are joined. On the two Wikipedia testbeds BM25 is far weaker than any dense index, and the translated index alone clears it in every pair. Fusion with so weak a lexical ranking lowers the native indexes on both testbeds, on Wiki-de from 0.945 to 0.919 and on MIRACL-de from 0.787 to 0.662. The translated index gains a little from it on Wiki-de (0.905 to 0.915) and loses on MIRACL-de (0.748 to 0.675).

On the Archive BM25 is strong (0.605). With 5,000 anchors the translated index alone reaches 0.537 and is above BM25 in only 2 of 20 pairs. Fused with BM25 it reaches 0.637 and is above BM25 alone in 19 of 20 pairs, while a native index fused with BM25 reaches 0.661. With 1,000 anchors the fusion still reaches 0.614 and is above BM25 in 13 of 20 pairs. Translated vectors thus add to lexical search even where they are weaker than it; where lexical search is far weaker than they are, fusion with equal weights gains little or loses.

> Translated vectors add to lexical search even where they are weaker than it.

**A tuned weight.** Equal weights are a blunt choice where one ranking is much stronger than the other. With the weight chosen on the other half of the queries, the fused translated index reaches 0.930 on Wiki-de (0.905 alone, 0.915 with equal weights) and 0.742 on MIRACL-de (0.748 alone, 0.675 with equal weights); the gain over equal weights is 1.5 points (95% interval 0.7 to 2.3) and 6.7 points (95% interval 5.2 to 8.3). On MIRACL-de even the largest dense weight on our grid leaves the fusion slightly below the translated index alone, and the native indexes lose as well (0.749 against 0.787). On the Archive, where the two rankings are of similar strength, tuning changes nothing: the difference is −0.2 points (95% interval −0.8 to 0.4). With all 10,000 in-domain anchors the translated index fused with equal weights reaches 0.641 there, which is 3.6 points (95% interval 0.9 to 6.3) above BM25 and 9.6 points (95% interval 7.4 to 11.8) above the translated index alone.

**Public anchors in hybrid search.** The same measurement with Wikipedia anchors changes what was said above about public anchors. A translated index of the Archive fitted on 10,000 Wikipedia anchors reaches 0.496 alone and differs from BM25 by −10.9 points (95% interval −14.7 to −7.2). Fused with equal weights it reaches 0.626, which cannot be told from BM25: the difference is 2.1 points (95% interval −0.7 to 4.7). With a tuned weight it reaches 0.640, which is 3.4 points (95% interval 1.4 to 5.5) above BM25 and at least as good as BM25 in 20 of 20 pairs; with 20,000 Wikipedia anchors it reaches 0.643. The in-domain anchors give 0.639 under the same procedure. Next to a strong lexical ranking and with a tuned weight, the disadvantage of public anchors on the specialised collection is no longer visible: what the weaker map loses, BM25 supplies.

## 6 Discussion

**Table 10.** The nine questions of [Section 4](#sec-experiments) and what the measurements say. Percentages are nDCG@10 relative to a full re-embed, in the order Wiki-de, MIRACL-de, Archive points are differences in nDCG@10 (hundredths); for the orthogonal map with all in-domain anchors unless stated otherwise.

|  | **Question** | **What the measurements say** | **Section** |
|----|----|----|----|
| 1 | How much survives translation between open models? | Index translation keeps 95.7%, 95.1% and 88.0% of a full re-embed, query translation 94.7%, 93.3% and 85.1%. No bridge is better than staying beyond the noise. | [5.2](#sec-open) |
| 2 | Do commercial spaces translate? | Cohere v3 at 97.9% on Wiki-de, Gemini-001 at 83.8% on the Archive. | [5.5](#sec-closed) |
| 3 | How many anchor pairs? | A few thousand. With 1,000 pairs: 91.0%, 87.9% and 74.2%. The random draw hardly matters. | [5.2](#sec-open) |
| 4 | Can public or foreign-language anchors replace in-domain pairs? | English anchors cost 0.4 points of nDCG@10 on Wiki-de, Wikipedia anchors 4.9 on the Archive. Under fusion with BM25 and a tuned weight that gap is no longer visible. | [5.6](#sec-anchors), [5.8](#sec-hybrid) |
| 5 | Does anchor similarity predict the outcome? | It correlates within a testbed (0.72, 0.59 and 0.58 for neighbour overlap) but does not give the size of the loss; accuracy on held-out anchors is saturated on the Wikipedia testbeds. | [5.7](#sec-predict) |
| 6 | What does lexical search add? | On the Archive the fusion reaches 0.641 against 0.605 for BM25 and 0.545 for the translated index alone. Where BM25 is weak, equal weights lower the result and a tuned weight gains little. | [5.8](#sec-hybrid) |
| 7 | Are anchors needed in the query role? | No. They change orthogonal query translation by 0.1, 0.2 and −0.6 points of nDCG@10. | [5.2](#sec-open) |
| 8 | Is a bridge an upgrade from a much weaker model? | No. None of 540 combinations is better than staying; 508 are worse. | [5.3](#sec-upgrade) |
| 9 | What happens in a partly migrated index? | It is worse than a fully translated one: 90.0%, 77.4% and 71.6% with nine tenths translated. | [5.4](#sec-mixed) |

**Figure 40.** What the measurements suggest for an operator, by what is still at hand. Orange marks the space of the old model and blue that of the new one, as in [Figure 2](#fig-overview).

[Table 10](#tab-summary) collects the answers to the nine questions, and [Figure 40](#fig-decision) turns them into the choices an operator faces.

**What translation is for.** The experiments leave no room for a bridge as an upgrade path. Wherever the old model can still embed queries, no map we fitted was better than keeping it beyond the noise of the query sample, and nearly all were worse. Between the five open models that is a matter of a few points lost in translation. With a much weaker old model it is a matter of principle: the translated index carries the old model’s limits into the new space, however good the new model is ([Section 5.3](#sec-upgrade)).

Translation is useful where staying is not possible, which is the situation that motivated this paper: the old model is retired, the provider has been left, or the budget for its API is exhausted. What remains then is lexical search, until the corpus has been embedded again. In that situation one matrix multiplication per stored vector yields an index that, with pairs from the collection itself, keeps between 79% and, for the closest pairs, nearly all of the new model’s retrieval quality, depending on the collection and the pair of spaces. Such an index was better than lexical search alone in nearly every case, on its own where BM25 is weak and fused with BM25 where it is strong. The re-embed can follow at its own pace.

For this purpose index translation is the natural mode: with the orthogonal map it was the better of the two on average on every testbed, and it leaves the query path unchanged. The re-embed should not be written into the translated index as it proceeds. A mixed index was worse than the fully translated one for most of the way, because native vectors outrank translated ones ([Section 5.4](#sec-mixed)). The new index is better built beside the translated one and put into service when it is complete ([Figure 41](#fig-paths)).

**Figure 41.** Two ways from a translated index to a re-embedded one, against the share of the collection already re-embedded: in place, so that the index holds translated and re-embedded vectors side by side (orange, from [Table 7](#tab-mixed)), or beside it, so that the translated index serves until the new one is complete (blue). nDCG@10 in per cent of a full re-embed, means over the ordered pairs of open models.

*Figure description: Line chart per testbed against the share of the collection already re-embedded: building beside keeps the level of the translated index and jumps to 100 per cent at the end; re-embedding in place first drops, by up to about 18 points, and recovers only towards the end.*

**What it costs.** The pairs are not free: every in-domain pair is a passage embedded with the new model. For a large collection a few thousand passages are a negligible share. For a small one they are not. The 10,000 pairs behind the Archive figures are 46% of its 21,510 passages, so translation saves about half of the re-embed there ([Figure 42](#fig-cost)). With 1,000 pairs, about 5% of the passages, the translated index keeps 74.2% of the new model’s quality and stays below BM25 on its own, and it still improves BM25 when fused with it in 13 of 20 pairs.

**Figure 42.** What the pairs cost: nDCG@10 of orthogonal index translation in per cent of a full re-embed, against the in-domain anchors that the new model has to embed, as a share of the collection (searched passages and anchors). Mean and range over the ordered pairs of open models. A full re-embed is 100% of the collection.

*Figure description: Line chart on a logarithmic axis: retrieval quality of index translation against the share of the collection embedded as anchors. The two Wikipedia testbeds reach about 90 per cent with under one per cent of the collection; the Archive needs more than a tenth for about 85 per cent.*

**What published anchors add.** An operator who holds the texts, the stored vectors and a new model can fit a map without any help, as we did for the Gemini index, and pairs from the collection itself were better than public ones. Published anchors serve the cases this does not reach. They allow candidate spaces to be compared before anything is embedded. They let a third party publish a map together with a measurement that others can repeat. And they cover an index whose texts are not available to whoever has to migrate it.

On the Archive a translated index fitted on public anchors was clearly weaker than one fitted on in-domain pairs, but fused with BM25 under a tuned weight it served as well, and it was better than BM25 alone. For an operator who has lost the old model and holds nothing but vectors, that is the difference between lexical search and hybrid search. What published anchors did not provide in our measurements is a reliable forecast: neither the similarity of two anchor matrices nor the accuracy of a map on held-out anchors told how much retrieval quality a translation would keep.

**What the standard has to ask for.** The anchor corpus can be small. On Wikipedia a few thousand passages carried almost all of the attainable quality; on the Archive the step from 5,000 to 10,000 in-domain pairs still added more than a point, and public anchors kept improving up to 20,000. A corpus of 20,000 passages is therefore a reasonable size; at 1,024 dimensions that is about 80 MB per model version. One role is enough. Anchors embedded in the query role did not improve the translation of queries with the orthogonal map and made ridge regression worse, so the standard asks for the document role and leaves further roles to the provider. English anchors served German retrieval, with multilingual models. The manifest should record how a map was centred, since the same orthogonal map without centring collapsed on single pairs. The requirement of a measurement in the manifest is supported by the spread of outcomes: on the Archive the same procedure keeps between 79.0 and 98.4% depending on the pair, and anchor similarity does not predict the level.

**Privacy.** Text can be reconstructed from embeddings [28], [29], and a map into a space for which an inversion model exists can carry that attack to other spaces [7]. Published anchors make such maps cheap: in our experiments 1,000 pairs were enough for about nine tenths of the retrieval quality on Wikipedia. Whoever can call a model’s API can produce such pairs today, so the standard creates no new capability for current models; it does extend the capability to models that are no longer served and to parties without API access. The practical consequence holds with or without the standard: a vector index deserves the same protection as the text it was computed from.

> A vector index deserves the same protection as the text it was computed from.

**Incentives and the alternative.** A provider gains nothing directly from making it easier to leave, and the cost of publishing anchors is one batch job per release. Cohere’s Wikipedia release shows that a provider may publish far more than the standard asks. A shared space that a provider builds into its models, as in Voyage 4 [4], is the stronger guarantee, since it needs no map; it is limited to the models one provider chooses to align, and the card’s `compatible_with` field records it. The two approaches complement each other.

**Next steps.** For a provider the step is small: publish a card and the anchor vectors with the next model release. A vector database can act without waiting for anyone, by storing a `space_id` with every index and refusing to compare across spaces. For the standard itself three things are open: anchor corpora for further languages and for specialised domains, a public register of cards and manifests, and a home in a standards body. The specification is at version 0.1, and its repository is the place for issues and proposals. The open research questions are collected in [Section 8](#sec-future).

## 7 Limitations

The study covers one language, three collections of at most 135,575 passages and exact search. Wiki-de is close to the ceiling for every model and has no hard negatives; the Archive questions are synthetic, have one relevant passage each and come from a single language model. The two Wikipedia testbeds share their queries. With about 300 queries per testbed, differences of a few points between single pairs are within noise; the intervals we report cover the sampling of queries, not the choice of models, and further draws of the anchors were made for the orthogonal map at two budgets only.

The fusion weight was tuned on half of the queries over a coarse grid that ends at a dense weight of 0.8. The in-domain anchors of Wiki-de are consecutive passages of one shard and not a random sample. mE5-large reads at most 512 tokens and so cuts 27.3% of the Archive passages short; it is the target of the weakest Archive pairs.

The five open models are of similar strength ([Table 3](#tab-native)), and the upgrade from a much weaker model rests on one old model with a short input window. The anchors in the query role were passages embedded with the query prompt; texts that look like queries were not tested. For the mixed index we tried no remedy, such as calibrating the scores of translated vectors or searching two indexes and fusing their rankings. The only specialised collection is private, so that part of the study cannot be repeated by others, while the Wikipedia testbeds and the public anchors can. The open models are small (at most 0.6 billion parameters), and the two commercial spaces entered through stored document vectors only, without a stay reference and without anchors in the query role. We tested three kinds of map; unpaired or more elaborate translators [7] may do better.

## 8 Future work

The measurements leave six questions open. Each follows from a limit of this study, and none can be answered from the data at hand.

1.  **Anchors for specialised domains.** On the Archive, public Wikipedia anchors were clearly weaker than pairs from the collection ([Section 5.6](#sec-anchors)). Whether a public anchor corpus drawn from a domain, such as legal or medical text, closes that gap for collections of the same domain is unknown. The answer decides how many anchor corpora the standard needs.
2.  **Anchors that look like queries.** Our anchors in the query role were passages embedded with the query prompt ([Section 5.2](#sec-open)). Short questions are distributed differently from passages, and whether a map fitted on them translates queries better has not been tested.
3.  **A remedy for the mixed index.** Native vectors outrank translated ones ([Section 5.4](#sec-mixed)). Calibrating the scores of translated vectors, or searching the two parts separately and fusing the rankings, might remove the dip. Neither has been tried, and it is unclear whether a calibration fitted on anchors carries over to queries.
4.  **The stay reference for commercial spaces.** For Cohere v3 and Gemini-001 only stored document vectors were at hand ([Section 5.5](#sec-closed)). The comparison with staying on the old model is therefore missing for the very spaces whose models an operator cannot run.
5.  **Larger models and other languages.** The open models have at most 0.6 billion parameters, and the text is German. Whether less is lost between larger models, as converging representations would suggest [16], is open, and so is whether the findings hold for languages with less training data.
6.  **A forecast without queries.** Neither the similarity of two anchor matrices nor the accuracy of a map on held-out anchors told the size of the loss ([Section 5.7](#sec-predict)). A measure that does, computed from published anchors alone, would let an operator choose a target without a judged query set. Whether such a measure exists is open.

## 9 Conclusion

Whether an index can be carried from one embedding space into another is an empirical property of the pair of spaces and of the collection. With an orthogonal map fitted on anchor pairs, a translated index kept on average 95.7% of the retrieval quality of a full re-embed on an easy German Wikipedia testbed, 95.1% on MIRACL-de and 88.0% on a private document archive, across five open models. Stored Cohere vectors translated into the open spaces at 97.9% on the Wikipedia testbed and stored Gemini vectors at 83.8% on the archive, where the open pairs reach 88.0%.

A bridge was almost always worse than keeping the old model and never better beyond the noise of the query sample, between models of similar strength and from a much weaker model into far stronger ones. An index that mixes translated and re-embedded vectors was worse than a fully translated one. Translation is thus a way to keep an index searchable when its model is gone, together with lexical search where that is strong. It is not a substitute for re-embedding, not an upgrade, and not an index to re-embed in place, piece by piece.

> Translation is not a substitute for re-embedding, not an upgrade, and not an index to re-embed in place, piece by piece.

How well a given index translates can only be found out with paired vectors. An operator can make them from their own collection as long as the texts and a new model are at hand; what nobody can make without the old model are vectors of new texts and of queries in the old space. We therefore ask providers of embedding models for one publication with every model version: an Embedding Space Card and the embeddings of a public anchor corpus of about 20,000 passages in the document role. We ask the W3C Web Machine Learning Community Group, which has before it a proposal that includes an embedding-space identifier [27], to consider the card as the description behind that identifier and the anchor embeddings as part of the card.

## Code and data availability

The specification with both JSON Schemas, the code of all experiments and the result files from which every result number, table and figure in this paper is generated are available at <https://github.com/egbalwaldmann/embedding-anchors>. A first anchor corpus (20,000 German and 20,000 English Wikipedia passages), its vectors in the document role for the five open models, one Embedding Space Card per space and one adapter with its manifest are available at <https://huggingface.co/datasets/egbalwaldmann/embedding-anchors>, with a mirror at <https://www.kaggle.com/datasets/egbalwaldmann/embedding-anchors>. This version of the paper is archived together with the code and the result files under the DOI [10.5281/zenodo.24484736](https://doi.org/10.5281/zenodo.24484736). The Archive testbed is private; none of its texts or vectors are released.

## Funding and competing interests

This work received no funding. The author declares no competing interests.

## References

- [1] C. Huyen, *AI Engineering: Building Applications with Foundation Models*. O'Reilly Media, 2025.
- [2] Google, “Embeddings.” \[Online\]. Available: <https://aistudio.google.com/docs/embeddings#migration>
- [3] Jina AI, “Migration From Jina Embeddings v2 to v3.” \[Online\]. Available: <https://jina.ai/news/migration-from-jina-embeddings-v2-to-v3/>
- [4] Voyage AI, “The Voyage 4 model family: shared embedding space with MoE architecture.” \[Online\]. Available: <https://blog.voyageai.com/2026/01/15/voyage-4/>
- [5] MongoDB, “Migrate to a New Embedding Model.” \[Online\]. Available: <https://www.mongodb.com/docs/voyageai/tutorials/migrate-embedding-model/>
- [6] H. Vejendla, “Drift-Adapter: A Practical Approach to Near Zero-Downtime Embedding Model Upgrades in Vector Databases,” in *Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing*, 2025, pp. 15938–15949. doi: [10.18653/v1/2025.emnlp-main.805](https://doi.org/10.18653/v1/2025.emnlp-main.805).
- [7] R. Jha, C. Zhang, V. Shmatikov, and J. X. Morris, “Harnessing the Universal Geometry of Embeddings,” in *Advances in Neural Information Processing Systems*, 2025, pp. 45963–45987. \[Online\]. Available: <https://arxiv.org/abs/2505.12540>
- [8] S. A. Hamideche, L.-A. Dufrène, Q. Lampin, and G. Larue, “How Far Do Simple Transformations Translate Across Text Embedding Models?.” \[Online\]. Available: <https://arxiv.org/abs/2608.05980>
- [9] N. Zhao, J. Zhang, T. Zhong, H. Wang, and B. Wang, “When the Bill Falls: Reusing the Old Index Defers, Never Avoids, Re-encoding in Complete Embedding-Model Migration.” \[Online\]. Available: <https://arxiv.org/abs/2611.20702>
- [10] T. Mikolov, Q. V. Le, and I. Sutskever, “Exploiting Similarities among Languages for Machine Translation.” \[Online\]. Available: <https://arxiv.org/abs/1309.4168>
- [11] C. Xing, D. Wang, C. Liu, and Y. Lin, “Normalized Word Embedding and Orthogonal Transform for Bilingual Word Translation,” in *Proceedings of the 2015 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies*, 2015, pp. 1006–1011. doi: [10.3115/v1/N15-1104](https://doi.org/10.3115/v1/N15-1104).
- [12] A. Conneau, G. Lample, M. Ranzato, L. Denoyer, and H. Jégou, “Word Translation Without Parallel Data,” in *International Conference on Learning Representations*, 2018. \[Online\]. Available: <https://arxiv.org/abs/1710.04087>
- [13] G. Dar, “mini-vec2vec: Scaling Universal Geometry Alignment with Linear Transformations.” \[Online\]. Available: <https://arxiv.org/abs/2510.02348>
- [14] J. Yoon and S. Ö. Arık, “Embedding-Converter: A Unified Framework for Cross-Model Embedding Transformation,” in *Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)*, 2025, pp. 25464–25482. doi: [10.18653/v1/2025.acl-long.1237](https://doi.org/10.18653/v1/2025.acl-long.1237).
- [15] L. Maystre *et al.*, “When Embedding Models Meet: Procrustes Bounds and Applications.” \[Online\]. Available: <https://arxiv.org/abs/2510.13406>
- [16] M. Huh, B. Cheung, T. Wang, and P. Isola, “Position: The Platonic Representation Hypothesis,” in *Proceedings of the 41st International Conference on Machine Learning*, in Proceedings of Machine Learning Research, vol. 235. 2024, pp. 20617–20642. \[Online\]. Available: <https://proceedings.mlr.press/v235/huh24a.html>
- [17] F. Gröger, S. Wen, and M. Brbić, “Revisiting the Platonic Representation Hypothesis: An Aristotelian View,” in *Proceedings of the 43rd International Conference on Machine Learning*, in Proceedings of Machine Learning Research, vol. 306. 2026, pp. 36724–36766. \[Online\]. Available: <https://proceedings.mlr.press/v306/groger26a.html>
- [18] L. Moschella, V. Maiorca, M. Fumero, A. Norelli, F. Locatello, and E. Rodolà, “Relative representations enable zero-shot latent space communication,” in *International Conference on Learning Representations*, 2023. \[Online\]. Available: <https://arxiv.org/abs/2209.15430>
- [19] V. Maiorca, L. Moschella, A. Norelli, M. Fumero, F. Locatello, and E. Rodolà, “Latent Space Translation via Semantic Alignment,” in *Advances in Neural Information Processing Systems*, 2023, pp. 55394–55414. \[Online\]. Available: <https://arxiv.org/abs/2311.00664>
- [20] Y. Shen, Y. Xiong, W. Xia, and S. Soatto, “Towards Backward-Compatible Representation Learning,” in *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 2020, pp. 6368–6377. \[Online\]. Available: <https://arxiv.org/abs/2003.11942>
- [21] V. Ramanujan, P. K. A. Vasu, A. Farhadi, O. Tuzel, and H. Pouransari, “Forward Compatible Training for Large-Scale Embedding Retrieval Systems,” in *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 2022, pp. 19386–19395. \[Online\]. Available: <https://arxiv.org/abs/2112.02805>
- [22] D. Goswami, L. Wang, B. Twardowski, and J. van de Weijer, “Query Drift Compensation: Enabling Compatibility in Continual Learning of Retrieval Embedding Models,” in *Proceedings of The 4th Conference on Lifelong Learning Agents*, in Proceedings of Machine Learning Research, vol. 330. 2026, pp. 324–340. \[Online\]. Available: <https://proceedings.mlr.press/v330/goswami26a.html>
- [23] A. Kusupati *et al.*, “Matryoshka Representation Learning,” in *Advances in Neural Information Processing Systems*, 2022, pp. 30233–30249. \[Online\]. Available: <https://arxiv.org/abs/2205.13147>
- [24] M. Mitchell *et al.*, “Model Cards for Model Reporting,” in *Proceedings of the Conference on Fairness, Accountability, and Transparency*, 2019, pp. 220–229. doi: [10.1145/3287560.3287596](https://doi.org/10.1145/3287560.3287596).
- [25] T. Gebru *et al.*, “Datasheets for Datasets,” *Communications of the ACM*, vol. 64, no. 12, pp. 86–92, 2021, doi: [10.1145/3458723](https://doi.org/10.1145/3458723).
- [26] Chrome Built-in AI Team, “Explainer: Built-in Semantic Embedder API.” \[Online\]. Available: <https://github.com/explainers-by-googlers/semantic-embedder-api>
- [27] Chrome Built-in AI Team, “Built-in Embedding API.” \[Online\]. Available: <https://github.com/webmachinelearning/proposals/issues/18>
- [28] J. X. Morris, V. Kuleshov, V. Shmatikov, and A. M. Rush, “Text Embeddings Reveal (Almost) As Much As Text,” in *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing*, 2023, pp. 12448–12460. doi: [10.18653/v1/2023.emnlp-main.765](https://doi.org/10.18653/v1/2023.emnlp-main.765).
- [29] D. Kim, D. Kang, K. Lee, H. Baek, and B. B. Kang, “Zero2Text: Zero-Training Cross-Domain Inversion Attacks on Textual Embeddings.” \[Online\]. Available: <https://arxiv.org/abs/2602.01757>
- [30] Cohere, “Multilingual Embeddings for Wikipedia in 300+ Languages.” \[Online\]. Available: <https://huggingface.co/datasets/CohereLabs/wikipedia-2023-11-embed-multilingual-v3>
- [31] N. Reimers and I. Gurevych, “Making Monolingual Sentence Embeddings Multilingual using Knowledge Distillation,” in *Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP)*, Association for Computational Linguistics, 2020, pp. 4512–4525.
- [32] X. Zhang *et al.*, “MIRACL: A Multilingual Retrieval Dataset Covering 18 Diverse Languages,” *Transactions of the Association for Computational Linguistics*, vol. 11, pp. 1114–1131, 2023, doi: [10.1162/tacl_a_00595](https://doi.org/10.1162/tacl_a_00595).
- [33] N. Kriegeskorte, M. Mur, and P. A. Bandettini, “Representational Similarity Analysis – Connecting the Branches of Systems Neuroscience,” *Frontiers in Systems Neuroscience*, vol. 2, p. 4, 2008, doi: [10.3389/neuro.06.004.2008](https://doi.org/10.3389/neuro.06.004.2008).
- [34] S. Kornblith, M. Norouzi, H. Lee, and G. Hinton, “Similarity of Neural Network Representations Revisited,” in *Proceedings of the 36th International Conference on Machine Learning*, in Proceedings of Machine Learning Research, vol. 97. 2019, pp. 3519–3529.

</div>

## Appendix A. Background in brief

This appendix is for readers who have not worked with embeddings.

**Embeddings.** An embedding model turns a text into a list of numbers, a vector with several hundred to a few thousand entries. It is trained so that texts of similar meaning get vectors that point in similar directions. The cosine of the angle between two vectors serves as the measure of similarity.

**Search.** To make a collection searchable, every passage is embedded once and the vectors are stored; this store is the index. A query is embedded with the same model, and the passages whose vectors are closest to it are returned. Nothing is compared word by word, which is why such a search finds a passage that answers a question in other words.

**Why models do not mix.** Each model arranges the texts in its own way. A single number in a vector means nothing by itself, and the same text gets unrelated vectors from two models. A query from one model compared with stored vectors of another returns nothing useful. Replacing the model therefore means embedding every passage again, which costs time and money and needs the texts.

**Translating instead.** If the two arrangements have nearly the same shape, one can be laid over the other ([Figure 4](#fig-intuition)). The map that does this is fitted on texts whose vectors are known in both spaces, the anchors. This paper proposes that providers publish such vectors for a fixed public list of texts, and it measures how well translated vectors work.

**How quality is measured.** For a set of queries with known relevant passages we look at the first ten results. nDCG@10 is high when the relevant passages are among them and near the top. Most results are given relative to embedding everything again with the new model, which counts as 100%.

**What to skip.** The proposal ([Section 3](#sec-proposal)) and the discussion ([Section 6](#sec-discussion)) can be read without the details of the experiments. A reader new to the field may skip the section on adapters and measures and [Appendix D](#app-methods).

## Appendix B. Example documents

The two listings show the machine-readable parts of the standard as they are published with the anchor release: the Embedding Space Card of one space, and the Adapter Manifest of an orthogonal map from that space into another. The map was fitted on the 20,000 German anchors; the saved weights reproduce both measurements in the manifest. In the second measurement the map translates queries, so the model whose index is searched is the target of the map and the re-embed reference is `native_source`.

**Listing 1.** Embedding Space Card of bge-m3, without the list of its anchor files.

**Listing 2.** Adapter Manifest of an orthogonal map from bge-m3 into mE5-large. The address of the weights is shortened.

## Appendix C. Models and prompts

[Table 11](#tab-models) lists the revision of the weights that were used for each model, its licence and the prompts its model card prescribes for documents and queries. All models were run through the sentence-transformers library on one Apple M3 Max. Retrieval is exact cosine search, every random choice uses the seed 20261120, and intervals come from 2,000 resamples of the queries. Every result number, table and figure in this paper is written by one script from the result files in the repository; nothing is copied by hand.

**Table 11.** Revisions, licences and prompts of the models. A text enters a model as prefix followed by the text; a dash means no prefix. The line break in the query prompt of Qwen3-0.6B is written as `\n`.

| **Space** | **Revision** | **Licence** | **Document prefix** | **Query prefix** |
|----|----|----|----|----|
| bge-m3 | `5617a9f6` | MIT | – | – |
| mE5-large | `3d7cfbda` | MIT | `passage: ` | `query: ` |
| arctic-l-v2 | `ac6544c8` | Apache-2.0 | – | `query: ` |
| Qwen3-0.6B | `97b0c614` | Apache-2.0 | – | `Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery:` |
| EmbGemma-2 | `f9972ac2` | Apache-2.0 | `title: none | text: ` | `task: search result | query: ` |
| MiniLM-L12 | `e8f8c211` | Apache-2.0 | – | – |

## Appendix D. Methods in detail

Three maps are fitted on $`k`$ anchor pairs, $`k \in \left\{ {100,300,1000,3000,5000,10000,20000} \right\}`$ as far as the anchor set reaches: orthogonal Procrustes after centring (semi-orthogonal where dimensions differ), affine ridge regression with the penalty chosen on held-out anchors, and a residual network with one hidden layer on top of the ridge solution, fitted at $`k = 3000`$ and, where available, $`k = 20000`$. The orthogonal map is $`W = UV^{\top}`$ from the thin singular value decomposition $`U\Sigma V^{\top}`$ of the cross-covariance of the centred anchor matrices; a vector $`x`$ is mapped to $`\left( {x - \mu_{s}} \right)W + \mu_{t}`$, with the two anchor means $`\mu_{s}`$ and $`\mu_{t}`$. Ridge regression is fitted on nine tenths of the $`k`$ pairs for each of five penalties, the penalty with the highest mean cosine on the remaining tenth is kept, and the map is refitted on all $`k`$ pairs. The residual network adds to the ridge output the output of one hidden layer of 2,048 units (GELU, dropout 0.1), trained with a cosine loss and AdamW and stopped early on a held-out tenth.

For query translation every map is fitted anew in the opposite direction on the same pairs; no map is inverted. In the main experiments all anchors are passages embedded in the document role, so a map applied to queries works on a kind of input it was not fitted on. To see whether that matters, we embedded the same anchor passages a second time with each model’s query prompt and fitted the maps for query translation on these vectors, on both sides of the pair; bge-m3 uses no prompts, so its vectors are the same in both roles. As a control for the centring we also fitted the orthogonal map on the uncentred anchor matrices.

The anchor sets are nested: every pair of spaces uses the same random order of anchors, and a budget of $`k`$ takes its first $`k`$. With fewer pairs than dimensions the orthogonal map is not determined by the data, which shows in the results for 100 and 300 pairs. All vectors are normalised to unit length before and after mapping. Retrieval is exact cosine search.

We report nDCG@10 (normalised discounted cumulative gain over the first ten results, which rewards relevant items more the higher they are ranked) and Recall@10 (the share of the relevant items that appear among the first ten) against the relevance judgements and, as a label-free measure, the share of the full re-embed’s top ten that the bridged system returns. A bridge is compared with staying on the old model per query: we resample the queries 2,000 times and call the difference in nDCG@10 a tie when its 95% interval includes zero.

The lexical retriever is BM25, the standard ranking function over word counts, with German stemming; hybrid runs fuse the top 1,000 of the two rankings by reciprocal rank fusion with the usual constant of 60 and equal weights. In a second variant the weight of the dense ranking is chosen from 0.2, 0.35, 0.5, 0.65 and 0.8 on one half of the queries and applied to the other half, in both directions. Differences between two configurations are given for the mean over all ordered pairs of open models: the nDCG@10 of each query is averaged over the pairs, the queries are resampled as above, and we report the difference in points of nDCG@10 (hundredths) with its 95% interval. The main results come from one random draw of anchors; for the orthogonal map with 1,000 and 5,000 pairs we repeated the fit with five further draws.

## Appendix E. Terms and abbreviations

In the running text, models and their spaces stand in a grey box (bge-m3), testbeds and abbreviations in small capitals (Wiki-de, CKA), and identifiers from code and documents in monospace (`space_id`). Abbreviations and the terms below are linked to their entry here; tables and figures name models and testbeds plainly.

### Terms

Embedding  
The vector that an embedding model writes for a text. Texts of similar meaning get vectors that lie close together.

Space  
The set of vectors that one encoder writes in one configuration. Only vectors of the same space can be compared.

Compatible spaces  
Spaces whose vectors the publisher guarantees to be directly comparable, without a map.

Embedding Space CardThe machine-readable description of a space: model and revision, dimensions, normalisation, and the prefix or task type of each role.

Role  
The way a text enters the encoder, typically as a document or as a query.

Prefix, task type  
A piece of text or a setting that a model adds to an input to mark its role.

Unit length  
A vector of length one. For such vectors the cosine is the dot product.

Passage  
The piece of a document that gets one vector.

Vector index  
The stored vectors of a collection, searched by comparing them with the vector of a query.

Dense retrieval  
Search by comparing vectors, here by exact cosine search.

Lexical retrieval  
Search by matching words, here with BM25.

Hybrid searchThe ranking of a dense index and the lexical ranking of BM25 are fused into one, here by reciprocal rank fusion.

Reciprocal rank fusionA way to fuse rankings: each ranking gives an item the score 1/(60 + rank), and the scores are added.

Anchor corpusA fixed, public, versioned list of passages. Its vectors in a space are the anchor embeddings of that space.

Anchor pair  
The two vectors of one anchor passage in two spaces. Maps are fitted on such pairs.

In-domain anchorsPairs made from passages of the collection that is to be searched, or on Wiki-de from the same source, held out from the search.

External anchorsPublic anchors from outside the searched collection: English Wikipedia on Wiki-de, German Wikipedia on the Archive.

Public anchors  
Pairs made from a public corpus, here Wikipedia, in place of the collection itself.

Map, adapter  
A function fitted on anchor pairs that carries vectors of a source space into a target space. It has one direction.

Orthogonal map  
A rotation, with a projection where the dimensions differ, computed in closed form from the anchor pairs. Between spaces of equal dimension it leaves every distance as it was.

Centring  
Subtracting the mean of the anchor vectors of the source space before mapping and adding the mean of the target space afterwards.

Ridge regression  
A least-squares map with a penalty on the size of its weights. It is free to change distances.

Residual network  
A small neural network that adds a correction to the output of the ridge map.

Fit quality  
The mean cosine between mapped vectors and the true vectors of the target space. It is not a retrieval measure.

Adapter ManifestThe record that travels with an adapter. It names the two spaces, the map and the anchors, and must contain a measured retrieval result.

Index translationThe stored document vectors are mapped once into the new space and searched with queries of the new model.

Query translationThe stored index stays as it is, and each query of the new model is mapped into the old space.

Bridge  
A system that serves through an adapter, in either mode.

Full re-embedDocuments and queries are embedded with the new model. Retrieval percentages in the paper are relative to this.

Stay  
Documents and queries remain in the space of the old model.

Mixed indexOne index that holds translated and re-embedded vectors side by side.

Relevance judgement  
The decision of a person that a passage, or a page, answers a query.

Known-item question  
A question written for one passage, which is its only relevant item.

Hard negative  
A passage that looks relevant to a query and is judged not to be.

Top-ten overlap  
The share of the re-embedded index’s ten best results that another index also returns.

Tie  
A difference in nDCG@10 whose 95% interval includes zero.

### Abbreviations and symbols

nDCG@10  
Normalised discounted cumulative gain over the first ten results. It rewards relevant results more the higher they are ranked; 1 is the best possible ranking.

Recall@10, R@10  
The share of the relevant items that appear among the first ten results.

BM25Best Matching 25, the standard ranking function over word counts.

CKACentred kernel alignment, a similarity of two sets of vectors that ignores rotation.

RSARepresentational similarity analysis, here the rank correlation of the pairwise cosines in two spaces.

XLM-RXLM-RoBERTa, the multilingual encoder on which three of the five open models are built.

MIRACLMultilingual Information Retrieval Across a Continuum of Languages, the benchmark behind the two Wikipedia testbeds.

APIApplication programming interface, here the service through which a provider’s model is called.

JSONJavaScript Object Notation, the format of cards and manifests.

DOIDigital object identifier.

W3CWorld Wide Web Consortium.

SD  
Standard deviation.

95% interval  
The range that holds the middle 95% of the values from 2,000 resamples of the queries.

$`k`$  
The number of anchor pairs a map is fitted on.

$`W`$, $`\mu_{s}`$, $`\mu_{t}`$  
The orthogonal map and the means of the anchor vectors in the source and the target space.

## Appendix F. Abstract in German

A translation of the abstract into German.

### Zusammenfassung

Ein Vektorindex ist an das Embedding-Modell gebunden, das ihn geschrieben hat: Vektoren zweier Modelle lassen sich nicht vergleichen, ein Modellwechsel bedeutet deshalb, jedes Dokument neu einzubetten. Abbildungen, die aus gepaarten Vektoren geschätzt werden, übersetzen zwischen manchen Räumen und scheitern bei anderen, und Betreiber können vorab nicht wissen, welcher Fall vorliegt, weil über einen Embedding-Raum nichts in vergleichbarer Form veröffentlicht wird. Wir schlagen einen minimalen Standard vor, der die Frage beantwortbar macht, ohne dass Anbieter ihre Modelle ändern müssen: eine *Embedding Space Card*, die festhält, was übereinstimmen muss, damit zwei Vektoren vergleichbar sind, ein öffentliches *Ankerkorpus*, dessen Embeddings jeder Anbieter zu jeder Modellversion veröffentlicht, und ein *Adapter Manifest*, das eine Abbildung zwischen zwei Räumen an ein gemessenes Suchergebnis bindet. Wir messen die Übersetzung auf zwei deutschen Wikipedia-Testbetten und einem privaten deutschen Archiv, zwischen fünf offenen Modellen und aus zwei kommerziellen Räumen. Mit einer orthogonalen Abbildung, geschätzt aus bis zu 20.000 Ankerpaaren aus der Sammlung, behält ein übersetzter Index im Mittel 95,7 %, 95,1 % und 88,0 % des nDCG@10 eines vollständig neu eingebetteten. Er ist fast immer schlechter als das beibehaltene alte Modell und nie jenseits des Rauschens der Anfragestichprobe besser, auch wenn das alte Modell viel schwächer ist: Ein übersetzter Index erbt die Grenzen des Modells, das ihn geschrieben hat. Ein Index, der übersetzte und neu eingebettete Vektoren mischt, ist schlechter als ein vollständig übersetzter. Anker in der Anfrage-Rolle helfen nicht; der Standard verlangt deshalb nur Anker in der Dokument-Rolle. Wikipedia-Anker statt Ankern aus dem Archiv selbst kosten dort 7,9 Prozentpunkte; dieser Abstand ist nicht mehr sichtbar, sobald der übersetzte Index bei abgestimmter Gewichtung mit BM25 fusioniert wird. Weder die Ähnlichkeit zweier Ankermatrizen noch die Trefferquote einer Abbildung auf zurückgehaltenen Ankern sagt die Größe des Verlusts voraus; das Manifest verlangt deshalb eine Messung. Übersetzen hält einen Index durchsuchbar, wenn sein Modell nicht mehr verfügbar ist. Es ersetzt das Neu-Einbetten nicht und ist kein Upgrade.

**Schlagwörter** Text-Embeddings · Vektorsuche · Modellwechsel · Interoperabilität · Retrieval · AI Engineering · künstliche Intelligenz
