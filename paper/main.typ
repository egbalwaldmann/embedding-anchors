#import "template.typ": paper, contents-list, figure-lists, appendix, cap, ruled, pullquote, described, mo, tb, gl, ab
#import "figures.typ": overview, space-id, decision, intuition, problem, documents, serving, design, funnel, shapes, direction, measures, fusion, available
#import "generated.typ": n, table-native, table-closed, table-hybrid, table-upgrade, table-mixed, table-models
#let v(key) = n.at(key)
#let sv(key) = n.at(key).replace("-", "−")
#let ci(key) = [#sv(key + ".diff") points (95% interval #sv(key + ".lo") to #sv(key + ".hi"))]

// Contents on the second page, the lists of figures, tables and listings on the third.
// Set to false for a venue that does not want them.
#let with-front-matter = true

// Line numbers in the margin, for a copy that goes to reviewers. Not for the public version.
#let with-line-numbers = false

#show: paper.with(
  title: "Publish the Anchors",
  subtitle: "A Minimal Interoperability Standard for Text Embedding Spaces, with a Cross-Vendor German Migration Study",
  short-title: "Publish the Anchors",
  authors: (
    (name: "Egbal Waldmann", email: "egbal@waldmann.dev", affiliation: "AI Engineer, Potsdam, Germany", orcid: "0000-0003-2958-5121"),
  ),
  note: "Preprint",
  date: "November 2026",
  date-of: datetime(year: 2026, month: 11, day: 23),
  abstract: [
    A vector index is tied to the embedding model that wrote it: vectors from two models cannot be compared, so a model change means embedding every document again. Maps fitted on paired vectors translate between some spaces and fail for others, and operators cannot tell in advance which case applies, because nothing about an embedding space is published in a comparable form. We propose a minimal standard that makes the question answerable without asking providers to change their models: an _Embedding Space Card_ that states what must be identical for two vectors to be comparable, a public _anchor corpus_ whose embeddings every provider publishes for every model version, and an _Adapter Manifest_ that ties a map between two spaces to a measured retrieval result. We measure translation on two German Wikipedia testbeds and a private German archive, between five open models and from two commercial spaces. With an orthogonal map fitted on up to 20,000 anchor pairs from the collection, a translated index keeps on average #v("wiki.top.procrustes.fwd.mean")%, #v("miracl.top.procrustes.fwd.mean")% and #v("archive.top.procrustes.fwd.mean")% of the nDCG\@10 of a #gl("full-re-embed")[full re-embed]. It is almost always worse than keeping the old model and never better beyond the noise of the query sample, even when the old model is much weaker: a translated index inherits the limits of the model that wrote it. An index that mixes translated and re-embedded vectors is worse than a fully translated one. Anchors in the query role do not help, so the standard asks for the document role only. Wikipedia anchors cost #v("archive.alt.loss.mean") percentage points on the archive, a gap no longer visible once the translated index is fused with #ab("bm25")[BM25] under a tuned weight. Neither the similarity of two anchor matrices nor the accuracy of a map on held-out anchors predicts the size of the loss, so the manifest requires a measurement. Translation keeps an index searchable when its model is gone. It is not a substitute for re-embedding and not an upgrade.
  ],
  keywords: ("text embeddings", "vector search", "model migration", "interoperability", "retrieval", "AI engineering", "artificial intelligence"),
  availability: [*Code and specification* #h(0.6em) #link("https://github.com/egbalwaldmann/embedding-anchors")[github.com/egbalwaldmann/embedding-anchors] \ *Anchor corpus* #h(0.6em) #link("https://huggingface.co/datasets/egbalwaldmann/embedding-anchors")[huggingface.co/datasets/egbalwaldmann/embedding-anchors] \ *Interactive figures* #h(0.6em) #link("https://anchors.egbalwaldmann.com")[anchors.egbalwaldmann.com] \ *DOI* #h(0.6em) #link("https://doi.org/10.5281/zenodo.24484736")[10.5281/zenodo.24484736]],
  lead: [A vector index dies with the model that wrote it. If every provider published the vectors of one small public collection of texts, anyone could carry an index to another model and measure what that costs. We tried it on German text: #v("archive.top.procrustes.fwd.mean")% to #v("wiki.top.procrustes.fwd.mean")% of the search quality of a full re-embed survives. That is enough to keep searching and never enough to beat the old model.],
)
#set cite(style: "ieee")
#set par.line(numbering: n => text(7pt, fill: luma(120))[#n]) if with-line-numbers
// Every formula of the paper with the words a screen reader says for it. The accessible export
// (--pdf-standard ua-1) stops at a formula that is missing here.
#show: described.with((
  ($k$, "k"), ($A$, "A"), ($B$, "B"), ($x$, "x"), ($W$, "W"), ($mu_s$, "mu s"), ($mu_t$, "mu t"),
  ($A -> B$, "A to B"), ($k = 3000$, "k equals 3000"), ($k = 20000$, "k equals 20000"),
  ($k in {100, 300, 1000, 3000, 5000, 10000, 20000}$, "k in 100, 300, 1000, 3000, 5000, 10000, 20000"),
  ($W = U V^top$, "W equals U times V transposed"), ($U Sigma V^top$, "U times Sigma times V transposed"),
  ($(x - mu_s) W + mu_t$, "x minus mu s, times W, plus mu t"),
))

#let de(key) = n.at(key).replace(".", ",")

#if with-front-matter {
  pagebreak(weak: true)
  contents-list()
  pagebreak(weak: true)
  figure-lists()
  pagebreak(weak: true)
}

= Introduction

Retrieval over embeddings is a standard building block of applications built on foundation models, above all of retrieval-augmented generation @huyen2025aiengineering. Dense retrieval stores one vector per passage and answers a query by comparing its vector with the stored ones. The comparison is only meaningful if both vectors come from the same model in the same configuration. Change the model, and the stored vectors become unusable: the new query vectors live in a different space (@fig-problem). The standard remedy is to embed the whole corpus again.

#figure(
  problem,
  caption: cap[What a change of model does to a stored index][What a change of model does to a stored index. As long as documents and queries are embedded by the same model, comparing vectors finds the passages that answer a query. A query from another model lives in a different space, and the comparison means nothing.],
) <fig-problem>

Providers say so plainly. Google documents that the spaces of `gemini-embedding-001` and its successor are incompatible and that all data must be re-embedded @google2026embeddings. Jina states that v3 vectors cannot search v2 vectors and the reverse @jina2024migration. The one shipped exception is narrow: Voyage 4 offers a shared space across the models of one generation of one vendor @voyage2026v4, and the vendor's migration guide treats embeddings from all other model pairs as not comparable @mongodb2026voyagemigrate.

The cost is not only compute. In the private document archive that motivates this paper (about 27,800 passages of German text), a change of embedding provider left the index effectively unsearchable until every passage had been embedded again; an index that held vectors of both models returned nothing useful. Two months later a spending limit stopped the embedding #ab("api")[API] altogether, and new documents could be stored but not made searchable. Both incidents have the same root: the index depends on one model that only its provider can run.

#pullquote[The index depends on one model that only its provider can run.]

Research offers a way out that is still unsettled. A map fitted on paired vectors can carry one space into another. For two upgrades, each between similar models, this recovers 95--99% of the recall of a #gl("full-re-embed")[full re-embed] @vejendla2025drift, and even unpaired translation is possible @jha2025vec2vec. Against this, simple maps work for some model pairs and fail sharply for others @hamideche2026simple, and a recent large study finds that adapter bridges, within and across families, almost always perform worse than staying with the old model, and that reuse of the old index defers the re-embed and does not avoid it @zhao2026bill.

For an operator, the practical problem is that the outcome cannot be known beforehand. Whether a map between space $A$ and space $B$ works is an empirical property of that pair and of the collection, and today the only way to find out is to embed a sample of one's own data with both models. An operator who still holds the texts can do half of this after the old model is gone: the stored vectors are the old model's side of the pairs, and embedding the same texts with a candidate model supplies the other side. We did so for the production index of the archive.

What cannot be recovered without the old model is everything that needs a new vector from it: a query in the old space, and with it the reference point of simply staying; pairs in the query role; and pairs for an index whose texts are not at hand. Nor can anything be said about a candidate model before a sample has been embedded with it, or about a map that somebody else has fitted on data that are not public.

Before the measurements reported here, several things were open. For German text, for stored vectors of commercial models and for a specialised collection, translation between embedding spaces had not been measured. It was not known whether a translated index can reach the old model it comes from, how many pairs a map needs, whether public anchors can stand in for pairs from the collection, or whether the outcome can be told in advance without a retrieval test. The experiments could have come out either way on each of these, and on two of them, the upgrade from a weak model and the forecast from anchors, the answer is negative.

This paper makes three contributions.

+ *A minimal standard* (@sec-proposal) that asks providers for one publication per model version: a machine-readable description of the space and the embeddings of a fixed public #gl("anchor-corpus")[anchor corpus]. With anchors published, anyone can fit a map between any two spaces from public data alone, compare candidate target spaces before embedding anything, and check a map that someone else has fitted; this includes spaces whose model is no longer served. The standard does not require models to be compatible; it makes compatibility measurable.
+ *A cross-vendor, German-language measurement* (@sec-experiments). Earlier migration studies use open models and English text. We measure translation between five open multilingual models from three architectural families and from two commercial spaces (Cohere `embed-multilingual-v3.0`, Google `gemini-embedding-001`) into open ones, on two German Wikipedia testbeds with human queries and on a private German archive. A much weaker old model serves as a further source, and we measure the state a running migration passes through, an index that holds translated and re-embedded vectors side by side.
+ *Evidence on the design of the #gl("anchor-corpus")[anchor corpus]*: how many anchors are needed, whether generic public anchors can stand in for in-domain pairs, whether anchors in another language transfer, whether anchors are needed in the query role, and how much of the loss a lexical retriever recovers in #gl("hybrid-search")[hybrid search].

The paper first places the proposal in the literature, then states it (@sec-proposal), describes the experiments (@sec-experiments) and their results, and ends with what follows for operators and for the standard (@sec-discussion). The terms and abbreviations of the paper are collected in @app-terms, which also explains how model names, testbeds and abbreviations are set; readers who have not worked with embeddings may start with @app-background, and a German abstract is in @app-german.

= Related Work

*Aligning embedding spaces.* Linear maps between independently trained word-embedding spaces were introduced for translation @mikolov2013exploiting, constrained to orthogonal maps @xing2015orthogonal and later learned without parallel data @conneau2018muse. For sentence embeddings, vec2vec learns translations without paired data @jha2025vec2vec, and mini-vec2vec reaches similar quality with a linear map at far lower cost @dar2025minivec2vec. Embedding-Converter trains a converter between models to avoid re-embedding @yoon2025converter. Maystre et al. prove that two sets of embeddings whose pairwise dot products approximately agree are approximately related by an orthogonal map, with a tight bound on the alignment error @maystre2025procrustes. Hamideche et al. test nine models and find that linear translators work for some pairs and fail for others @hamideche2026simple.

*Why alignment might be possible at all.* The Platonic Representation Hypothesis argues that representations of large models converge @huh2024platonic. A re-analysis finds that the global convergence largely disappears once similarity scores are calibrated against a permutation null that removes the effect of model width and depth, and that only local neighbourhood similarity retains significant agreement @groger2026aristotelian. Relative representations describe each item by its similarities to a fixed anchor set, which makes independently trained spaces comparable @moschella2023relative, and closed-form translations between encoders can be estimated from paired anchors @maiorca2023translation. Our proposal turns the anchor idea into a publication requirement.

*Compatibility by training.* Backward-compatible training makes a new model's features directly comparable with the old ones, which its authors report as achieved without sacrificing accuracy @shen2020bct, while later work finds that it can significantly hinder the new model @ramanujan2022fct. Forward-compatible training stores side information with each item to ease later transformation @ramanujan2022fct. Query drift compensation projects the queries of an updated model into the old space @goswami2025qdc. These methods need control over training and therefore work only within one provider; the shared space of the Voyage 4 models is a shipped case of compatibility within one provider @voyage2026v4. Matryoshka training gives compatibility across dimensions of one model, not across models @kusupati2022matryoshka.

*Migration adapters for vector databases.* Drift-Adapter maps new queries into the old index space with an orthogonal, low-rank or small residual network adapter fitted on a sample of re-embedded documents. It reports 95--99% of the recall of a #gl("full-re-embed")[full re-embed], measured against the new model's own nearest neighbours, for two upgrades between similar models (MiniLM to MPNet, which the author places in one architectural family, and CLIP ViT-B to ViT-L); for a change of architecture, from GloVe to MPNet, the same paper reports 59--72% @vejendla2025drift. Zhao et al. replay complete migrations for sixteen model pairs on a one-million-passage MS MARCO subsample and a code corpus, with scale replays on all 8.8 million passages for three pairs. Adapter bridges perform below the old model on every pair but one of the fifteen that are not an identity control, including pairs within a family; only the bridge between two language-model embedders of one family clears it, by a margin the authors consider too small to count as an improvement @zhao2026bill. Both studies use open models and, for text, English corpora; Drift-Adapter adds an image set and Zhao et al. a code corpus. Neither covers commercial spaces, other languages, or public versus #gl("in-domain-anchors")[in-domain anchors]. Zhao et al. include lexical candidates in some migration strategies, but do not study #gl("hybrid-search")[hybrid search] as a way to recover what a bridge loses.

*Standardisation.* Model cards @mitchell2019modelcards and datasheets for datasets @gebru2021datasheets established short structured documents that travel with a model or a dataset; the card proposed here is such a document for the one property they do not cover, the identity of the vector space. The Chrome team's Semantic Embedder #ab("api")[API] explainer proposes metadata with an embedding-space identifier so that developers know when to re-index, and asks whether a standard for embedding spaces is needed, comparable to codecs or language codes @chrome2026embedder. The same proposal has been submitted to the #ab("w3c")[W3C] Web Machine Learning Community Group and names the same identifier as part of the metadata @webml2026embedding. Observability conventions and benchmark metadata name the model but do not describe the space. We found no adapter format with a required measurement and no shared #gl("anchor-corpus")[anchor corpus].

*Security.* Text can be reconstructed from embeddings @morris2023vec2text, even without any training or leaked pairs of embeddings and text, given only query access to the target model @kim2026zero2text, and translation between spaces carries such attacks from one space to another @jha2025vec2vec. Published anchors lower the cost of exactly this translation; we return to the trade-off in @sec-discussion.

= Proposal: Cards, Anchors, Manifests <sec-proposal>

The proposal has three parts (@fig-overview). Each is useful alone; together they let an operator answer, before committing to a migration, whether an index can be carried into another space and at what loss. #ab("json")[JSON] Schemas are in the repository, and @app-examples shows a card and a manifest. @fig-documents sets out what the two documents hold.

#pullquote[The standard does not require models to be compatible. It makes compatibility measurable.]

#figure(
  overview,
  caption: cap[The three parts of the standard and the two uses of a map][The standard and what it is for. (a) Every provider embeds the same public #gl("anchor-corpus")[anchor corpus] and publishes the vectors with an #gl("embedding-space-card")[Embedding Space Card]; the two matrices are paired data, on which anyone can fit a map and record its measured result in an #gl("adapter-manifest")[Adapter Manifest]. (b) #gl("index-translation")[Index translation] maps the stored vectors once and searches them with native queries of the new model. (c) #gl("query-translation")[Query translation] leaves the index as it is and maps every query. Orange marks the space of the old model, blue that of the new one.],
) <fig-overview>

== Embedding Space Card

Two vectors are comparable if and only if they come from the same _space_. A space is narrower than a model name. The same model yields different spaces when the output is truncated to another dimension, when a different task type or prefix is used, or when the weights behind a stable model name change. The card states everything that defines the space:

- `space_id`: a stable identifier of the form `publisher/model@revision:variant` (@fig-space-id). Any change that makes old and new vectors incomparable requires a new identifier.
- model identity: publisher, name, pinned revision, optionally a hash of the weights;
- geometry: dimensions, native dimensions, how truncation was done and whether vectors were renormalised, similarity measure, whether vectors are unit length;
- input handling: per role the prefix or task type, the token limit and what happens beyond it. A card lists the roles whose vectors are meant to be compared with each other, typically document and query; a task type that is not meant to be searched against them, such as classification, is a different space with its own card;
- `compatible_with`: other spaces the publisher guarantees to be directly comparable, which covers compatibility by training;
- `anchors`: where the embeddings of public anchor corpora in this space can be downloaded.

#figure(
  space-id,
  caption: cap[The parts of a space identifier][The parts of a space identifier, here that of #mo[bge-m3] in the anchor release. Vectors with different identifiers are not comparable, unless the card of one space lists the other under `compatible_with`.],
) <fig-space-id>

A vector database that stores the `space_id` with each index can refuse to mix spaces. That alone would have turned the silent failure described in the introduction into an error message.

== Anchor corpus

An #gl("anchor-corpus")[anchor corpus] is a fixed, public, versioned list of text passages with a checksum. The requirement the standard places on a provider is this: _for every model version, publish the card and the embeddings of the anchor corpus_ in the document role. For a provider this costs one batch job per release. For everyone else it creates paired data between any two spaces that were ever published, without access to either model: the pairs for spaces $A$ and $B$ are simply the two published matrices, row by row (@fig-intuition).

#figure(
  intuition,
  caption: cap[Why a map can translate between two spaces][The same anchor texts as points in two spaces, drawn in two dimensions. Each model arranges the texts in its own way. Where the two arrangements have nearly the same shape, a turn and a shift fitted on the anchors lay one over the other and carry every other vector along. This works only approximately: the translated vector of a document lands near the vector the new model would write, not on it.],
) <fig-intuition>

#pullquote[For a provider this costs one batch job per release.]

This has three consequences. Maps can be fitted by third parties, published and checked by anyone. A space remains translatable after its model is retired, even for an index whose texts are no longer at hand, because the anchors outlive the #ab("api")[API]. And compatibility can be roughly estimated before any text is embedded or any map is fitted, from the two anchor matrices alone, for example by comparing their pairwise similarity structure (@sec-predict).

The requirement covers one role. A provider may publish the anchors in further roles of the card, but in our experiments anchors embedded in the query role did not improve the translation of queries (@sec-experiments), and a standard that wants to be adopted should not ask for more than it can justify.

Published anchors do not replace an operator's own pairs. Where the texts and a new model are at hand, the operator can make pairs from the collection itself, which are the better basis (@sec-experiments); public anchors are the common yardstick and the fallback. How large the corpus must be, and whether one generic corpus serves specialised domains and several languages, are empirical questions. Our experiments address them for German. One provider has in effect already published anchors: Cohere released its embeddings of the full Wikipedia in many languages @cohere2023wikipedia. Our public anchors are drawn from that release, so one commercial space is covered from the start.

== Adapter Manifest

An adapter is a map from a source space to a target space. The manifest records the two `space_id`s, the type of map, a checksum of its weights, the #gl("anchor-corpus")[anchor corpus] and number of pairs it was fitted on, and at least one _measurement_: a named benchmark, the mode of use, and the retrieval metric for the system served through the adapter next to the same metric after a #gl("full-re-embed")[full re-embed] and, where available, when staying on the old model. An adapter without a measurement is not conformant. This is deliberate. The literature shows that maps between some pairs do not work, and a format that lets them circulate without numbers would spread failures.

#pullquote[An adapter without a measurement is not conformant.]

#figure(
  documents,
  caption: cap[What the card and the manifest hold][The two documents of the standard with their fields, named as in the #ab("json")[JSON] Schemas. A card describes one space. A manifest names two cards, the map between them, the anchors it was fitted on and at least one measured result. Which native value is the reference of a #gl("full-re-embed")[full re-embed] depends on the mode (@fig-direction).],
) <fig-documents>

The manifest distinguishes two modes. In _index translation_ the stored document vectors are mapped once into the new space and searched with native queries of the new model. In _query translation_ the old index stays and each query of the new model is mapped into the old space. The first changes the index, the second adds a step to every query. With an orthogonal map the two modes are nearly the same computation: the map of one direction is the transpose of the other and a rotation leaves cosines unchanged, so the modes differ only through the centring of the two spaces and, where the dimensions differ, through the projection; how much that matters is an empirical question. Maps with more freedom have no such symmetry. A map has one direction: the manifest names the space it reads and the space it writes, and each measurement names the mode it was taken in (@fig-direction). We call a system that serves through an adapter, in either mode, a _bridge_.

#figure(
  direction,
  caption: cap[The direction of a map and the mode it serves in][The direction of a map against the mode it serves in. For #gl("index-translation")[index translation] the map carries the old space into the new one. For #gl("query-translation")[query translation] it runs the other way, and the old model is its target. In both cases the native value of the space the queries come from is the reference of a #gl("full-re-embed")[full re-embed], and the other one is staying on the old model.],
) <fig-direction>

= Experiments <sec-experiments>

== Questions

+ Between open models of different families, how much retrieval quality survives #gl("index-translation")[index translation] and #gl("query-translation")[query translation], compared with a #gl("full-re-embed")[full re-embed] and with staying on the old model?
+ How well do stored vectors of two commercial spaces translate into open spaces?
+ How many anchor pairs are needed?
+ Can public anchors (Wikipedia) replace in-domain pairs, and do anchors in another language transfer?
+ Does the similarity structure of two anchor matrices predict whether a map will work?
+ How much of the loss does #gl("hybrid-search")[hybrid search] with a lexical retriever recover?
+ Do anchors embedded in the query role improve the translation of queries?
+ Does a bridge pay off as an upgrade from a much weaker old model?
+ What happens in an index that holds translated and re-embedded vectors side by side?

== Spaces

#figure(
  ruled(
    columns: 4, align: (left, left, left, right),
    header: ([Space], [Model], [Architecture], [Dim.]),
    [bge-m3], [`BAAI/bge-m3`], [XLM-R encoder], [1,024],
    [mE5-large], [`intfloat/multilingual-e5-large`], [XLM-R encoder], [1,024],
    [arctic-l-v2], [`Snowflake/snowflake-arctic-embed-l-v2.0`], [XLM-R encoder], [1,024],
    [Qwen3-0.6B], [`Qwen/Qwen3-Embedding-0.6B`], [decoder language model], [1,024],
    [EmbGemma-2], [`google/embeddinggemma-2`], [Gemma encoder], [768],
    table.hline(stroke: 0.4pt),
    [Cohere v3], [`embed-multilingual-v3.0`], [not published], [1,024],
    [Gemini-001], [`gemini-embedding-001`], [not published], [1,536],
    table.hline(stroke: 0.4pt),
    [MiniLM-L12], [`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`], [MiniLM encoder], [384],
  ),
  caption: cap[The embedding spaces of the study][The embedding spaces of the study. The five open models at the top are the target of every translation and, between themselves, also its source. The two commercial spaces enter as sources through stored document vectors, #mo[Cohere v3] on #tb[Wiki-de] and #mo[Gemini-001] on the #tb[Archive]. #mo[MiniLM-L12] is the deliberately weak old model of @sec-upgrade. Revisions and prompts are in @app-models.],
) <tab-spaces>

Five open multilingual models run locally (@tab-spaces): #mo[bge-m3] (`BAAI/bge-m3`), #mo[mE5-large] (`intfloat/multilingual-e5-large`) and #mo[arctic-l-v2] (`Snowflake/snowflake-arctic-embed-l-v2.0`), which are #ab("xlm-r")[XLM-R] encoders, the third built on the pretrained encoder of the first; #mo[Qwen3-0.6B] (`Qwen/Qwen3-Embedding-0.6B`, a decoder language model); and #mo[EmbGemma-2] (`google/embeddinggemma-2`, a Gemma encoder with 768 dimensions). Two commercial spaces enter through stored document vectors only (@fig-available): Cohere `embed-multilingual-v3.0` (from the public Wikipedia release @cohere2023wikipedia; the released vectors have 1,024 dimensions and, as we found, unit length) and Google `gemini-embedding-001`, the model of the archive's production index, truncated by the #ab("api")[API] to 1,536 dimensions and used without a task type. Each model is used with the query and document prompts its model card prescribes. As a deliberately weak old model we add #mo[MiniLM-L12] (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; 384 dimensions, input cut at 128 tokens) @reimers2020multilingual. It serves only as the source of a translation and is not part of any mean over the open models.

#figure(
  available,
  caption: cap[Which vectors were at hand for which space][Which vectors were at hand for each space. For the two commercial spaces there are no query vectors and therefore no reference for staying. For #mo[Gemini-001] there are no vectors of the public Wikipedia anchors either, which is what a provider publishing anchors would supply.],
) <fig-available>

== Testbeds

#figure(
  ruled(
    columns: 6, align: (left, right, right, left, right, left),
    header: ([Testbed], [Passages], [Queries], [Relevance], [In-domain anchors], [External anchors]),
    [Wiki-de], [#v("wiki.corpus")], [#v("wiki.queries")], [judged page], [20,000], [English Wikipedia],
    [MIRACL-de], [#v("miracl.corpus")], [#v("miracl.queries")], [judged passage], [#v("miracl.anchors.in-domain")], [--],
    [Archive], [#v("archive.corpus")], [#v("archive.queries")], [one known passage], [#v("archive.anchors.in-domain")], [German Wikipedia],
  ),
  caption: cap[The three testbeds][The three testbeds. Queries are human-written on the two Wikipedia testbeds and generated on the #tb[Archive]. On #tb[Wiki-de] any passage of a page judged relevant counts. The external anchor sets and the #gl("in-domain-anchors")[in-domain anchors] of #tb[Wiki-de] hold 20,000 passages each; no anchor passage is part of a searched corpus.],
) <tab-testbeds>

#figure(
  image("fig/testbeds.svg", width: 100%, alt: "Bar chart, one row per testbed: the searched passages split into background and judged passages, with the number of queries and what counts as relevant; on the right the anchor sets, which are never searched."),
  caption: cap[The three testbeds drawn to scale][The three testbeds drawn to scale: the passages that are searched, with the part that carries judgements, and the anchor sets beside them, which are never searched.],
) <fig-testbeds>

@fig-testbeds draws the three testbeds to scale.

*#tb[Wiki-de].* German Wikipedia passages from the Cohere release, which makes one commercial space available with public vectors: 100,000 passages from one shard as background, plus all passages of the pages that #tb[MIRACL-de] @zhang2023miracl judges relevant for its 305 development queries, #v("wiki.corpus") passages from #v("wiki.groups") pages in total. #v("wiki.queries") queries have at least one relevant page in the corpus. According to the dataset card of the #ab("miracl")[MIRACL] corpus, passage identifiers have the form `X#Y`, where all passages with the same `X` come from one article; we found `X` to be the Wikipedia page identifier, which is stable across dumps and also appears in the identifiers of the Cohere release, so relevance transfers at page level; rankings are collapsed to pages before scoring. This testbed is easy by construction: about a quarter of its passages belong to relevant pages, the background is unrelated to the queries, and any passage of a relevant page counts as a hit. Anchors: the first 20,000 German passages of a different shard (in-domain; consecutive passages of 3,387 pages) and 20,000 English passages (cross-lingual). No anchor passage occurs in the corpus.

*#tb[MIRACL-de].* The German part of #ab("miracl")[MIRACL] with its original judgements at passage level @zhang2023miracl: all 3,103 passages that carry a judgement (3,144 judgements, 811 of them positive), plus 100,000 passages drawn uniformly from the rest of the German #ab("miracl")[MIRACL] corpus, #v("miracl.corpus") passages in total, and the same #v("miracl.queries") development queries as in #tb[Wiki-de], here with their judgements at passage level. The judged passages were candidates that an ensemble of retrieval systems had ranked at the top for the query, so every query meets hard negatives, and only a passage judged relevant counts. Anchors: #v("miracl.anchors.in-domain") further passages from the same uniform draw. This testbed has no commercial space.

*#tb[Archive].* A private archive of German documents, split into passages of up to 1,500 characters and embedded in production with `gemini-embedding-001`. Of the 27,809 passages in the index, 26,905 remain after removing passages without a stored vector, very short passages and exact duplicates. The archive holds many documents in several copies. Passages whose production vectors have a cosine above 0.97 are treated as near-duplicates, grouped by single linkage, and all but one of each group removed, which takes out another 5,395 passages and leaves 21,510 from 4,932 documents (@fig-funnel). Whole documents are held out as #gl("in-domain-anchors")[in-domain anchors] (#v("archive.anchors.in-domain") passages), so that no anchor shares a document with the #v("archive.corpus") passages that are searched; the German Wikipedia anchors of #tb[Wiki-de] serve as public anchors.

#figure(
  funnel(v("archive.anchors.in-domain"), v("archive.corpus"), v("archive.queries")),
  caption: cap[How the #tb[Archive] testbed was cut from the production index][How the #tb[Archive] testbed was cut from the production index: passages without a vector, very short passages and copies are removed, whole documents are held out as anchors, and the rest is searched.],
) <fig-funnel>

The #v("archive.queries") queries are known-item questions: for one sampled passage from each of #v("archive.queries") documents, a language model running locally (Gemma 4, 12B) wrote one German question that the passage answers, and that passage is the query's only relevant item. Such questions are easier than real user queries, they reward lexical overlap with the passage they were written from, and the model that wrote them belongs to the same family as one of the embedders (#mo[EmbGemma-2]). Only aggregate numbers from this testbed are reported; no text from it is released.

*Input length.* The open models read Wikipedia passages up to 512 tokens, which cuts at most #v("wiki.tokens.max-truncated")% of the passages on #tb[Wiki-de] and #v("miracl.tokens.max-truncated")% on #tb[MIRACL-de]. #tb[Archive] passages are longer in tokens; there each model reads up to its own limit, capped at 2,048 tokens. Only #mo[mE5-large], with a limit of #v("archive.tokens.me5-large.limit") tokens, cuts a noticeable share (#v("archive.tokens.me5-large.truncated")% of the passages).

*Reference points.* A _full re-embed_ embeds documents and queries with the new model. _Stay_ keeps documents and queries in the old model's space. For the two commercial spaces only stored document vectors were available, so the stay reference exists for the open models only. @fig-serving sets the ways of serving side by side.

#figure(
  serving,
  caption: cap[Ways to serve a collection, and who wrote what][Ways to serve a collection, by which model wrote the stored vectors and the query. Colour marks the space in which the two are compared: orange the old model's, blue the new one's. The #gl("mixed-index")[mixed index] is the subject of @sec-mixed, lexical search and its fusion with a dense ranking that of @sec-hybrid.],
) <fig-serving>

== Adapters and measures

Three maps are fitted on $k$ anchor pairs, with $k$ from 100 to 20,000 as far as the anchor set reaches: an orthogonal map after centring, affine ridge regression, and a small residual network on top of the ridge solution. For #gl("query-translation")[query translation] every map is fitted anew in the opposite direction. All anchors are passages embedded in the document role. Two controls repeat the fit, one on the same passages embedded with each model's query prompt and one on uncentred matrices. Vectors have unit length before and after mapping, and retrieval is exact cosine search. @fig-shapes shows in a drawing what sets a rotation apart from a least-squares map and what centring does.

#figure(
  shapes,
  caption: cap[What three kinds of map do to the shape of a space][What distinguishes the maps, as a drawing in two dimensions and not a measurement. A rotation keeps the shape of the source space; fitted without centring it keeps the shape and misses the place. A least-squares map such as ridge regression may land closer on average and still bend the shape, so that neighbours change. The drawing leaves out that all vectors are scaled back to unit length.],
) <fig-shapes>

@fig-real-spaces shows the orthogonal map on real vectors: sixty anchors that the map was not fitted on, in the space of #mo[bge-m3] and in that of #mo[mE5-large], where each translated vector lands close to the vector the new model writes for the same passage.

#figure(
  image("fig/real-spaces.svg", width: 100%, alt: "Two scatter plots of the first two principal components. Left: sixty anchors in the space of bge-m3. Right: the same anchors in the space of mE5-large, each translated vector joined by a line to the vector that mE5-large writes for the same passage."),
  caption: cap[Real vectors before and after the orthogonal map][Sixty Wikipedia anchors held out from the fit, in two real spaces: as #mo[bge-m3] places them (left) and, in the space of #mo[mE5-large], as #mo[mE5-large] places them and as the orthogonal map fitted on 19,000 other anchors places them (right). Each space is projected onto its own first two principal components, which hold little of the variance, so the picture shows the arrangement, not the distances. Four anchors are numbered in both panels.],
) <fig-real-spaces>

We report nDCG\@10 (normalised discounted cumulative gain over the first ten results, which rewards relevant items more the higher they are ranked) and Recall\@10 (the share of the relevant items that appear among the first ten) against the relevance judgements and, as a label-free measure, the share of the #gl("full-re-embed")[full re-embed]'s top ten that the bridged system returns. A bridge is compared with staying on the old model per query: the queries are resampled 2,000 times, and a difference in nDCG\@10 whose 95% interval includes zero is called a tie (@fig-tie). Differences in nDCG\@10 are given in points (hundredths), differences between relative values in percentage points. The lexical retriever is #ab("bm25")[BM25], the standard ranking function over word counts. Hybrid runs fuse its ranking with the dense one by #gl("reciprocal-rank-fusion")[reciprocal rank fusion], with equal weights or with a weight tuned on the other half of the queries. @app-methods gives the maps, the fusion and the statistics in full.

To test whether the outcome can be predicted from published anchors alone, we compute three similarity measures between the two anchor matrices of a pair of spaces, on 2,000 anchors: the Spearman correlation of their pairwise cosine similarities (representational similarity analysis, #ab("rsa")[RSA] @kriegeskorte2008rsa), linear centred kernel alignment (#ab("cka")[CKA] @kornblith2019cka), and the mean overlap of each anchor's ten nearest anchors in the two spaces. All three are invariant to rotation and need no map (@fig-measures). @fig-design counts the combinations of pair, mode, map and anchor budget measured for the open models.

#figure(
  measures,
  caption: cap[What the three similarity measures compare][What the three similarity measures compare, as a drawing. None of them needs a map, and all three give the same value when one of the spaces is turned.],
) <fig-measures>

#figure(
  image("fig/tie.svg", width: 100%, alt: "Three columns, one per pair of spaces on Wiki-de. Top: the difference per query between the translated index and the old model, most of them zero. Bottom: the distribution of the mean difference over 2,000 resampled query sets with its 95% interval; the first two intervals lie below zero, the third includes zero."),
  caption: cap[What a tie is][How a translated index is compared with the old model, for three pairs of spaces on #tb[Wiki-de]. Top: the difference in nDCG\@10 per query; most queries are unaffected. Bottom: the mean difference over 2,000 query sets drawn with replacement, and the interval that holds the middle 95% of them. An interval below zero means below the old model, one that includes zero is a tie.],
) <fig-tie>

#figure(
  design(v("wiki.beats-stay.of"), v("miracl.beats-stay.of"), v("archive.beats-stay.of"), v("all.beats-stay.of")),
  caption: cap[The measured combinations, testbed by testbed][The measured combinations of the pairs of open models, testbed by testbed. These #v("all.beats-stay.of") combinations are the basis of the comparison with the old model in @sec-open.],
) <fig-design>

= Results

@fig-glance gathers the main results before the sections below take them apart.

#figure(
  image("fig/glance.svg", width: 100%, alt: "Dot plot with one row per setting and one marker per testbed, nDCG at 10 in per cent of a full re-embed with the range over the pairs: index and query translation between 85 and 96 per cent, with 1,000 anchors lower, a mixed index and the weak MiniLM-L12 far lower."),
  caption: cap[The results at a glance][The results at a glance: nDCG\@10 in per cent of a #gl("full-re-embed")[full re-embed], mean and range over the pairs of spaces, orthogonal map. The top two rows use all #gl("in-domain-anchors")[in-domain anchors]; each row below changes one thing against the first. A testbed is missing where the setting was not measured on it.],
) <fig-glance>

== Reference points

#figure(
  table-native,
  caption: cap[Retrieval quality of each space after a #gl("full-re-embed")[full re-embed], and of #ab("bm25")[BM25]][Retrieval quality of each open space after a #gl("full-re-embed")[full re-embed], and of #ab("bm25")[BM25]. For an old model these numbers are also the _stay_ reference.],
) <tab-native>

#figure(
  image("fig/native.svg", width: 100%, alt: "Dot plot per testbed: nDCG at 10 and Recall at 10 of five open models, of the weak old model and of BM25."),
  caption: cap[Reference points: the open models, the weak old model and #ab("bm25")[BM25]][The reference points of @tab-native at a glance: nDCG\@10 (filled) and Recall\@10 (open) of each open model after a #gl("full-re-embed")[full re-embed], of the weak old model #mo[MiniLM-L12] (@sec-upgrade) and of #ab("bm25")[BM25].],
) <fig-native>

@tab-native gives the reference points and @fig-native shows them side by side. On #tb[Wiki-de] the five open models lie within #v("wiki.native.spread") points of nDCG\@10 of each other and close to the ceiling, well above #ab("bm25")[BM25]. #tb[MIRACL-de] is harder and separates the models: they spread over #v("miracl.native.spread") points, between #v("miracl.native.min") and #v("miracl.native.max"). On the #tb[Archive] the models spread over #v("archive.native.spread") points and #ab("bm25")[BM25] lies among them, which is plausible for questions written from the passage they are meant to find.

Two re-embedded indexes do not return the same passages even without translation. The top tens of two different open models share on average #v("wiki.native-overlap")% of their passages on #tb[Wiki-de], #v("miracl.native-overlap")% on #tb[MIRACL-de] and #v("archive.native-overlap")% on the #tb[Archive]. The overlap figures below have to be read against this.

== Translation between open models <sec-open>

#figure(
  image("fig/curves.svg", width: 100%, alt: "Line chart per testbed: retrieval quality relative to a full re-embed rises with the number of anchor pairs and flattens after a few thousand; ridge regression falls behind for query translation."),
  caption: cap[Retrieval quality of translation against the number of anchor pairs][Retrieval quality of a translated index (solid) and of translated queries (dashed), relative to a #gl("full-re-embed")[full re-embed], against the number of anchor pairs. Means over all ordered pairs of open models, #gl("in-domain-anchors")[in-domain anchors]; open markers: residual network. Grey lines: the individual pairs for orthogonal #gl("index-translation")[index translation]. The unlabelled tick is 5,000. The vertical line marks 1,024 pairs, the dimension of most of the spaces, below which an orthogonal map is fitted on fewer pairs than it has directions. Dotted: staying on the old model, which averages close to 100%, since every model is source and target equally often.],
) <fig-curves>

#figure(
  image("fig/matrix-wiki-de.svg", width: 100%, alt: "Two heat maps for Wiki-de with one cell per pair of source and target space, index translation and query translation; values between 90 and 100 per cent."),
  caption: cap[#tb[Wiki-de]: translation between every pair of spaces][#tb[Wiki-de]: nDCG\@10 in per cent of a #gl("full-re-embed")[full re-embed] for every pair of spaces, orthogonal map, #v("wiki.kmax") #gl("in-domain-anchors")[in-domain anchors]. Empty cells are a space paired with itself; the colour scale is the same in @fig-matrix-wiki, @fig-matrix-miracl and @fig-matrix-archive. An asterisk marks a bridge whose nDCG\@10 is at least that of the old model; the row of the commercial space has no such reference.],
) <fig-matrix-wiki>

#figure(
  image("fig/matrix-miracl-de.svg", width: 100%, alt: "Two heat maps for MIRACL-de with one cell per pair of source and target space; values between 83 and 100 per cent."),
  caption: cap[#tb[MIRACL-de]: translation between every pair of spaces][#tb[MIRACL-de]: as @fig-matrix-wiki, with #v("miracl.kmax") #gl("in-domain-anchors")[in-domain anchors].],
) <fig-matrix-miracl>

#figure(
  image("fig/matrix-archive.svg", width: 100%, alt: "Two heat maps for the Archive with one cell per pair of source and target space; values between 63 and 98 per cent."),
  caption: cap[#tb[Archive]: translation between every pair of spaces][#tb[Archive]: as @fig-matrix-wiki, with #v("archive.kmax") #gl("in-domain-anchors")[in-domain anchors].],
) <fig-matrix-archive>

#figure(
  image("fig/stay.svg", width: 100%, alt: "Interval plot with one row per ordered pair of open models and one panel per testbed: the difference between the translated index and the old model is below zero or tied with zero for every pair."),
  caption: cap[A translated index against the old model's own index, pair by pair][#gl("index-translation")[Index translation] against staying on the old model, for every ordered pair of open models: the difference in nDCG\@10 with its 95% interval from resampling the queries. Orthogonal map, all #gl("in-domain-anchors")[in-domain anchors]. A filled marker is below the old model beyond the uncertainty of the query sample, an open marker is a tie.],
) <fig-stay>

#figure(
  ruled(
    columns: 8, align: (left, right, right, right, right, right, right, right),
    header: ([Testbed], [Index], [Range], [Queries], [R\@10], [Family], [Across], [Against re-embed]),
    [#box[Wiki-de]], [#v("wiki.top.procrustes.fwd.mean")], [#v("wiki.top.procrustes.fwd.min")--#v("wiki.top.procrustes.fwd.max")], [#v("wiki.top.procrustes.bwd.mean")], [#v("wiki.top.procrustes.fwd.r10")], [#v("wiki.main.fwd.within.mean")], [#v("wiki.main.fwd.cross.mean")], [#box[#sv("wiki.x.c.bridge-vs-native.diff") [#sv("wiki.x.c.bridge-vs-native.lo"), #sv("wiki.x.c.bridge-vs-native.hi")]]],
    [#box[MIRACL-de]], [#v("miracl.top.procrustes.fwd.mean")], [#v("miracl.top.procrustes.fwd.min")--#v("miracl.top.procrustes.fwd.max")], [#v("miracl.top.procrustes.bwd.mean")], [#v("miracl.top.procrustes.fwd.r10")], [#v("miracl.main.fwd.within.mean")], [#v("miracl.main.fwd.cross.mean")], [#box[#sv("miracl.x.c.bridge-vs-native.diff") [#sv("miracl.x.c.bridge-vs-native.lo"), #sv("miracl.x.c.bridge-vs-native.hi")]]],
    [#box[Archive]], [#v("archive.top.procrustes.fwd.mean")], [#v("archive.top.procrustes.fwd.min")--#v("archive.top.procrustes.fwd.max")], [#v("archive.top.procrustes.bwd.mean")], [#v("archive.top.procrustes.fwd.r10")], [#v("archive.main.fwd.within.mean")], [#v("archive.main.fwd.cross.mean")], [#box[#sv("archive.x.c.bridge-vs-native.diff") [#sv("archive.x.c.bridge-vs-native.lo"), #sv("archive.x.c.bridge-vs-native.hi")]]],
  ),
  caption: cap[Translation between the open models in numbers][Translation between the open models with the orthogonal map and all #gl("in-domain-anchors")[in-domain anchors], means over the ordered pairs. nDCG\@10 in per cent of a #gl("full-re-embed")[full re-embed] for #gl("index-translation")[index translation], its range over the pairs, and for #gl("query-translation")[query translation]; Recall\@10 of #gl("index-translation")[index translation] in per cent of a #gl("full-re-embed")[full re-embed] (R\@10); #gl("index-translation")[index translation] between the three #ab("xlm-r")[XLM-R] encoders (family) and across families; and the difference between the translated and the re-embedded index in points of nDCG\@10 with its 95% interval in brackets.],
) <tab-open>

#figure(
  image("fig/depth.svg", width: 100%, alt: "Line chart per testbed: nDCG at 10, Recall at 10 and Recall at 100 in per cent of a full re-embed for index and query translation; the values rise towards 100 per cent from left to right."),
  caption: cap[Reordered rather than lost: three depths of the result list][#gl("index-translation")[Index translation] (filled) and #gl("query-translation")[query translation] (open) at three depths of the result list, in per cent of a #gl("full-re-embed")[full re-embed]: nDCG\@10, Recall\@10 and Recall\@100. Means and range over the ordered pairs of open models, orthogonal map, all #gl("in-domain-anchors")[in-domain anchors].],
) <fig-depth>

*A translated index is usable.* With the orthogonal map and all #gl("in-domain-anchors")[in-domain anchors], #gl("index-translation")[index translation] keeps on average #v("wiki.top.procrustes.fwd.mean")%, #v("miracl.top.procrustes.fwd.mean")% and #v("archive.top.procrustes.fwd.mean")% of the nDCG\@10 of a #gl("full-re-embed")[full re-embed] on #tb[Wiki-de], #tb[MIRACL-de] and the #tb[Archive], and #gl("query-translation")[query translation] one to three percentage points less (@tab-open, @fig-curves). The pairs differ, most of all on the #tb[Archive], where the weakest keeps #v("archive.top.procrustes.fwd.min")% (@fig-matrix-wiki, @fig-matrix-miracl, @fig-matrix-archive). Recall\@10 survives better than nDCG\@10, since a small change of the vectors more often reorders the top ten than it removes a relevant passage from them, and Recall\@100 survives almost entirely (@fig-depth): what translation loses is mostly order, not passages. The family of the two models matters: between the three #ab("xlm-r")[XLM-R] encoders several points more survive than across families. On every testbed the translated index is below the re-embedded one beyond the uncertainty of the query sample.

*A translated index is not better than the old model.* For the best configuration, the orthogonal map with all #gl("in-domain-anchors")[in-domain anchors], #gl("index-translation")[index translation] is below the old model's nDCG\@10 beyond the uncertainty of the query sample in #v("wiki.main.fwd.below") of #v("wiki.main.fwd.n") pairs on #tb[Wiki-de], #v("miracl.main.fwd.below") of #v("miracl.main.fwd.n") on #tb[MIRACL-de] and #v("archive.main.fwd.below") of #v("archive.main.fwd.n") on the #tb[Archive], and tied with it in the others (@fig-stay).

#pullquote[Of #v("all.beats-stay.of") measured combinations, none beat the old model beyond the noise.]

The picture is the same over everything we measured. Of the #v("all.beats-stay.of") combinations of testbed, pair, mode, map, anchor set and anchor budget, which are not independent of each other, #v("all.beats-stay.ndcg") reach the nDCG\@10 of the old model: none of the #v("wiki.beats-stay.of") on #tb[Wiki-de], #v("miracl.beats-stay.ndcg") of the #v("miracl.beats-stay.of") on #tb[MIRACL-de] and none of the #v("archive.beats-stay.of") on the #tb[Archive]. The #v("miracl.beats-stay.ndcg") are index translations from #mo[bge-m3] into the two other #ab("xlm-r")[XLM-R] encoders, which are stronger than #mo[bge-m3] there, and they exceed the old model by at most #v("miracl.beats-stay.ndcg-max") points, far inside the uncertainty. In no combination is a bridge better than the old model beyond that uncertainty; it is worse beyond it in #v("wiki.beats-stay.below"), #v("miracl.beats-stay.below") and #v("archive.beats-stay.below") combinations on the three testbeds and tied in the remaining #v("wiki.beats-stay.tie"), #v("miracl.beats-stay.tie") and #v("archive.beats-stay.tie").

Recall\@10, for which we computed no intervals, is slightly more lenient: there a bridge exceeds the old model in #v("wiki.beats-stay.r10") combinations on #tb[Wiki-de], #v("miracl.beats-stay.r10") on #tb[MIRACL-de] and #v("archive.beats-stay.r10") on the #tb[Archive], by at most #v("wiki.beats-stay.r10-max") points. Where a bridge between open models scores above the #gl("full-re-embed")[full re-embed], the old model is the stronger of the two. For German text and five open models from three architectural families this agrees with Zhao et al., who find bridges below the old model on all but one of their pairs and a margin too small to count as an improvement on that one @zhao2026bill.

*Agreement with the new model's own neighbours says little about retrieval quality.* The translated index returns on average #v("wiki.top.procrustes.fwd.overlap")% (#tb[Wiki-de]), #v("miracl.top.procrustes.fwd.overlap")% (#tb[MIRACL-de]) and #v("archive.top.procrustes.fwd.overlap")% (#tb[Archive]) of the ten passages that the re-embedded index returns. That is about as much as two independently embedded indexes share, and on the two Wikipedia testbeds slightly less (@fig-overlap). A bridged index finds relevant passages nearly as often as the new model, but to a considerable extent different ones, as any other model would. Results measured against a model's own neighbours and results measured against relevance judgements are therefore not comparable.

#pullquote[A translated index finds relevant passages nearly as often as the new model, but to a considerable extent different ones.]

#figure(
  image("fig/overlap.svg", width: 100%, alt: "Scatter plot per testbed: translated indexes and the old models' own indexes share a similar part of the re-embedded index's top ten; the old indexes lie near 100 per cent, the translated ones below."),
  caption: cap[Agreement with the re-embedded index against retrieval quality][Share of the re-embedded index's top ten that another index returns, against the nDCG\@10 of that index relative to the re-embed. One point per ordered pair of open models. Blue: the old model's index translated into the new space (orthogonal map, all #gl("in-domain-anchors")[in-domain anchors]) and searched with the new model's queries. Orange: the old model's own index with its own queries.],
) <fig-overlap>

#figure(
  image("fig/fidelity.svg", width: 100%, alt: "Scatter plot per testbed: ridge regression reproduces query vectors with a higher cosine than the orthogonal map but retrieves worse."),
  caption: cap[Fit quality against retrieval quality of translated queries][How faithfully a map reproduces query vectors against how well the translated queries retrieve: the mean cosine between mapped and true query vectors and the nDCG\@10 relative to a #gl("full-re-embed")[full re-embed], for #gl("query-translation")[query translation] with all #gl("in-domain-anchors")[in-domain anchors]. A grey line joins the two maps of one ordered pair of open models.],
) <fig-fidelity>

#figure(
  image("fig/fit-order.svg", width: 100%, alt: "Two scatter plots for Wiki-de, cosine to the true vector against the share of the ten nearest neighbours kept. Left: held-out anchors, both maps around 60 per cent. Right: queries searched among 20,000 passages, ridge regression further right and lower than the orthogonal map."),
  caption: cap[Landing close is not keeping the order][How close a map lands and how much of the order it keeps, on #tb[Wiki-de]: the mean cosine between mapped and true vectors against the share of the ten nearest neighbours under the true vectors that are also among the ten nearest under the mapped ones. Left: 2,000 held-out anchors, maps fitted on 5,000 others. Right: the queries, searched among 20,000 passages. One point per ordered pair of open models and map; a grey line joins the two maps of one pair.],
) <fig-fit-order>

*The orthogonal map is the robust choice.* Ridge regression is better with few anchors: at 300 pairs it keeps #v("wiki.in-domain.ridge.fwd.300.mean")% on #tb[Wiki-de] against #v("wiki.in-domain.procrustes.fwd.300.mean")% for the orthogonal map. From 3,000 pairs onwards the orthogonal map is as good or better for #gl("index-translation")[index translation], and it is far better for #gl("query-translation")[query translation], where ridge falls to #v("wiki.top.ridge.bwd.mean")% on #tb[Wiki-de], #v("miracl.top.ridge.bwd.mean")% on #tb[MIRACL-de] and #v("archive.top.ridge.bwd.mean")% on the #tb[Archive]. The two modes of the orthogonal map differ on average by #v("wiki.modes.gap.mean"), #v("miracl.modes.gap.mean") and #v("archive.modes.gap.mean") points on the three testbeds, as little as its symmetry leads one to expect. The difference is small but it is not noise: averaged over the pairs, #gl("index-translation")[index translation] is ahead of #gl("query-translation")[query translation] by #ci("wiki.x.c.index-vs-query-translation"), #ci("miracl.x.c.index-vs-query-translation") and #ci("archive.x.c.index-vs-query-translation"). Single pairs differ more, by up to #v("archive.modes.gap.max") points on the #tb[Archive] (#v("archive.modes.gap.max-pair")), so the centring is not always harmless.

Fit quality does not explain the failure of ridge. Measured by the mean cosine between mapped and true vectors, ridge is on average the more faithful map: on #tb[Wiki-de] it reproduces passages it was not fitted on with a mean cosine of #v("wiki.fidelity.ridge.docs-bwd") against #v("wiki.fidelity.procrustes.docs-bwd") for the orthogonal map, and queries with #v("wiki.fidelity.ridge.queries-bwd") against #v("wiki.fidelity.procrustes.queries-bwd"). It nevertheless ranks worse (@fig-fidelity). @fig-fit-order shows the same on #tb[Wiki-de] for all twenty ordered pairs, measured as the share of the ten nearest neighbours that survive the map: among held-out anchors the two maps keep about the same share, among the passages that queries are searched in, the orthogonal map keeps more, although ridge lands closer. A least-squares map is free to change the distances between vectors, and a higher average cosine does not mean that neighbours keep their order; an orthogonal map between spaces of equal dimension leaves every distance of the source space as it was. How well a map fits is therefore no evidence of how well it retrieves, which is a further reason for the manifest to demand a retrieval measurement. The residual network on top of ridge repairs part of the damage and reaches the orthogonal map for #gl("index-translation")[index translation] (#v("wiki.top.mlp.fwd.mean")% at #v("wiki.top.mlp.k") pairs on #tb[Wiki-de]), but not for #gl("query-translation")[query translation] (#v("wiki.top.mlp.bwd.mean")%).

#pullquote[How well a map fits is no evidence of how well it retrieves.]

*How many anchors.* On #tb[Wiki-de] the curve flattens early: the orthogonal map reaches #v("wiki.in-domain.procrustes.fwd.1000.mean")% with 1,000 pairs, #v("wiki.in-domain.procrustes.fwd.5000.mean")% with 5,000 and #v("wiki.in-domain.procrustes.fwd.20000.mean")% with 20,000. On #tb[MIRACL-de] the same steps give #v("miracl.in-domain.procrustes.fwd.1000.mean")%, #v("miracl.in-domain.procrustes.fwd.5000.mean")% and #v("miracl.in-domain.procrustes.fwd.20000.mean")%. On the #tb[Archive] the curve is flatter at the start and still rising at the end of the anchor set, with #v("archive.in-domain.procrustes.fwd.1000.mean")% at 1,000 pairs, #v("archive.in-domain.procrustes.fwd.5000.mean")% at 5,000 and #v("archive.in-domain.procrustes.fwd.10000.mean")% at 10,000. A few thousand pairs carry most of what the orthogonal map delivers; how much that is depends on the collection. Below 1,000 pairs the result depends strongly on the pair.

#figure(
  ruled(
    columns: 7, align: (left, right, right, right, right, right, right),
    header: ([Testbed], [Uncentred], [Worse], [Role, orthogonal], [Role, ridge], [SD 1k], [SD 5k]),
    [#box[Wiki-de]], [#v("wiki.x.uncentred.fwd.mean")], [#v("wiki.x.uncentred.fwd.worse") of #v("wiki.x.uncentred.fwd.n")], [#box[#sv("wiki.x.c.query-role-vs-document-role.procrustes.diff") [#sv("wiki.x.c.query-role-vs-document-role.procrustes.lo"), #sv("wiki.x.c.query-role-vs-document-role.procrustes.hi")]]], [#box[#sv("wiki.x.c.query-role-vs-document-role.ridge.diff") [#sv("wiki.x.c.query-role-vs-document-role.ridge.lo"), #sv("wiki.x.c.query-role-vs-document-role.ridge.hi")]]], [#v("wiki.x.seed.1000.fwd.sd")], [#v("wiki.x.seed.5000.fwd.sd")],
    [#box[MIRACL-de]], [#v("miracl.x.uncentred.fwd.mean")], [#v("miracl.x.uncentred.fwd.worse") of #v("miracl.x.uncentred.fwd.n")], [#box[#sv("miracl.x.c.query-role-vs-document-role.procrustes.diff") [#sv("miracl.x.c.query-role-vs-document-role.procrustes.lo"), #sv("miracl.x.c.query-role-vs-document-role.procrustes.hi")]]], [#box[#sv("miracl.x.c.query-role-vs-document-role.ridge.diff") [#sv("miracl.x.c.query-role-vs-document-role.ridge.lo"), #sv("miracl.x.c.query-role-vs-document-role.ridge.hi")]]], [#v("miracl.x.seed.1000.fwd.sd")], [#v("miracl.x.seed.5000.fwd.sd")],
    [#box[Archive]], [#v("archive.x.uncentred.fwd.mean")], [#v("archive.x.uncentred.fwd.worse") of #v("archive.x.uncentred.fwd.n")], [#box[#sv("archive.x.c.query-role-vs-document-role.procrustes.diff") [#sv("archive.x.c.query-role-vs-document-role.procrustes.lo"), #sv("archive.x.c.query-role-vs-document-role.procrustes.hi")]]], [#box[#sv("archive.x.c.query-role-vs-document-role.ridge.diff") [#sv("archive.x.c.query-role-vs-document-role.ridge.lo"), #sv("archive.x.c.query-role-vs-document-role.ridge.hi")]]], [#v("archive.x.seed.1000.fwd.sd")], [#v("archive.x.seed.5000.fwd.sd")],
  ),
  caption: cap[Three controls: centring, role of the anchors, draw of the anchors][Three controls. Centring: nDCG\@10 of orthogonal #gl("index-translation")[index translation] without centring in per cent of a #gl("full-re-embed")[full re-embed] (with centring: @tab-open), and the number of ordered pairs that lose more than a point without it. Role: change of #gl("query-translation")[query translation] in points of nDCG\@10 when the maps are fitted on anchors in the query role instead of the document role, with its 95% interval in brackets. Draw: standard deviation, in percentage points, of the mean over the pairs across five further random draws of 1,000 and of 5,000 anchors.],
) <tab-controls>

*The draw of the anchors hardly matters.* Over five further random draws, the mean over the pairs for #gl("index-translation")[index translation] has a standard deviation of at most half a percentage point, with 1,000 anchors as with 5,000 (@tab-controls). A single pair varies more, by up to #v("archive.x.seed.1000.fwd.pair-sd.max") points on the #tb[Archive] with 1,000 anchors. The means reported here are stable; a difference of a point or two between two single pairs is not.

#figure(
  image("fig/controls.svg", width: 100%, alt: "Six scatter plots against a diagonal. Top row: without centring single pairs fall far below the diagonal. Bottom row: anchors in the query role leave the orthogonal map on the diagonal and move ridge regression below it."),
  caption: cap[Two controls: centring and the role of the anchors][Two controls, one point per ordered pair of open models, nDCG\@10 in per cent of a #gl("full-re-embed")[full re-embed] with all #gl("in-domain-anchors")[in-domain anchors]. Top: orthogonal #gl("index-translation")[index translation] fitted without centring against the same map with centring; the pair that loses most is named. Bottom: #gl("query-translation")[query translation] with maps fitted on anchors in the query role against anchors in the document role. A point on the diagonal is unchanged.],
) <fig-controls>

#figure(
  image("fig/offset.svg", width: 100%, alt: "Dot plot, one row per space: the length of the mean anchor vector lies between 0.29 and 0.83, and the mean cosine of two anchors between about 0.1 and 0.7."),
  caption: cap[How far the vectors of each space lie from the origin][How far the vectors of each space lie off the origin, on the 20,000 German anchors of #tb[Wiki-de]: the length of their mean vector, where every vector has length 1, and the mean cosine between two anchors. Zero would mean vectors spread evenly around the origin. Centring removes this offset before the map is fitted.],
) <fig-offset>

*Centring carries the orthogonal map.* Fitted on the uncentred anchor matrices, the same map is clearly worse on every testbed (@tab-controls; @fig-controls, top), and single pairs collapse: #v("archive.x.uncentred.fwd.min-pair") falls from #v("archive.x.uncentred.fwd.min-centred")% to #v("archive.x.uncentred.fwd.min")% on the #tb[Archive]. The vectors of an embedding model do not lie around the origin, the offset differs from model to model, and a rotation cannot move it (@fig-offset). Without centring, the two modes returned the same result for every pair of spaces with equal dimensions, as the symmetry of the map requires, so the difference between the modes reported above comes from the centring and from the projection between dimensions. An adapter manifest that says "orthogonal" therefore has to say whether and on what the map was centred.

*Anchors in the query role do not help* (@fig-controls, bottom). With maps fitted on the same anchor passages embedded with the query prompts, orthogonal #gl("query-translation")[query translation] hardly changes: nothing beyond the noise on the two Wikipedia testbeds and a small loss on the #tb[Archive] (@tab-controls). Single pairs move in both directions, between #sv("archive.x.role.procrustes.gain.min") and #sv("archive.x.role.procrustes.gain.max") percentage points on the #tb[Archive]. Ridge regression, whose weakness on queries one might have blamed on the role of its anchors, gets worse with anchors in the query role on every testbed. These anchors are passages embedded as queries. Whether texts that look like queries would serve better is a different question, which a corpus of passages cannot answer; what the result does show is that the document role is a sufficient basis for the orthogonal map in both modes.

== A much weaker old model <sec-upgrade>

#figure(
  table-upgrade,
  caption: cap[A much weaker old model: staying, translating and re-embedding][#mo[MiniLM-L12] as the old model: nDCG\@10 when staying on it, of its index translated into the five open spaces and of the open models' queries translated into its space (means over the five open models, all #gl("in-domain-anchors")[in-domain anchors]; in brackets the share of staying), and the mean of the five open models after a #gl("full-re-embed")[full re-embed].],
) <tab-upgrade>

The five open models are of similar strength, so the comparison above cannot say whether a bridge pays off as an upgrade. If the new model is far better than the old one, an index that keeps most of the new model's quality might beat staying. #mo[MiniLM-L12] is such an old model: its own nDCG\@10 is #v("wiki.x.minilm-l12.native.rel")% of the mean of the five open models on #tb[Wiki-de], #v("miracl.x.minilm-l12.native.rel")% on #tb[MIRACL-de] and #v("archive.x.minilm-l12.native.rel")% on the #tb[Archive], where its limit of 128 tokens covers only the beginning of a long passage (@tab-upgrade, @fig-upgrade).

#figure(
  image("fig/upgrade.svg", width: 100%, alt: "Line chart per testbed: the translated index of the weak old model stays below that model's own retrieval quality at every number of anchor pairs, far below a full re-embed."),
  caption: cap[A much weaker old model, by number of anchor pairs][#mo[MiniLM-L12] as the old model: nDCG\@10 of its translated index and of translated queries against its own index, means over the five open models, against the number of in-domain anchor pairs. Horizontal lines: the mean of the five open models after a #gl("full-re-embed")[full re-embed], #mo[MiniLM-L12] kept as it is, and #ab("bm25")[BM25].],
) <fig-upgrade>

Translation does not lift #mo[MiniLM-L12]'s index above its own level (@fig-upgrade). With the orthogonal map and all #gl("in-domain-anchors")[in-domain anchors], the translated index reaches between #v("wiki.x.minilm-l12.in-domain.procrustes.fwd.vs-stay")% and #v("archive.x.minilm-l12.in-domain.procrustes.fwd.vs-stay")% of what #mo[MiniLM-L12] delivers when it is simply kept, and translated queries against the old index less (@tab-upgrade). Ridge regression does better than the orthogonal map for #gl("index-translation")[index translation] here and comes level with staying on the #tb[Archive]. That is of no practical use there: #ab("bm25")[BM25] alone reaches #v("archive.bm25.ndcg") on the #tb[Archive], and fusing it with equal weights with so weak a dense ranking, translated (#v("archive.x.minilm-l12.hy.fused")) or not (#v("archive.x.minilm-l12.hy.stay-fused")), pulls #ab("bm25")[BM25] down. Of the #v("all.x.upgrade.of") combinations of testbed, target, mode, map, anchor set and anchor budget, none is better than staying beyond the uncertainty of the query sample; #v("all.x.upgrade.reach") reach the old model's nDCG\@10, all of them on the #tb[Archive] with at least 3,000 #gl("in-domain-anchors")[in-domain anchors], and #v("all.x.upgrade.below") are worse beyond the uncertainty. Measured against the new model, the translated index keeps only #v("wiki.x.minilm-l12.in-domain.procrustes.fwd.mean")%, #v("miracl.x.minilm-l12.in-domain.procrustes.fwd.mean")% and #v("archive.x.minilm-l12.in-domain.procrustes.fwd.mean")% of a #gl("full-re-embed")[full re-embed].

The percentages of @sec-open therefore describe pairs of comparable models, not a property of translation. A map rearranges the information that the stored vectors hold and adds none: what the old model did not separate stays unseparated in the new space. The quality of a translated index is bounded by the old model, whichever space it is translated into (@fig-ceiling).

#figure(
  image("fig/ceiling.svg", width: 100%, alt: "Three scatter plots against a diagonal, one per testbed: the nDCG at 10 of the old model kept as it is against that of its translated index; nearly all points lie on or below the diagonal, for the open models and for MiniLM-L12."),
  caption: cap[The old model is the ceiling][The old model is the ceiling: nDCG\@10 of the old model kept as it is against that of its index translated into a new space, one point per ordered pair; orthogonal map, all #gl("in-domain-anchors")[in-domain anchors]. Above the diagonal the translated index would be better than staying. Points close to it lie within the uncertainty of the query sample (@fig-stay).],
) <fig-ceiling>

#pullquote[A map rearranges the information that the stored vectors hold and adds none.]

== A partly migrated index <sec-mixed>

#figure(
  table-mixed,
  caption: cap[An index with translated and re-embedded vectors side by side][One index with translated and re-embedded vectors side by side: nDCG\@10 in per cent of a #gl("full-re-embed")[full re-embed] by the share of translated passages, means over the ordered pairs of open models (orthogonal map, all #gl("in-domain-anchors")[in-domain anchors]; a translated share of 100% is the fully translated index), and the share of translated passages in the top ten when half of the index is translated.],
) <tab-mixed>

A migration that replaces vectors in place passes through a state in which translated and re-embedded vectors share one index. We built such indexes by taking a random 10, 50 or 90% of the passages from the translated index and the rest from the re-embedded index of the target model, and searched them with the target model's queries (@tab-mixed, @fig-mixed).

#figure(
  image("fig/mixed.svg", width: 100%, alt: "Line charts per testbed. Top: retrieval quality falls as the translated share of the index grows to 90 per cent and recovers at 100 per cent. Bottom: translated passages are under-represented in the top ten."),
  caption: cap[A partly migrated index, pair by pair][An index that holds translated and re-embedded vectors side by side. Top: nDCG\@10 in per cent of a #gl("full-re-embed")[full re-embed] by the translated share of the index; a share of 0% is the re-embedded index, 100% the fully translated one. Bottom: the share of translated passages among the top ten. Orthogonal map, all #gl("in-domain-anchors")[in-domain anchors].],
) <fig-mixed>

A #gl("mixed-index")[mixed index] is worse than its composition suggests (@fig-mixed). With nine tenths of the passages translated it keeps #v("wiki.x.mixed.90.mean")%, #v("miracl.x.mixed.90.mean")% and #v("archive.x.mixed.90.mean")% of a #gl("full-re-embed")[full re-embed], less than the fully translated index on every testbed (@tab-mixed), and the weakest pair on the #tb[Archive] falls to #v("archive.x.mixed.90.min")%. On #tb[MIRACL-de] and the #tb[Archive] the index with half of its passages translated is already below the fully translated one. The result lists show why. In the half-translated index, translated passages fill only between #v("wiki.x.mixed.50.translated")% and #v("archive.x.mixed.50.translated")% of the top ten, not half of it. A translated vector has a cosine of about 0.8 with the vector the new model writes for the same passage, so its similarity to a native query is damped (@fig-damping), and a native passage is ranked ahead of a translated one whether or not it is the more relevant. In a fully translated index every passage carries the same handicap and the order survives. Re-embedding a translated index in place thus makes retrieval worse before it makes it better.

#pullquote[Re-embedding a translated index in place makes retrieval worse before it makes it better.]

#figure(
  image("fig/damping.svg", width: 100%, alt: "Histograms for two pairs on Wiki-de of the cosine between a query and its relevant passages. The translated vectors lie clearly to the left of the new model's own vectors, many of them below the best passage that is not relevant."),
  caption: cap[Why native vectors push translated ones aside][Why native passages push translated ones down, for two pairs of spaces on #tb[Wiki-de]: the cosine between a query of the new model and its relevant passages, as the new model embeds them (grey) and translated from the old space (blue). Top: every relevant passage. Bottom: the best relevant passage of each query, against the best passage that is not relevant, embedded by the new model (orange; here not the old model's space). In a #gl("mixed-index")[mixed index] a translated relevant passage often loses to a native passage that is not relevant.],
) <fig-damping>

== From commercial into open spaces <sec-closed>

#figure(
  table-closed,
  caption: cap[Translation from the two commercial spaces into the open ones][Translation from the two commercial spaces, of which only stored document vectors were available, into the open spaces: nDCG\@10 in per cent of a #gl("full-re-embed")[full re-embed] for index and #gl("query-translation")[query translation] with the orthogonal map and #gl("in-domain-anchors")[in-domain anchors], and the share of the re-embed's top ten that #gl("index-translation")[index translation] returns. #mo[Cohere v3] on #tb[Wiki-de], #mo[Gemini-001] on the #tb[Archive].],
) <tab-closed>

Stored vectors of the two commercial spaces can be translated into the open spaces as well, those of Cohere better than the average open pair and those of Gemini somewhat worse (@tab-closed, @fig-closed).

#figure(
  image("fig/closed.svg", width: 100%, alt: "Line chart for Cohere v3 on Wiki-de and Gemini-001 on the Archive: translation into five open spaces by number of anchor pairs, against the range of the open pairs."),
  caption: cap[Translation from the two commercial spaces, by number of anchor pairs][Translation from the two commercial spaces into the five open ones against the number of in-domain anchor pairs, orthogonal map. Grey: mean and range of #gl("index-translation")[index translation] between the ordered pairs of open models on the same testbed.],
) <fig-closed> The public Cohere vectors reach #v("wiki.cohere-v3.in-domain.procrustes.fwd.20000.mean")% of a #gl("full-re-embed")[full re-embed] on average over the five open targets (#v("wiki.cohere-v3.in-domain.procrustes.fwd.20000.min")--#v("wiki.cohere-v3.in-domain.procrustes.fwd.20000.max")%), and #v("wiki.cohere-v3.in-domain.procrustes.fwd.1000.mean")% with 1,000 anchors. That is above the average open pair, and one reason is visible in the anchors: the Cohere space is close to that of #mo[mE5-large], with a #ab("cka")[CKA] of #v("wiki.sim.cohere-v3.me5-large.cka"), the highest of any pair on this testbed (@fig-similarity). The archive's production index, `gemini-embedding-001` at 1,536 dimensions, translates at #v("archive.gemini-001.in-domain.procrustes.fwd.10000.mean")% for #gl("index-translation")[index translation] (#v("archive.gemini-001.in-domain.procrustes.fwd.10000.min")--#v("archive.gemini-001.in-domain.procrustes.fwd.10000.max")%) and #v("archive.gemini-001.in-domain.procrustes.bwd.10000.mean")% for #gl("query-translation")[query translation], below the mean of the open pairs on the same testbed and inside their range. For neither space could we compute the stay reference, so these numbers say what a translated index delivers, not whether it is worth giving up the old model.

== Which anchors <sec-anchors>

#figure(
  image("fig/anchor-source.svg", width: 100%, alt: "Line chart for Wiki-de and the Archive: in-domain anchors against English or German Wikipedia anchors by number of anchor pairs; the curves coincide on Wiki-de and separate on the Archive."),
  caption: cap[#gl("in-domain-anchors")[In-domain anchors] against anchors from another language or domain][#gl("in-domain-anchors")[In-domain anchors] against #gl("external-anchors")[external anchors], orthogonal map, ordered pairs of open models. Left: #tb[Wiki-de], German against English Wikipedia anchors. Right: the #tb[Archive], anchors from the archive against German Wikipedia anchors; the in-domain set ends at #v("archive.kmax") pairs.],
) <fig-anchor-source>

*Anchors in another language cost little, anchors from another domain cost more* (@fig-anchor-source). For German Wikipedia retrieval, 20,000 English Wikipedia anchors give #v("wiki.english.procrustes.fwd.20000.mean")% against #v("wiki.in-domain.procrustes.fwd.20000.mean")% with German ones; the weakest pair falls from #v("wiki.in-domain.procrustes.fwd.20000.min")% to #v("wiki.english.procrustes.fwd.20000.min")%. For the #tb[Archive], 10,000 Wikipedia anchors give #v("archive.wikipedia.procrustes.fwd.10000.mean")% against #v("archive.in-domain.procrustes.fwd.10000.mean")% with 10,000 passages from the archive itself, and the weakest pair falls from #v("archive.in-domain.procrustes.fwd.10000.min")% to #v("archive.wikipedia.procrustes.fwd.10000.min")%; with 20,000 Wikipedia anchors the mean rises to #v("archive.wikipedia.procrustes.fwd.20000.mean")%. Pair by pair, the Wikipedia anchors cost #v("archive.alt.loss.mean") percentage points of a #gl("full-re-embed")[full re-embed] on average and up to #v("archive.alt.loss.max") at equal size. In nDCG\@10 itself and averaged over the pairs, the #gl("in-domain-anchors")[in-domain anchors] are ahead by #ci("archive.x.c.in-domain-vs-other-anchors") on the #tb[Archive] and the German ones by #ci("wiki.x.c.in-domain-vs-other-anchors") on #tb[Wiki-de]. A generic public corpus is thus clearly the weaker basis on a specialised collection, and size recovers only a small part of the difference. The two comparisons come from different testbeds and do not separate language from domain in a controlled way. For the Gemini index the comparison could not be made at all, because no vectors of the Wikipedia anchors exist in that space; this is the gap that published anchors would close.

== What the anchors predict <sec-predict>

#figure(
  image("fig/similarity.svg", width: 100%, alt: "Three triangular heat maps, one per testbed, with the similarity of every pair of spaces: linear CKA above the diagonal, neighbour overlap below."),
  caption: cap[Similarity of the anchor matrices of every pair of spaces][Similarity of the anchor matrices of every pair of spaces, computed on 2,000 #gl("in-domain-anchors")[in-domain anchors] without fitting a map: linear #ab("cka")[CKA] above the diagonal, the mean overlap of the ten nearest anchors below it. Darker is more similar; each measure has its own scale, shared by the three panels.],
) <fig-similarity>

#figure(
  image("fig/predict.svg", width: 100%, alt: "Four scatter plots against retrieval quality after translation, one marker shape per testbed: three similarity measures, where the testbeds form separate clouds, and the accuracy on held-out anchors, which stands at 100 per cent for both Wikipedia testbeds."),
  caption: cap[Similarity of two spaces against the outcome of translation][Similarity of two spaces, computed from 2,000 anchors without fitting a map, against the retrieval quality of orthogonal #gl("index-translation")[index translation] between them, and, bottom right, how often a mapped held-out anchor is nearest to its own counterpart (map fitted on 5,000 anchors). One point per ordered pair of spaces.],
) <fig-predict>

@fig-similarity shows two of the three measures for every pair of spaces. On the two Wikipedia testbeds the three #ab("xlm-r")[XLM-R] encoders share more of their neighbours with each other than with the other two open models; on the #tb[Archive] this grouping is not visible. Within one testbed, the similarity of two anchor matrices correlates with the outcome of translation (@fig-predict). The rank correlation between nearest-neighbour overlap and relative nDCG\@10 is #v("wiki.predict.knn.fwd") on #tb[Wiki-de] (#v("wiki.predict.n") ordered pairs), #v("miracl.predict.knn.fwd") on #tb[MIRACL-de] (#v("miracl.predict.n")) and #v("archive.predict.knn.fwd") on the #tb[Archive] (#v("archive.predict.n")); for #ab("rsa")[RSA] it is #v("wiki.predict.rsa.fwd"), #v("miracl.predict.rsa.fwd") and #v("archive.predict.rsa.fwd"), for #ab("cka")[CKA] #v("wiki.predict.cka.fwd"), #v("miracl.predict.cka.fwd") and #v("archive.predict.cka.fwd"). The numbers of pairs are small and the ordered pairs are not independent, since both directions of a pair share one similarity value, so these are descriptions, not tests.

On the #tb[Archive] the #gl("in-domain-anchors")[in-domain anchors] are private. Similarities computed from the public Wikipedia anchors instead correlate with the same outcomes at #v("archive.predict-public.knn") (nearest neighbours), #v("archive.predict-public.rsa") (#ab("rsa")[RSA]) and #v("archive.predict-public.cka") (#ab("cka")[CKA]) over the #v("archive.predict-public.n") ordered pairs of open models. Across testbeds the measures do not transfer: the same similarity value goes with a loss of a few per cent on #tb[Wiki-de] and of more than a tenth on the #tb[Archive].

The correlations are also carried in part by differences between source spaces. An operator has one source and wants to choose a target; within one source space, over its four possible targets, the rank correlation averages between #v("wiki.predict-source.cka") for #ab("cka")[CKA] and #v("wiki.predict-source.rsa") for #ab("rsa")[RSA] on #tb[Wiki-de], between #v("miracl.predict-source.cka") and #v("miracl.predict-source.rsa") on #tb[MIRACL-de] and between #v("archive.predict-source.cka") and #v("archive.predict-source.rsa") on the #tb[Archive], with neighbour overlap in between each time. @fig-choice shows what that means for the choice: ranked by neighbour overlap and ranked by the outcome, the four targets of a source often come out in a different order. Similarity read off published anchors is therefore a first indication of which spaces are close, and a weak guide to the choice of a target. It cannot tell how much will be lost on the operator's own queries; that needs a measurement, which is why the manifest requires one.

A fourth candidate needs a map but no queries: fit the orthogonal map on 5,000 anchors and count how often a mapped anchor, out of 2,000 held out, is nearest to its own counterpart. On the anchors of the two Wikipedia testbeds this accuracy is saturated (@fig-predict, bottom right). It lies between #v("wiki.x.retrieval.in-domain.min") and #v("wiki.x.retrieval.in-domain.max")% for the pairs of #tb[Wiki-de] and between #v("miracl.x.retrieval.in-domain.min") and #v("miracl.x.retrieval.in-domain.max")% for those of #tb[MIRACL-de], although the retrieval outcomes of these pairs differ by more than ten points, and its rank correlation with the outcome is #sv("wiki.x.retrieval.in-domain.rho") and #sv("miracl.x.retrieval.in-domain.rho"). On the #gl("in-domain-anchors")[in-domain anchors] of the #tb[Archive] it spreads from #v("archive.x.retrieval.in-domain.min") to #v("archive.x.retrieval.in-domain.max")% and correlates with the outcome at #sv("archive.x.retrieval.in-domain.rho"), but within one source space only at #sv("archive.x.retrieval.in-domain.rho-source"). A map that fails this test will not retrieve; a map that passes it has shown very little.

#pullquote[A map that fails on held-out anchors will not retrieve; a map that passes has shown very little.]

#figure(
  image("fig/choice.svg", width: 100%, alt: "Slope charts, one per source space and testbed: the four possible targets ranked by anchor similarity on the left and by measured retrieval quality on the right; many lines cross, more on the Archive than on Wiki-de."),
  caption: cap[One source, four targets: the ranking by similarity against the ranking by result][Choosing a target from published anchors. For each source space, its four possible targets ranked by the similarity of the anchor matrices (left, overlap of the ten nearest anchors) and by the measured outcome of orthogonal #gl("index-translation")[index translation] (right, nDCG\@10 in per cent of a #gl("full-re-embed")[full re-embed]). A crossing line is a target that the similarity ranks wrongly.],
) <fig-choice>

== Hybrid search <sec-hybrid>

#figure(
  table-hybrid,
  caption: cap[Fusion of a translated index with #ab("bm25")[BM25]][nDCG\@10 with and without fusion with #ab("bm25")[BM25], means over the ordered pairs of open models; bridge is orthogonal #gl("index-translation")[index translation] with $k$ #gl("in-domain-anchors")[in-domain anchors]. Staying on the old model has the same means as the native columns, since every model is source and target equally often.],
) <tab-hybrid>

When the old model is gone, the alternative to a translated index is not an empty result list but lexical search, so #ab("bm25")[BM25] is the bar a bridge has to clear (@tab-hybrid, @fig-hybrid).

#figure(
  image("fig/hybrid.svg", width: 100%, alt: "Dot plot per testbed with ranges: nDCG at 10 of the re-embedded and the translated index alone and fused with BM25 with equal and tuned weights, and of BM25 alone."),
  caption: cap[Dense, lexical and fused retrieval][nDCG\@10 of dense retrieval alone and fused with #ab("bm25")[BM25], with equal weights and with a weight tuned on the other half of the queries. Markers are means and bars the range, over the five open models for the re-embedded index and over the ordered pairs of open models for the translated one. Translation is orthogonal #gl("index-translation")[index translation] with all #gl("in-domain-anchors")[in-domain anchors] or with the same number of #gl("external-anchors")[external anchors]: English Wikipedia on #tb[Wiki-de], German Wikipedia on the #tb[Archive].],
) <fig-hybrid>

#figure(
  fusion,
  caption: cap[How #gl("reciprocal-rank-fusion")[reciprocal rank fusion] joins two rankings][How #gl("reciprocal-rank-fusion")[reciprocal rank fusion] joins a dense and a lexical ranking, with an invented example. Passage A is second in one ranking and first in the other and comes out on top; F, found by one ranking only, falls behind.],
) <fig-fusion>

Combining term-based and embedding-based retrieval is common practice in such systems @huyen2025aiengineering; @fig-fusion shows how two rankings are joined. On the two Wikipedia testbeds #ab("bm25")[BM25] is far weaker than any dense index, and the translated index alone clears it in every pair. Fusion with so weak a lexical ranking lowers the native indexes on both testbeds, on #tb[Wiki-de] from #v("wiki.hy.native") to #v("wiki.hy.native-fused") and on #tb[MIRACL-de] from #v("miracl.hy.native") to #v("miracl.hy.native-fused"). The translated index gains a little from it on #tb[Wiki-de] (#v("wiki.hy.bridge") to #v("wiki.hy.fused")) and loses on #tb[MIRACL-de] (#v("miracl.hy.bridge") to #v("miracl.hy.fused")).

On the #tb[Archive] #ab("bm25")[BM25] is strong (#v("archive.bm25.ndcg")). With #v("archive.hybrid.k") anchors the translated index alone reaches #v("archive.hy.bridge") and is above #ab("bm25")[BM25] in only #v("archive.hy.bridge-beats-bm25") of #v("archive.hy.n") pairs. Fused with #ab("bm25")[BM25] it reaches #v("archive.hy.fused") and is above #ab("bm25")[BM25] alone in #v("archive.hy.fused-beats-bm25") of #v("archive.hy.n") pairs, while a native index fused with #ab("bm25")[BM25] reaches #v("archive.hy.native-fused"). With 1,000 anchors the fusion still reaches #v("archive.hybrid.procrustes.fwd.1000.fused") and is above #ab("bm25")[BM25] in #v("archive.hybrid.procrustes.fwd.1000.fused-beats-bm25") of #v("archive.hybrid.procrustes.fwd.1000.n") pairs. Translated vectors thus add to lexical search even where they are weaker than it; where lexical search is far weaker than they are, fusion with equal weights gains little or loses.

#pullquote[Translated vectors add to lexical search even where they are weaker than it.]

*A tuned weight.* Equal weights are a blunt choice where one ranking is much stronger than the other. With the weight chosen on the other half of the queries, the fused translated index reaches #v("wiki.x.hy.in-domain.20000.tuned") on #tb[Wiki-de] (#v("wiki.x.hy.in-domain.20000.bridge") alone, #v("wiki.x.hy.in-domain.20000.fused") with equal weights) and #v("miracl.x.hy.in-domain.20000.tuned") on #tb[MIRACL-de] (#v("miracl.x.hy.in-domain.20000.bridge") alone, #v("miracl.x.hy.in-domain.20000.fused") with equal weights); the gain over equal weights is #ci("wiki.x.c.tuned-vs-fused") and #ci("miracl.x.c.tuned-vs-fused"). On #tb[MIRACL-de] even the largest dense weight on our grid leaves the fusion slightly below the translated index alone, and the native indexes lose as well (#v("miracl.x.hy.native.tuned") against #v("miracl.hy.native")). On the #tb[Archive], where the two rankings are of similar strength, tuning changes nothing: the difference is #ci("archive.x.c.tuned-vs-fused"). With all #v("archive.kmax") #gl("in-domain-anchors")[in-domain anchors] the translated index fused with equal weights reaches #v("archive.x.hy.in-domain.10000.fused") there, which is #ci("archive.x.c.fused.in-domain.10000-vs-bm25") above #ab("bm25")[BM25] and #ci("archive.x.c.fused-vs-bridge") above the translated index alone.

*Public anchors in #gl("hybrid-search")[hybrid search].* The same measurement with Wikipedia anchors changes what was said above about public anchors. A translated index of the #tb[Archive] fitted on 10,000 Wikipedia anchors reaches #v("archive.x.hy.wikipedia.10000.bridge") alone and differs from #ab("bm25")[BM25] by #ci("archive.x.c.bridge.wikipedia.10000-vs-bm25"). Fused with equal weights it reaches #v("archive.x.hy.wikipedia.10000.fused"), which cannot be told from #ab("bm25")[BM25]: the difference is #ci("archive.x.c.fused.wikipedia.10000-vs-bm25"). With a tuned weight it reaches #v("archive.x.hy.wikipedia.10000.tuned"), which is #ci("archive.x.c.tuned.wikipedia.10000-vs-bm25") above #ab("bm25")[BM25] and at least as good as #ab("bm25")[BM25] in #v("archive.x.hy.wikipedia.10000.tuned-beats") of #v("archive.x.hy.wikipedia.10000.n") pairs; with 20,000 Wikipedia anchors it reaches #v("archive.x.hy.wikipedia.20000.tuned"). The #gl("in-domain-anchors")[in-domain anchors] give #v("archive.x.hy.in-domain.10000.tuned") under the same procedure. Next to a strong lexical ranking and with a tuned weight, the disadvantage of public anchors on the specialised collection is no longer visible: what the weaker map loses, #ab("bm25")[BM25] supplies.

= Discussion <sec-discussion>

#figure(
  ruled(
    columns: (auto, 1fr, 1.55fr, auto), align: (right, left, left, left),
    header: ([], [Question], [What the measurements say], [Section]),
    [1], [How much survives translation between open models?], [Index translation keeps #v("wiki.top.procrustes.fwd.mean")%, #v("miracl.top.procrustes.fwd.mean")% and #v("archive.top.procrustes.fwd.mean")% of a full re-embed, query translation #v("wiki.top.procrustes.bwd.mean")%, #v("miracl.top.procrustes.bwd.mean")% and #v("archive.top.procrustes.bwd.mean")%. No bridge is better than staying beyond the noise.], [#ref(<sec-open>, supplement: none)],
    [2], [Do commercial spaces translate?], [Cohere v3 at #v("wiki.cohere-v3.in-domain.procrustes.fwd.20000.mean")% on Wiki-de, Gemini-001 at #v("archive.gemini-001.in-domain.procrustes.fwd.10000.mean")% on the Archive.], [#ref(<sec-closed>, supplement: none)],
    [3], [How many anchor pairs?], [A few thousand. With 1,000 pairs: #v("wiki.in-domain.procrustes.fwd.1000.mean")%, #v("miracl.in-domain.procrustes.fwd.1000.mean")% and #v("archive.in-domain.procrustes.fwd.1000.mean")%. The random draw hardly matters.], [#ref(<sec-open>, supplement: none)],
    [4], [Can public or foreign-language anchors replace in-domain pairs?], [English anchors cost #sv("wiki.x.c.in-domain-vs-other-anchors.diff") points of nDCG\@10 on Wiki-de, Wikipedia anchors #sv("archive.x.c.in-domain-vs-other-anchors.diff") on the Archive. Under fusion with BM25 and a tuned weight that gap is no longer visible.], [#ref(<sec-anchors>, supplement: none), #ref(<sec-hybrid>, supplement: none)],
    [5], [Does anchor similarity predict the outcome?], [It correlates within a testbed (#v("wiki.predict.knn.fwd"), #v("miracl.predict.knn.fwd") and #v("archive.predict.knn.fwd") for neighbour overlap) but does not give the size of the loss; accuracy on held-out anchors is saturated on the Wikipedia testbeds.], [#ref(<sec-predict>, supplement: none)],
    [6], [What does lexical search add?], [On the Archive the fusion reaches #v("archive.x.hy.in-domain.10000.fused") against #v("archive.bm25.ndcg") for BM25 and #v("archive.x.hy.in-domain.10000.bridge") for the translated index alone. Where BM25 is weak, equal weights lower the result and a tuned weight gains little.], [#ref(<sec-hybrid>, supplement: none)],
    [7], [Are anchors needed in the query role?], [No. They change orthogonal query translation by #sv("wiki.x.c.query-role-vs-document-role.procrustes.diff"), #sv("miracl.x.c.query-role-vs-document-role.procrustes.diff") and #sv("archive.x.c.query-role-vs-document-role.procrustes.diff") points of nDCG\@10.], [#ref(<sec-open>, supplement: none)],
    [8], [Is a bridge an upgrade from a much weaker model?], [No. None of #v("all.x.upgrade.of") combinations is better than staying; #v("all.x.upgrade.below") are worse.], [#ref(<sec-upgrade>, supplement: none)],
    [9], [What happens in a partly migrated index?], [It is worse than a fully translated one: #v("wiki.x.mixed.90.mean")%, #v("miracl.x.mixed.90.mean")% and #v("archive.x.mixed.90.mean")% with nine tenths translated.], [#ref(<sec-mixed>, supplement: none)],
  ),
  caption: cap[The nine questions and what the measurements say][The nine questions of @sec-experiments and what the measurements say. Percentages are nDCG\@10 relative to a #gl("full-re-embed")[full re-embed], in the order #tb[Wiki-de], #tb[MIRACL-de], #tb[Archive]; points are differences in nDCG\@10 (hundredths); for the orthogonal map with all #gl("in-domain-anchors")[in-domain anchors] unless stated otherwise.],
) <tab-summary>

#figure(
  decision,
  caption: cap[What the measurements suggest for an operator][What the measurements suggest for an operator, by what is still at hand. Orange marks the space of the old model and blue that of the new one, as in @fig-overview.],
) <fig-decision>

@tab-summary collects the answers to the nine questions, and @fig-decision turns them into the choices an operator faces.

*What translation is for.* The experiments leave no room for a bridge as an upgrade path. Wherever the old model can still embed queries, no map we fitted was better than keeping it beyond the noise of the query sample, and nearly all were worse. Between the five open models that is a matter of a few points lost in translation. With a much weaker old model it is a matter of principle: the translated index carries the old model's limits into the new space, however good the new model is (@sec-upgrade).

Translation is useful where staying is not possible, which is the situation that motivated this paper: the old model is retired, the provider has been left, or the budget for its #ab("api")[API] is exhausted. What remains then is lexical search, until the corpus has been embedded again. In that situation one matrix multiplication per stored vector yields an index that, with pairs from the collection itself, keeps between #v("all.top.fwd.min")% and, for the closest pairs, nearly all of the new model's retrieval quality, depending on the collection and the pair of spaces. Such an index was better than lexical search alone in nearly every case, on its own where #ab("bm25")[BM25] is weak and fused with #ab("bm25")[BM25] where it is strong. The re-embed can follow at its own pace.

For this purpose #gl("index-translation")[index translation] is the natural mode: with the orthogonal map it was the better of the two on average on every testbed, and it leaves the query path unchanged. The re-embed should not be written into the translated index as it proceeds. A #gl("mixed-index")[mixed index] was worse than the fully translated one for most of the way, because native vectors outrank translated ones (@sec-mixed). The new index is better built beside the translated one and put into service when it is complete (@fig-paths).

#figure(
  image("fig/paths.svg", width: 100%, alt: "Line chart per testbed against the share of the collection already re-embedded: building beside keeps the level of the translated index and jumps to 100 per cent at the end; re-embedding in place first drops, by up to about 18 points, and recovers only towards the end."),
  caption: cap[Two ways from a translated index to a re-embedded one][Two ways from a translated index to a re-embedded one, against the share of the collection already re-embedded: in place, so that the index holds translated and re-embedded vectors side by side (orange, from @tab-mixed), or beside it, so that the translated index serves until the new one is complete (blue). nDCG\@10 in per cent of a #gl("full-re-embed")[full re-embed], means over the ordered pairs of open models.],
) <fig-paths>

*What it costs.* The pairs are not free: every in-domain pair is a passage embedded with the new model. For a large collection a few thousand passages are a negligible share. For a small one they are not. The #v("archive.kmax") pairs behind the #tb[Archive] figures are 46% of its 21,510 passages, so translation saves about half of the re-embed there (@fig-cost). With 1,000 pairs, about 5% of the passages, the translated index keeps #v("archive.in-domain.procrustes.fwd.1000.mean")% of the new model's quality and stays below #ab("bm25")[BM25] on its own, and it still improves #ab("bm25")[BM25] when fused with it in #v("archive.hybrid.procrustes.fwd.1000.fused-beats-bm25") of #v("archive.hybrid.procrustes.fwd.1000.n") pairs.

#figure(
  image("fig/cost.svg", width: 100%, alt: "Line chart on a logarithmic axis: retrieval quality of index translation against the share of the collection embedded as anchors. The two Wikipedia testbeds reach about 90 per cent with under one per cent of the collection; the Archive needs more than a tenth for about 85 per cent."),
  caption: cap[What the pairs cost][What the pairs cost: nDCG\@10 of orthogonal #gl("index-translation")[index translation] in per cent of a #gl("full-re-embed")[full re-embed], against the #gl("in-domain-anchors")[in-domain anchors] that the new model has to embed, as a share of the collection (searched passages and anchors). Mean and range over the ordered pairs of open models. A #gl("full-re-embed")[full re-embed] is 100% of the collection.],
) <fig-cost>

*What published anchors add.* An operator who holds the texts, the stored vectors and a new model can fit a map without any help, as we did for the Gemini index, and pairs from the collection itself were better than public ones. Published anchors serve the cases this does not reach. They allow candidate spaces to be compared before anything is embedded. They let a third party publish a map together with a measurement that others can repeat. And they cover an index whose texts are not available to whoever has to migrate it.

On the #tb[Archive] a translated index fitted on public anchors was clearly weaker than one fitted on in-domain pairs, but fused with #ab("bm25")[BM25] under a tuned weight it served as well, and it was better than #ab("bm25")[BM25] alone. For an operator who has lost the old model and holds nothing but vectors, that is the difference between lexical search and #gl("hybrid-search")[hybrid search]. What published anchors did not provide in our measurements is a reliable forecast: neither the similarity of two anchor matrices nor the accuracy of a map on held-out anchors told how much retrieval quality a translation would keep.

*What the standard has to ask for.* The #gl("anchor-corpus")[anchor corpus] can be small. On Wikipedia a few thousand passages carried almost all of the attainable quality; on the #tb[Archive] the step from 5,000 to 10,000 in-domain pairs still added more than a point, and public anchors kept improving up to 20,000. A corpus of 20,000 passages is therefore a reasonable size; at 1,024 dimensions that is about 80 MB per model version. One role is enough. Anchors embedded in the query role did not improve the translation of queries with the orthogonal map and made ridge regression worse, so the standard asks for the document role and leaves further roles to the provider. English anchors served German retrieval, with multilingual models. The manifest should record how a map was centred, since the same orthogonal map without centring collapsed on single pairs. The requirement of a measurement in the manifest is supported by the spread of outcomes: on the #tb[Archive] the same procedure keeps between #v("archive.top.procrustes.fwd.min") and #v("archive.top.procrustes.fwd.max")% depending on the pair, and anchor similarity does not predict the level.

*Privacy.* Text can be reconstructed from embeddings @morris2023vec2text @kim2026zero2text, and a map into a space for which an inversion model exists can carry that attack to other spaces @jha2025vec2vec. Published anchors make such maps cheap: in our experiments 1,000 pairs were enough for about nine tenths of the retrieval quality on Wikipedia. Whoever can call a model's #ab("api")[API] can produce such pairs today, so the standard creates no new capability for current models; it does extend the capability to models that are no longer served and to parties without #ab("api")[API] access. The practical consequence holds with or without the standard: a vector index deserves the same protection as the text it was computed from.

#pullquote[A vector index deserves the same protection as the text it was computed from.]

*Incentives and the alternative.* A provider gains nothing directly from making it easier to leave, and the cost of publishing anchors is one batch job per release. Cohere's Wikipedia release shows that a provider may publish far more than the standard asks. A shared space that a provider builds into its models, as in Voyage 4 @voyage2026v4, is the stronger guarantee, since it needs no map; it is limited to the models one provider chooses to align, and the card's `compatible_with` field records it. The two approaches complement each other.

*Next steps.* For a provider the step is small: publish a card and the anchor vectors with the next model release. A vector database can act without waiting for anyone, by storing a `space_id` with every index and refusing to compare across spaces. For the standard itself three things are open: anchor corpora for further languages and for specialised domains, a public register of cards and manifests, and a home in a standards body. The specification is at version 0.1, and its repository is the place for issues and proposals. The open research questions are collected in @sec-future.

= Limitations <sec-limits>

The study covers one language, three collections of at most #v("wiki.corpus") passages and exact search. #tb[Wiki-de] is close to the ceiling for every model and has no hard negatives; the #tb[Archive] questions are synthetic, have one relevant passage each and come from a single language model. The two Wikipedia testbeds share their queries. With about 300 queries per testbed, differences of a few points between single pairs are within noise; the intervals we report cover the sampling of queries, not the choice of models, and further draws of the anchors were made for the orthogonal map at two budgets only.

The fusion weight was tuned on half of the queries over a coarse grid that ends at a dense weight of 0.8. The #gl("in-domain-anchors")[in-domain anchors] of #tb[Wiki-de] are consecutive passages of one shard and not a random sample. #mo[mE5-large] reads at most 512 tokens and so cuts #v("archive.tokens.me5-large.truncated")% of the #tb[Archive] passages short; it is the target of the weakest #tb[Archive] pairs.

The five open models are of similar strength (@tab-native), and the upgrade from a much weaker model rests on one old model with a short input window. The anchors in the query role were passages embedded with the query prompt; texts that look like queries were not tested. For the #gl("mixed-index")[mixed index] we tried no remedy, such as calibrating the scores of translated vectors or searching two indexes and fusing their rankings. The only specialised collection is private, so that part of the study cannot be repeated by others, while the Wikipedia testbeds and the public anchors can. The open models are small (at most 0.6 billion parameters), and the two commercial spaces entered through stored document vectors only, without a stay reference and without anchors in the query role. We tested three kinds of map; unpaired or more elaborate translators @jha2025vec2vec may do better.

= Future work <sec-future>

The measurements leave six questions open. Each follows from a limit of this study, and none can be answered from the data at hand.

+ *Anchors for specialised domains.* On the #tb[Archive], public Wikipedia anchors were clearly weaker than pairs from the collection (@sec-anchors). Whether a public #gl("anchor-corpus")[anchor corpus] drawn from a domain, such as legal or medical text, closes that gap for collections of the same domain is unknown. The answer decides how many anchor corpora the standard needs.
+ *Anchors that look like queries.* Our anchors in the query role were passages embedded with the query prompt (@sec-open). Short questions are distributed differently from passages, and whether a map fitted on them translates queries better has not been tested.
+ *A remedy for the #gl("mixed-index")[mixed index].* Native vectors outrank translated ones (@sec-mixed). Calibrating the scores of translated vectors, or searching the two parts separately and fusing the rankings, might remove the dip. Neither has been tried, and it is unclear whether a calibration fitted on anchors carries over to queries.
+ *The stay reference for commercial spaces.* For #mo[Cohere v3] and #mo[Gemini-001] only stored document vectors were at hand (@sec-closed). The comparison with staying on the old model is therefore missing for the very spaces whose models an operator cannot run.
+ *Larger models and other languages.* The open models have at most 0.6 billion parameters, and the text is German. Whether less is lost between larger models, as converging representations would suggest @huh2024platonic, is open, and so is whether the findings hold for languages with less training data.
+ *A forecast without queries.* Neither the similarity of two anchor matrices nor the accuracy of a map on held-out anchors told the size of the loss (@sec-predict). A measure that does, computed from published anchors alone, would let an operator choose a target without a judged query set. Whether such a measure exists is open.

= Conclusion

Whether an index can be carried from one embedding space into another is an empirical property of the pair of spaces and of the collection. With an orthogonal map fitted on anchor pairs, a translated index kept on average #v("wiki.top.procrustes.fwd.mean")% of the retrieval quality of a #gl("full-re-embed")[full re-embed] on an easy German Wikipedia testbed, #v("miracl.top.procrustes.fwd.mean")% on #tb[MIRACL-de] and #v("archive.top.procrustes.fwd.mean")% on a private document archive, across five open models. Stored Cohere vectors translated into the open spaces at #v("wiki.cohere-v3.in-domain.procrustes.fwd.20000.mean")% on the Wikipedia testbed and stored Gemini vectors at #v("archive.gemini-001.in-domain.procrustes.fwd.10000.mean")% on the archive, where the open pairs reach #v("archive.top.procrustes.fwd.mean")%.

A bridge was almost always worse than keeping the old model and never better beyond the noise of the query sample, between models of similar strength and from a much weaker model into far stronger ones. An index that mixes translated and re-embedded vectors was worse than a fully translated one. Translation is thus a way to keep an index searchable when its model is gone, together with lexical search where that is strong. It is not a substitute for re-embedding, not an upgrade, and not an index to re-embed in place, piece by piece.

#pullquote[Translation is not a substitute for re-embedding, not an upgrade, and not an index to re-embed in place, piece by piece.]

How well a given index translates can only be found out with paired vectors. An operator can make them from their own collection as long as the texts and a new model are at hand; what nobody can make without the old model are vectors of new texts and of queries in the old space. We therefore ask providers of embedding models for one publication with every model version: an #gl("embedding-space-card")[Embedding Space Card] and the embeddings of a public #gl("anchor-corpus")[anchor corpus] of about 20,000 passages in the document role. We ask the #ab("w3c")[W3C] Web Machine Learning Community Group, which has before it a proposal that includes an embedding-space identifier @webml2026embedding, to consider the card as the description behind that identifier and the anchor embeddings as part of the card. 
#heading(numbering: none)[Code and data availability]

The specification with both #ab("json")[JSON] Schemas, the code of all experiments and the result files from which every result number, table and figure in this paper is generated are available at #link("https://github.com/egbalwaldmann/embedding-anchors"). A first #gl("anchor-corpus")[anchor corpus] (20,000 German and 20,000 English Wikipedia passages), its vectors in the document role for the five open models, one #gl("embedding-space-card")[Embedding Space Card] per space and one adapter with its manifest are available at #link("https://huggingface.co/datasets/egbalwaldmann/embedding-anchors"), with a mirror at #link("https://www.kaggle.com/datasets/egbalwaldmann/embedding-anchors"). A companion page at #link("https://anchors.egbalwaldmann.com") shows the results interactively, pair by pair; it is built from the same result files and is part of the repository. This version of the paper is archived together with the code and the result files under the #ab("doi")[DOI] #link("https://doi.org/10.5281/zenodo.24484736")[10.5281/zenodo.24484736]. The #tb[Archive] testbed is private; none of its texts or vectors are released.

#heading(numbering: none)[Funding and competing interests]

This work received no funding. The author declares no competing interests.

#{
  set text(9.5pt, region: "US")
  bibliography("refs.bib", style: "ieee", title: "References")
}

#show: appendix

= Background in brief <app-background>

This appendix is for readers who have not worked with embeddings.

*Embeddings.* An embedding model turns a text into a list of numbers, a vector with several hundred to a few thousand entries. It is trained so that texts of similar meaning get vectors that point in similar directions. The cosine of the angle between two vectors serves as the measure of similarity.

*Search.* To make a collection searchable, every passage is embedded once and the vectors are stored; this store is the index. A query is embedded with the same model, and the passages whose vectors are closest to it are returned. Nothing is compared word by word, which is why such a search finds a passage that answers a question in other words.

*Why models do not mix.* Each model arranges the texts in its own way. A single number in a vector means nothing by itself, and the same text gets unrelated vectors from two models. A query from one model compared with stored vectors of another returns nothing useful. Replacing the model therefore means embedding every passage again, which costs time and money and needs the texts.

*Translating instead.* If the two arrangements have nearly the same shape, one can be laid over the other (@fig-intuition). The map that does this is fitted on texts whose vectors are known in both spaces, the anchors. This paper proposes that providers publish such vectors for a fixed public list of texts, and it measures how well translated vectors work.

*How quality is measured.* For a set of queries with known relevant passages we look at the first ten results. nDCG\@10 is high when the relevant passages are among them and near the top. Most results are given relative to embedding everything again with the new model, which counts as 100%.

*What to skip.* The proposal (@sec-proposal) and the discussion (@sec-discussion) can be read without the details of the experiments. A reader new to the field may skip the section on adapters and measures and @app-methods.

= Example documents <app-examples>

The two listings show the machine-readable parts of the standard as they are published with the anchor release: the #gl("embedding-space-card")[Embedding Space Card] of one space, and the #gl("adapter-manifest")[Adapter Manifest] of an orthogonal map from that space into another. The map was fitted on the 20,000 German anchors; the saved weights reproduce both measurements in the manifest. In the second measurement the map translates queries, so the model whose index is searched is the target of the map and the re-embed reference is `native_source`.

#let example(path) = raw(read(path).replace("https://huggingface.co/datasets/egbalwaldmann/embedding-anchors/resolve/main", "https://…"), lang: "json", block: true)

#figure(
  align(left, example("../spec/examples/space-card.bge-m3.json")),
  caption: cap[#gl("embedding-space-card")[Embedding Space Card] of #mo[bge-m3]][#gl("embedding-space-card")[Embedding Space Card] of #mo[bge-m3], without the list of its anchor files.],
) <lst-card>

#figure(
  align(left, example("../spec/examples/adapter-manifest.bge-m3--multilingual-e5-large.orthogonal.json")),
  caption: cap[#gl("adapter-manifest")[Adapter Manifest] of an orthogonal map from #mo[bge-m3] into #mo[mE5-large]][#gl("adapter-manifest")[Adapter Manifest] of an orthogonal map from #mo[bge-m3] into #mo[mE5-large]. The address of the weights is shortened.],
) <lst-manifest>

= Models and prompts <app-models>

@tab-models lists the revision of the weights that were used for each model, its licence and the prompts its model card prescribes for documents and queries. All models were run through the sentence-transformers library on one Apple M3 Max. Retrieval is exact cosine search, every random choice uses the seed 20261120, and intervals come from 2,000 resamples of the queries. Every result number, table and figure in this paper is written by one script from the result files in the repository; nothing is copied by hand.

#figure(
  placement: none,
  table-models,
  caption: cap[Revisions, licences and prompts of the models][Revisions, licences and prompts of the models. A text enters a model as prefix followed by the text; a dash means no prefix. The line break in the query prompt of #mo[Qwen3-0.6B] is written as `\n`.],
) <tab-models>

= Methods in detail <app-methods>

Three maps are fitted on $k$ anchor pairs, $k in {100, 300, 1000, 3000, 5000, 10000, 20000}$ as far as the anchor set reaches: orthogonal Procrustes after centring (semi-orthogonal where dimensions differ), affine ridge regression with the penalty chosen on held-out anchors, and a residual network with one hidden layer on top of the ridge solution, fitted at $k = 3000$ and, where available, $k = 20000$. The orthogonal map is $W = U V^top$ from the thin singular value decomposition $U Sigma V^top$ of the cross-covariance of the centred anchor matrices; a vector $x$ is mapped to $(x - mu_s) W + mu_t$, with the two anchor means $mu_s$ and $mu_t$. Ridge regression is fitted on nine tenths of the $k$ pairs for each of five penalties, the penalty with the highest mean cosine on the remaining tenth is kept, and the map is refitted on all $k$ pairs. The residual network adds to the ridge output the output of one hidden layer of 2,048 units (GELU, dropout 0.1), trained with a cosine loss and AdamW and stopped early on a held-out tenth.

For #gl("query-translation")[query translation] every map is fitted anew in the opposite direction on the same pairs; no map is inverted. In the main experiments all anchors are passages embedded in the document role, so a map applied to queries works on a kind of input it was not fitted on. To see whether that matters, we embedded the same anchor passages a second time with each model's query prompt and fitted the maps for #gl("query-translation")[query translation] on these vectors, on both sides of the pair; #mo[bge-m3] uses no prompts, so its vectors are the same in both roles. As a control for the centring we also fitted the orthogonal map on the uncentred anchor matrices.

The anchor sets are nested: every pair of spaces uses the same random order of anchors, and a budget of $k$ takes its first $k$. With fewer pairs than dimensions the orthogonal map is not determined by the data, which shows in the results for 100 and 300 pairs. All vectors are normalised to unit length before and after mapping. Retrieval is exact cosine search.

We report nDCG\@10 (normalised discounted cumulative gain over the first ten results, which rewards relevant items more the higher they are ranked) and Recall\@10 (the share of the relevant items that appear among the first ten) against the relevance judgements and, as a label-free measure, the share of the #gl("full-re-embed")[full re-embed]'s top ten that the bridged system returns. A bridge is compared with staying on the old model per query: we resample the queries 2,000 times and call the difference in nDCG\@10 a tie when its 95% interval includes zero.

The lexical retriever is #ab("bm25")[BM25], the standard ranking function over word counts, with German stemming; hybrid runs fuse the top 1,000 of the two rankings by #gl("reciprocal-rank-fusion")[reciprocal rank fusion] with the usual constant of 60 and equal weights. In a second variant the weight of the dense ranking is chosen from 0.2, 0.35, 0.5, 0.65 and 0.8 on one half of the queries and applied to the other half, in both directions. Differences between two configurations are given for the mean over all ordered pairs of open models: the nDCG\@10 of each query is averaged over the pairs, the queries are resampled as above, and we report the difference in points of nDCG\@10 (hundredths) with its 95% interval. The main results come from one random draw of anchors; for the orthogonal map with 1,000 and 5,000 pairs we repeated the fit with five further draws.

= Terms and abbreviations <app-terms>

In the running text, models and their spaces stand in a grey box (#mo[bge-m3]), testbeds and abbreviations in small capitals (#tb[Wiki-de], #ab("cka")[CKA]), and identifiers from code and documents in monospace (`space_id`). Abbreviations and the terms below are linked to their entry here; tables and figures name models and testbeds plainly.

#heading(level: 2, numbering: none, outlined: false)[Terms]

/ Embedding#metadata(none)<gl-embedding>: The vector that an embedding model writes for a text. Texts of similar meaning get vectors that lie close together.
/ Space#metadata(none)<gl-space>: The set of vectors that one encoder writes in one configuration. Only vectors of the same space can be compared.
/ Compatible spaces#metadata(none)<gl-compatible-spaces>: Spaces whose vectors the publisher guarantees to be directly comparable, without a map.
/ Embedding Space Card#metadata(none)<gl-embedding-space-card>: The machine-readable description of a space: model and revision, dimensions, normalisation, and the prefix or task type of each role.
/ Role#metadata(none)<gl-role>: The way a text enters the encoder, typically as a document or as a query.
/ Prefix, task type#metadata(none)<gl-prefix>: A piece of text or a setting that a model adds to an input to mark its role.
/ Unit length#metadata(none)<gl-unit-length>: A vector of length one. For such vectors the cosine is the dot product.
/ Passage#metadata(none)<gl-passage>: The piece of a document that gets one vector.
/ Vector index#metadata(none)<gl-vector-index>: The stored vectors of a collection, searched by comparing them with the vector of a query.
/ Dense retrieval#metadata(none)<gl-dense-retrieval>: Search by comparing vectors, here by exact cosine search.
/ Lexical retrieval#metadata(none)<gl-lexical-retrieval>: Search by matching words, here with BM25.
/ Hybrid search#metadata(none)<gl-hybrid-search>: The ranking of a dense index and the lexical ranking of BM25 are fused into one, here by reciprocal rank fusion.
/ Reciprocal rank fusion#metadata(none)<gl-reciprocal-rank-fusion>: A way to fuse rankings: each ranking gives an item the score 1/(60 + rank), and the scores are added.
/ Anchor corpus#metadata(none)<gl-anchor-corpus>: A fixed, public, versioned list of passages. Its vectors in a space are the anchor embeddings of that space.
/ Anchor pair#metadata(none)<gl-anchor-pair>: The two vectors of one anchor passage in two spaces. Maps are fitted on such pairs.
/ In-domain anchors#metadata(none)<gl-in-domain-anchors>: Pairs made from passages of the collection that is to be searched, or on Wiki-de from the same source, held out from the search.
/ External anchors#metadata(none)<gl-external-anchors>: Public anchors from outside the searched collection: English Wikipedia on Wiki-de, German Wikipedia on the Archive.
/ Public anchors#metadata(none)<gl-public-anchors>: Pairs made from a public corpus, here Wikipedia, in place of the collection itself.
/ Map, adapter#metadata(none)<gl-map>: A function fitted on anchor pairs that carries vectors of a source space into a target space. It has one direction.
/ Orthogonal map#metadata(none)<gl-orthogonal-map>: A rotation, with a projection where the dimensions differ, computed in closed form from the anchor pairs. Between spaces of equal dimension it leaves every distance as it was.
/ Centring#metadata(none)<gl-centring>: Subtracting the mean of the anchor vectors of the source space before mapping and adding the mean of the target space afterwards.
/ Ridge regression#metadata(none)<gl-ridge-regression>: A least-squares map with a penalty on the size of its weights. It is free to change distances.
/ Residual network#metadata(none)<gl-residual-network>: A small neural network that adds a correction to the output of the ridge map.
/ Fit quality#metadata(none)<gl-fit-quality>: The mean cosine between mapped vectors and the true vectors of the target space. It is not a retrieval measure.
/ Adapter Manifest#metadata(none)<gl-adapter-manifest>: The record that travels with an adapter. It names the two spaces, the map and the anchors, and must contain a measured retrieval result.
/ Index translation#metadata(none)<gl-index-translation>: The stored document vectors are mapped once into the new space and searched with queries of the new model.
/ Query translation#metadata(none)<gl-query-translation>: The stored index stays as it is, and each query of the new model is mapped into the old space.
/ Bridge#metadata(none)<gl-bridge>: A system that serves through an adapter, in either mode.
/ Full re-embed#metadata(none)<gl-full-re-embed>: Documents and queries are embedded with the new model. Retrieval percentages in the paper are relative to this.
/ Stay#metadata(none)<gl-stay>: Documents and queries remain in the space of the old model.
/ Mixed index#metadata(none)<gl-mixed-index>: One index that holds translated and re-embedded vectors side by side.
/ Relevance judgement#metadata(none)<gl-relevance-judgement>: The decision of a person that a passage, or a page, answers a query.
/ Known-item question#metadata(none)<gl-known-item-question>: A question written for one passage, which is its only relevant item.
/ Hard negative#metadata(none)<gl-hard-negative>: A passage that looks relevant to a query and is judged not to be.
/ Top-ten overlap#metadata(none)<gl-top-ten-overlap>: The share of the re-embedded index's ten best results that another index also returns.
/ Tie#metadata(none)<gl-tie>: A difference in nDCG\@10 whose 95% interval includes zero.

#heading(level: 2, numbering: none, outlined: false)[Abbreviations and symbols]

/ nDCG\@10#metadata(none)<gl-ndcg-10>: Normalised discounted cumulative gain over the first ten results. It rewards relevant results more the higher they are ranked; 1 is the best possible ranking.
/ Recall\@10, R\@10#metadata(none)<gl-recall-10>: The share of the relevant items that appear among the first ten results.
/ BM25#metadata(none)<gl-bm25>: Best Matching 25, the standard ranking function over word counts.
/ CKA#metadata(none)<gl-cka>: Centred kernel alignment, a similarity of two sets of vectors that ignores rotation.
/ RSA#metadata(none)<gl-rsa>: Representational similarity analysis, here the rank correlation of the pairwise cosines in two spaces.
/ XLM-R#metadata(none)<gl-xlm-r>: XLM-RoBERTa, the multilingual encoder on which three of the five open models are built.
/ MIRACL#metadata(none)<gl-miracl>: Multilingual Information Retrieval Across a Continuum of Languages, the benchmark behind the two Wikipedia testbeds.
/ API#metadata(none)<gl-api>: Application programming interface, here the service through which a provider's model is called.
/ JSON#metadata(none)<gl-json>: JavaScript Object Notation, the format of cards and manifests.
/ DOI#metadata(none)<gl-doi>: Digital object identifier.
/ W3C#metadata(none)<gl-w3c>: World Wide Web Consortium.
/ SD#metadata(none)<gl-sd>: Standard deviation.
/ 95% interval#metadata(none)<gl-95-interval>: The range that holds the middle 95% of the values from 2,000 resamples of the queries.
/ $k$: The number of anchor pairs a map is fitted on.
/ $W$, $mu_s$, $mu_t$: The orthogonal map and the means of the anchor vectors in the source and the target space.

= Abstract in German <app-german>

A translation of the abstract into German.

#{
  set text(lang: "de")
  heading(level: 2, numbering: none, outlined: false)[Zusammenfassung]
  [Ein Vektorindex ist an das Embedding-Modell gebunden, das ihn geschrieben hat: Vektoren zweier Modelle lassen sich nicht vergleichen, ein Modellwechsel bedeutet deshalb, jedes Dokument neu einzubetten. Abbildungen, die aus gepaarten Vektoren geschätzt werden, übersetzen zwischen manchen Räumen und scheitern bei anderen, und Betreiber können vorab nicht wissen, welcher Fall vorliegt, weil über einen Embedding-Raum nichts in vergleichbarer Form veröffentlicht wird. Wir schlagen einen minimalen Standard vor, der die Frage beantwortbar macht, ohne dass Anbieter ihre Modelle ändern müssen: eine _Embedding Space Card_, die festhält, was übereinstimmen muss, damit zwei Vektoren vergleichbar sind, ein öffentliches _Ankerkorpus_, dessen Embeddings jeder Anbieter zu jeder Modellversion veröffentlicht, und ein _Adapter Manifest_, das eine Abbildung zwischen zwei Räumen an ein gemessenes Suchergebnis bindet. Wir messen die Übersetzung auf zwei deutschen Wikipedia-Testbetten und einem privaten deutschen Archiv, zwischen fünf offenen Modellen und aus zwei kommerziellen Räumen. Mit einer orthogonalen Abbildung, geschätzt aus bis zu 20.000 Ankerpaaren aus der Sammlung, behält ein übersetzter Index im Mittel #de("wiki.top.procrustes.fwd.mean") %, #de("miracl.top.procrustes.fwd.mean") % und #de("archive.top.procrustes.fwd.mean") % des nDCG\@10 eines vollständig neu eingebetteten. Er ist fast immer schlechter als das beibehaltene alte Modell und nie jenseits des Rauschens der Anfragestichprobe besser, auch wenn das alte Modell viel schwächer ist: Ein übersetzter Index erbt die Grenzen des Modells, das ihn geschrieben hat. Ein Index, der übersetzte und neu eingebettete Vektoren mischt, ist schlechter als ein vollständig übersetzter. Anker in der Anfrage-Rolle helfen nicht; der Standard verlangt deshalb nur Anker in der Dokument-Rolle. Wikipedia-Anker statt Ankern aus dem Archiv selbst kosten dort #de("archive.alt.loss.mean") Prozentpunkte; dieser Abstand ist nicht mehr sichtbar, sobald der übersetzte Index bei abgestimmter Gewichtung mit BM25 fusioniert wird. Weder die Ähnlichkeit zweier Ankermatrizen noch die Trefferquote einer Abbildung auf zurückgehaltenen Ankern sagt die Größe des Verlusts voraus; das Manifest verlangt deshalb eine Messung. Übersetzen hält einen Index durchsuchbar, wenn sein Modell nicht mehr verfügbar ist. Es ersetzt das Neu-Einbetten nicht und ist kein Upgrade.]
  std.v(1mm)
  set par(justify: false)
  [*Schlagwörter* #h(0.6em) Text-Embeddings · Vektorsuche · Modellwechsel · Interoperabilität · Retrieval · AI Engineering · künstliche Intelligenz]
}
