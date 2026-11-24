// Drawn figures.
#import "@preview/cetz:0.5.3"

#let old = rgb("#fbe3d0")   // space of the old model
#let new = rgb("#d6e6f5")   // space of the new model
#let pub = rgb("#efefef")   // public texts

#let overview = {
  set text(9pt)
  set par(justify: false, leading: 0.45em)
  let small(body) = text(8pt, body)
  cetz.canvas(length: 1cm, {
    import cetz.draw: *
    let bx(name, x, y, w, fill, body, h: 1.15) = {
      rect((x - w / 2, y - h / 2), (x + w / 2, y + h / 2), radius: 2pt, fill: fill, stroke: 0.6pt, name: name)
      content((x, y), align(center, body))
    }
    let arrow(a, b) = line(a, b, stroke: 0.6pt, mark: (end: "stealth", fill: black, scale: 0.55))
    let note(pos, anchor, body) = content(pos, anchor: anchor, padding: 3pt, small(body))
    let tag(y, body) = content((0, y), anchor: "west", strong(body))

    // (a) what is published, and what follows from it
    tag(0, [(a)])
    bx("corpus", 2.05, 0, 2.5, pub, [Anchor corpus \ #small[public texts]])
    bx("a", 6.2, 0.75, 3.3, old, [Anchor vectors $A$ \ #small[with the card of space $A$]])
    bx("b", 6.2, -0.75, 3.3, new, [Anchor vectors $B$ \ #small[with the card of space $B$]])
    bx("map", 10.45, 0, 2.9, white, [Map $A -> B$ \ #small[fitted on the pairs]])
    bx("manifest", 14.35, 0, 3.1, white, [Adapter Manifest \ #small[map and measurement]])
    arrow("corpus.east", "a.west")
    arrow("corpus.east", "b.west")
    note((3.75, 0.5), "south", [model $A$])
    note((3.75, -0.5), "north", [model $B$])
    arrow("a.east", "map.west")
    arrow("b.east", "map.west")
    arrow("map.east", "manifest.west")

    line((0, -1.75), (15.9, -1.75), stroke: (paint: luma(170), thickness: 0.4pt, dash: "dashed"))

    // (b) index translation
    tag(-2.75, [(b)])
    bx("ia", 2.05, -2.75, 2.5, old, [Stored index \ #small[vectors of model $A$]])
    bx("ib", 7.2, -2.75, 2.9, new, [Translated index \ #small[in space $B$]])
    bx("qb", 14.35, -2.75, 3.1, new, [Query \ #small[embedded by model $B$]])
    arrow("ia.east", "ib.west")
    note((4.52, -2.75), "south", [map, once])
    arrow("qb.west", "ib.east")
    note((10.72, -2.75), "south", [search])

    // (c) query translation
    tag(-4.35, [(c)])
    bx("ia2", 2.05, -4.35, 2.5, old, [Stored index \ #small[vectors of model $A$]])
    bx("qa", 9.6, -4.35, 2.9, old, [Translated query \ #small[in space $A$]])
    bx("qb2", 14.35, -4.35, 3.1, new, [Query \ #small[embedded by model $B$]])
    arrow("qb2.west", "qa.east")
    note((11.92, -4.35), "south", [map])
    arrow("qa.west", "ia2.east")
    note((5.72, -4.35), "south", [search])
  })
}

// The parts of a space identifier, with what each part stands for.
#let space-id = {
  set text(9pt)
  set par(justify: false, leading: 0.45em)
  cetz.canvas(length: 1cm, {
    import cetz.draw: *
    let parts = (
      ("baai", [publisher], [who released the model]),
      ("bge-m3", [model], [the name it is known by]),
      ("5617a9f6", [revision], [the weights; a new one whenever they change behind the name]),
      ("dense", [variant], [output dimensions, truncation, normalisation, prefixes or task types]),
    )
    let seps = ("/", "@", ":")
    let cw = 0.3        // width of one character of the identifier
    let gap = 0.5       // room for a separator
    let total = parts.map(p => p.at(0).len() * cw + 0.3).sum() + gap * seps.len()
    let x = (15.9 - total) / 2
    let slot = 15.9 / parts.len()
    for (i, (id, name, what)) in parts.enumerate() {
      let w = id.len() * cw + 0.3
      let cx = x + w / 2
      let lx = slot * (i + 0.5)
      rect((x, -0.42), (x + w, 0.42), radius: 2pt, fill: pub, stroke: 0.6pt)
      content((cx, 0), text(13pt, raw(id)))
      line((cx, -0.42), (cx, -0.85), (lx, -0.85), (lx, -1.15), stroke: 0.5pt + luma(110))
      content((lx, -1.2), anchor: "north", box(width: slot * 1cm - 5mm, align(center, [#strong(name) \ #text(8pt, what)])))
      if i < seps.len() { content((x + w + gap / 2, 0), text(13pt, raw(seps.at(i)))) }
      x += w + gap
    }
  })
}

// What the measurements suggest an operator does, by what is still at hand.
#let decision = {
  set text(9pt)
  set par(justify: false, leading: 0.45em)
  let small(body) = text(8pt, body)
  cetz.canvas(length: 1cm, {
    import cetz.draw: *
    let bx(name, x, y, w, fill, body, h: 1.15, stroke: 0.6pt) = {
      rect((x - w / 2, y - h / 2), (x + w / 2, y + h / 2), radius: 2pt, fill: fill, stroke: stroke, name: name)
      content((x, y), align(center, body))
    }
    let arrow(..pts) = line(..pts, stroke: 0.6pt, mark: (end: "stealth", fill: black, scale: 0.55))
    let note(pos, anchor, body) = content(pos, anchor: anchor, padding: 3pt, small(emph(body)))

    bx("q1", 2.4, 0, 4.2, white, [Can the old model \ still embed queries?], stroke: 1pt)
    bx("stay", 10.6, 0, 10.6, old, [Stay on the old model \ #small[no translated index was better; an upgrade is a full re-embed]])
    bx("q2", 2.4, -1.95, 4.2, white, [Are the texts and a \ new model at hand?], stroke: 1pt)
    bx("own", 7.75, -1.95, 4.9, pub, [Pairs from the collection \ #small[embed a few thousand passages anew]])
    bx("public", 2.4, -3.9, 4.2, pub, [Published anchors \ #small[of the old and of the new space]])
    bx("map", 7.75, -3.9, 4.9, white, [Orthogonal map, centred \ #small[fit it, translate the index once]])
    bx("serve", 13.3, -3.9, 5.2, new, [Translated index \ #small[searchable at once, alone or with BM25]])
    bx("rebuild", 13.3, -1.95, 5.2, new, [Re-embed beside it \ #small[when the texts are at hand; switch \ when complete, do not mix]])

    arrow("q1.east", "stay.west")
    note((4.9, 0), "south", [yes])
    arrow("q1.south", "q2.north")
    note((2.4, -0.97), "west", [no])
    arrow("q2.east", "own.west")
    note((4.9, -1.95), "south", [yes])
    arrow("q2.south", "public.north")
    note((2.4, -2.92), "west", [no])
    arrow("own.south", "map.north")
    arrow("public.east", "map.west")
    arrow("map.east", "serve.west")
    arrow("serve.north", "rebuild.south")
  })
}

// Why a map can translate: the same anchor texts as points in two spaces.
#let intuition = {
  set text(9pt)
  set par(justify: false, leading: 0.45em)
  let small(body) = text(8pt, body)
  cetz.canvas(length: 1cm, {
    import cetz.draw: *
    let anchors = ((-1.25, 0.95), (0.25, 1.35), (1.45, 0.25), (0.3, -0.5), (-0.85, -1.15))
    let wobble = ((0.07, -0.05), (-0.06, 0.06), (0.05, 0.07), (-0.07, -0.04), (0.06, 0.05))
    let doc = (0.75, 0.55)
    let turn(p, deg) = (p.at(0) * calc.cos(deg * 1deg) - p.at(1) * calc.sin(deg * 1deg), p.at(0) * calc.sin(deg * 1deg) + p.at(1) * calc.cos(deg * 1deg))
    let at(c, p) = (c.at(0) + p.at(0), c.at(1) + p.at(1))
    let ca = (3.3, 0)
    let cb = (12.6, 0)
    let dark = rgb("#1a4f8b")
    let panel(c, fill, title) = {
      rect((c.at(0) - 2.9, -2.05), (c.at(0) + 2.9, 2.05), radius: 3pt, fill: fill, stroke: 0.6pt)
      content((c.at(0), 2.4), strong(title))
    }
    panel(ca, old, [Space of the old model])
    panel(cb, new, [Space of the new model])
    for (i, p) in anchors.enumerate() {
      let a = at(ca, p)
      let b = at(cb, at(turn(p, 62), wobble.at(i)))
      circle(a, radius: 0.085, fill: black, stroke: none)
      content(at(a, (0.24, 0.2)), small[#(i + 1)])
      circle(b, radius: 0.085, fill: black, stroke: none)
      content(at(b, (0.24, 0.2)), small[#(i + 1)])
    }
    // a stored document: its old vector, its translated vector and the vector the new model would write
    circle(at(ca, doc), radius: 0.11, fill: white, stroke: 1.1pt + dark)
    let mapped = at(cb, turn(doc, 62))
    let native = at(mapped, (0.3, -0.24))
    circle(mapped, radius: 0.11, fill: white, stroke: 1.1pt + dark)
    rect(at(native, (-0.09, -0.09)), at(native, (0.09, 0.09)), fill: dark, stroke: none)
    line((6.45, 0.25), (9.45, 0.25), stroke: 0.6pt, mark: (end: "stealth", fill: black, scale: 0.55))
    content((7.95, 0.25), anchor: "south", padding: 3pt, small[fitted on the anchors:])
    content((7.95, 0.2), anchor: "north", padding: 3pt, small[a turn and a shift])
    // key
    let ky = -2.65
    circle((1.0, ky), radius: 0.085, fill: black, stroke: none)
    content((1.25, ky), anchor: "west", small[an anchor text; the same five texts in both spaces])
    circle((1.0, ky - 0.52), radius: 0.11, fill: white, stroke: 1.1pt + dark)
    content((1.25, ky - 0.52), anchor: "west", small[a stored document: on the left its old vector, on the right the same vector after translation])
    rect((1.0 - 0.09, ky - 1.04 - 0.09), (1.0 + 0.09, ky - 1.04 + 0.09), fill: dark, stroke: none)
    content((1.25, ky - 1.04), anchor: "west", small[the vector the new model would write for that document])
  })
}

// ---------------------------------------------------------------- explanatory drawings
#let _draw(body) = {
  set text(9pt)
  set par(justify: false, leading: 0.45em)
  cetz.canvas(length: 1cm, body)
}
#let _s(body) = text(8pt, body)

// The problem: what a change of model does to a stored index.
#let problem = _draw({
  import cetz.draw: *
  let bx(x, y, w, fill, body) = {
    rect((x - w / 2, y - 0.55), (x + w / 2, y + 0.55), radius: 2pt, fill: fill, stroke: 0.6pt)
    content((x, y), align(center, body))
  }
  let row(y, label, qfill, qtext, verdict, ok) = {
    content((0, y), anchor: "west", strong(label))
    bx(4.5, y, 3.4, old, [Stored index \ #_s[vectors of model A]])
    bx(9.3, y, 3.4, qfill, qtext)
    line((6.2, y), (7.6, y), stroke: if ok { 0.6pt } else { (paint: black, thickness: 0.6pt, dash: "dashed") })
    content((6.9, y), anchor: "south", padding: 3pt, _s[compare])
    if not ok { content((6.9, y), text(11pt, weight: "bold")[×]) }
    content((11.3, y), anchor: "west", box(width: 4.5cm, _s(verdict)))
  }
  row(0, [Today], old, [Query \ #_s[embedded by model A]], [Same space: the nearest stored vectors are the passages that answer the query.], true)
  row(-1.5, [Model replaced], new, [Query \ #_s[embedded by model B]], [Different spaces: the comparison means nothing. Every document has to be embedded again.], false)
})

// The two documents of the standard and what they hold. Field names as in the two JSON Schemas.
#let documents = _draw({
  import cetz.draw: *
  let card(x, w, title, sub, groups) = {
    let h = 6.75
    rect((x, -h), (x + w, 0), radius: 3pt, fill: white, stroke: 0.7pt)
    rect((x, -0.95), (x + w, 0), radius: (north-west: 3pt, north-east: 3pt), fill: pub, stroke: 0.7pt)
    content((x + 0.25, -0.33), anchor: "west", strong(title))
    content((x + 0.25, -0.7), anchor: "west", _s(sub))
    let y = -1.25
    for (name, fields) in groups {
      content((x + 0.25, y), anchor: "north-west", box(width: (w - 0.5) * 1cm, [#_s(strong(name)) \ #text(7.5pt, fields)]))
      y -= 1.1
    }
  }
  card(0, 7.4, [Embedding Space Card], [one per space, published by the provider], (
    ([Identity], [`spec_version` · `space_id` · `model`: publisher, name, revision]),
    ([Geometry], [`dimensions` · `native_dimensions` · `truncation` · `similarity` · `normalized`]),
    ([Input], [`input`: `roles` with prefix or task type · `max_tokens` · `overflow`]),
    ([Compatibility], [`compatible_with`: spaces guaranteed to be directly comparable]),
    ([Anchors], [`anchors`: `corpus_id` · `corpus_sha256` · `role` · `url`]),
  ))
  card(8.5, 7.4, [Adapter Manifest], [one per map, published by whoever fitted it], (
    ([Spaces], [`source_space` · `target_space`, each the `space_id` of a card]),
    ([Map], [`map`: `type` · `weights_url` · `weights_sha256` · `centred`]),
    ([Fit], [`fit`: `corpus_id` · `corpus_sha256` · `pairs` · roles]),
    ([Measurement, at least one], [`evaluation`: `benchmark` · `mode` · `metric` · `bridged`]),
    ([Reference of a full re-embed], [`native_target` for index translation · `native_source` for query translation]),
  ))
  line((8.5, -1.75), (7.4, -1.75), stroke: 0.6pt, mark: (end: "stealth", fill: black, scale: 0.55))
})

// Ways to serve: which model wrote the stored vectors and the query, and in which space they meet.
#let serving = _draw({
  import cetz.draw: *
  let cell(x, y, w, fill, body) = {
    rect((x, y - 0.4), (x + w, y + 0.4), radius: 2pt, fill: fill, stroke: 0.6pt)
    content((x + w / 2, y), _s(body))
  }
  content((3.0, 0.9), anchor: "west", strong[Stored vectors])
  content((7.7, 0.9), anchor: "west", strong[Query])
  content((11.9, 0.9), anchor: "west", strong[What it is])
  let rows = (
    ([Stay], (old, [written by A]), (old, [written by A]), [the old model as it is; the reference for staying]),
    ([Index translation], (new, [written by A, mapped to B]), (new, [written by B]), [one pass over the stored vectors]),
    ([Query translation], (old, [written by A]), (old, [written by B, mapped to A]), [one extra step for every query]),
    ([Full re-embed], (new, [written by B]), (new, [written by B]), [everything embedded again; counts as 100%]),
  )
  for (i, (name, d, q, what)) in rows.enumerate() {
    let y = -i * 1.0
    content((0, y), anchor: "west", strong(name))
    cell(3.0, y, 4.3, d.at(0), d.at(1))
    cell(7.7, y, 3.8, q.at(0), q.at(1))
    content((11.9, y), anchor: "west", box(width: 4.0cm, _s(what)))
  }
  let y = -4.0
  content((0, y), anchor: "west", strong[Mixed index])
  cell(3.0, y, 2.1, new, [by A, mapped])
  cell(5.2, y, 2.1, new, [written by B])
  cell(7.7, y, 3.8, new, [written by B])
  content((11.9, y), anchor: "west", box(width: 4.0cm, _s[the state during a re-embed in place]))
  let y = -5.0
  content((0, y), anchor: "west", strong[Lexical search])
  cell(3.0, y, 4.3, pub, [the texts, indexed by BM25])
  cell(7.7, y, 3.8, pub, [the words of the query])
  content((11.9, y), anchor: "west", box(width: 4.0cm, _s[needs no model; can be fused with any row above]))
})

// What the experiments vary: the measured combinations of the open pairs, testbed by testbed.
#let design(wiki, miracl, archive, total) = _draw({
  import cetz.draw: *
  let bx(x, w, y, fill, body) = {
    rect((x, y - 0.4), (x + w, y + 0.4), radius: 2pt, fill: fill, stroke: 0.6pt)
    content((x + w / 2, y), body)
  }
  content((2.5, 0.85), anchor: "west", strong[In-domain anchors])
  content((8.2, 0.85), anchor: "west", strong[External anchors])
  content((13.9, 0.85), anchor: "west", strong[Combinations])
  let rows = (
    ([Wiki-de], [20 × 2 × 16 = 640], [20 × 2 × 14 = 560], wiki),
    ([MIRACL-de], [20 × 2 × 16 = 640], none, miracl),
    ([Archive], [20 × 2 × 13 = 520], [20 × 2 × 14 = 560], archive),
  )
  for (i, (name, own, ext, sum)) in rows.enumerate() {
    let y = -i * 1.0
    content((0, y), anchor: "west", strong(name))
    bx(2.5, 5.0, y, pub, own)
    if ext != none {
      content((7.85, y), [+])
      bx(8.2, 5.0, y, pub, ext)
    } else {
      content((10.7, y), _s[none])
    }
    content((13.55, y), [=])
    bx(13.9, 2.0, y, white, strong(sum))
  }
  bx(13.9, 2.0, -3.1, new, strong(total))
  content((13.55, -3.1), anchor: "east", [in all])
  content((0, -4.05), anchor: "north-west", box(width: 15.9cm, _s[Each product reads: 20 ordered pairs of the five open models × 2 modes (index and query translation) × the settings of map and anchor budget. The settings are the orthogonal map and ridge regression at each of seven budgets from 100 to 20,000 pairs (six on the Archive, whose own anchors end at 10,000) and, for anchors from the collection, the residual network at two budgets (one on the Archive). On top of these come two commercial source spaces, a weak old model, anchors in the query role, uncentred maps, five further draws of the anchors, mixed indexes and fusion with BM25.]))
})

// How the private testbed was cut from the production index.
#let funnel(anchors, searched, queries) = _draw({
  import cetz.draw: *
  let stage(x, w, h, fill, big, sub) = {
    rect((x, -h / 2), (x + w, h / 2), radius: 2pt, fill: fill, stroke: 0.6pt)
    content((x + w / 2, 0.18), text(11pt, weight: "bold", big))
    content((x + w / 2, -0.25), align(center, _s(sub)))
  }
  let arrow(a, b, note) = {
    line((a, 0), (b, 0), stroke: 0.6pt, mark: (end: "stealth", fill: black, scale: 0.55))
    content(((a + b) / 2, 0.05), anchor: "south", padding: 2pt, align(center, text(7.5pt, note)))
  }
  stage(0, 2.6, 2.6, old, [27,809], [passages in the \ production index])
  arrow(2.6, 4.6, [no vector, too \ short, exact copy \ −904])
  stage(4.6, 2.4, 2.5, old, [26,905], [passages])
  arrow(7.0, 8.9, [near-duplicates \ −5,395])
  stage(8.9, 2.4, 2.0, old, [21,510], [passages from \ 4,932 documents])
  line((11.3, 0.45), (12.6, 1.0), stroke: 0.6pt, mark: (end: "stealth", fill: black, scale: 0.55))
  line((11.3, -0.45), (12.6, -1.0), stroke: 0.6pt, mark: (end: "stealth", fill: black, scale: 0.55))
  rect((12.6, 0.35), (15.9, 1.65), radius: 2pt, fill: pub, stroke: 0.6pt)
  content((14.25, 1.18), text(11pt, weight: "bold", anchors))
  content((14.25, 0.75), _s[anchors, whole documents])
  rect((12.6, -1.65), (15.9, -0.35), radius: 2pt, fill: new, stroke: 0.6pt)
  content((14.25, -0.82), text(11pt, weight: "bold", searched))
  content((14.25, -1.25), _s[searched, with #queries questions])
})

// What three kinds of map do to the shape of a space. A drawing, not a measurement.
#let shapes = _draw({
  import cetz.draw: *
  let pts = ((-0.9, -0.6), (0.9, -0.6), (0.9, 0.6), (-0.9, 0.6), (0.0, 0.0), (0.45, -0.3))
  let turn(p, deg) = (p.at(0) * calc.cos(deg * 1deg) - p.at(1) * calc.sin(deg * 1deg), p.at(0) * calc.sin(deg * 1deg) + p.at(1) * calc.cos(deg * 1deg))
  let dark = rgb("#1a4f8b")
  let panel(cx, title, note, f, shift) = {
    rect((cx - 1.85, -1.75), (cx + 1.85, 1.75), radius: 3pt, fill: white, stroke: 0.6pt)
    content((cx, 2.1), strong(title))
    let target = pts.map(p => { let q = turn(p, 35); (cx + q.at(0), q.at(1)) })
    line(..target.slice(0, 4), close: true, stroke: (paint: luma(150), thickness: 0.6pt, dash: "dashed"))
    for q in target { circle(q, radius: 0.085, fill: luma(175), stroke: none) }
    let mapped = pts.map(p => { let q = f(p); (cx + q.at(0) + shift.at(0), q.at(1) + shift.at(1)) })
    line(..mapped.slice(0, 4), close: true, stroke: 0.8pt + dark)
    for q in mapped { circle(q, radius: 0.06, fill: dark, stroke: none) }
    content((cx, -2.1), anchor: "north", box(width: 3.9cm, align(center, _s(note))))
  }
  panel(2.0, [Rotation, centred], [The shape is kept and lands on the target.], p => turn(p, 35), (0, 0))
  panel(7.95, [Rotation, not centred], [The shape is kept but lands beside the target.], p => turn(p, 35), (0.55, -0.45))
  panel(13.9, [Ridge (least squares)], [Closer on average, but the shape is bent: neighbours change.], p => { let q = turn(p, 35); (q.at(0) * 0.62 + 0.25 * q.at(1), q.at(1) * 0.8) }, (0, 0))
  circle((4.6, -3.25), radius: 0.085, fill: luma(175), stroke: none)
  content((4.8, -3.25), anchor: "west", _s[where the new model puts the texts])
  circle((10.0, -3.25), radius: 0.06, fill: dark, stroke: none)
  content((10.2, -3.25), anchor: "west", _s[the mapped vectors])
})

// The direction of a map against the mode it serves in.
#let direction = _draw({
  import cetz.draw: *
  let sp(x, y, fill, body) = {
    rect((x, y - 0.33), (x + 1.5, y + 0.33), radius: 2pt, fill: fill, stroke: 0.6pt)
    content((x + 0.75, y), _s(body))
  }
  let heads = ((0, [Mode]), (3.1, [The map reads and writes]), (7.3, [Stored index]), (10.3, [Query]), (12.9, [In the manifest]))
  for (x, h) in heads { content((x, 0.85), anchor: "west", strong(h)) }
  let row(y, name, a, b, index, query, re, stay) = {
    content((0, y), anchor: "west", strong(name))
    sp(3.1, y, a.at(0), a.at(1))
    line((4.7, y), (5.3, y), stroke: 0.6pt, mark: (end: "stealth", fill: black, scale: 0.55))
    sp(5.4, y, b.at(0), b.at(1))
    content((7.3, y), anchor: "west", box(width: 2.8cm, _s(index)))
    content((10.3, y), anchor: "west", box(width: 2.4cm, _s(query)))
    content((12.9, y + 0.2), anchor: "west", _s[re-embed: #raw(re)])
    content((12.9, y - 0.2), anchor: "west", _s[stay: #raw(stay)])
  }
  row(0, [Index translation], (old, [A, old]), (new, [B, new]), [mapped once, then lives in B], [from model B, as it is], "native_target", "native_source")
  row(-1.15, [Query translation], (new, [B, new]), (old, [A, old]), [stays in A], [from model B, mapped to A], "native_source", "native_target")
})

// What the three similarity measures compare. A drawing.
#let measures = _draw({
  import cetz.draw: *
  let dark = rgb("#1a4f8b")
  let title(cx, t) = content((cx, 2.15), strong(t))
  let note(cx, t) = content((cx, -1.95), anchor: "north", box(width: 4.6cm, align(center, _s(t))))
  // (a) neighbour overlap
  title(2.5, [Neighbour overlap])
  for (cx, label, mine) in ((1.25, [space A], (0, 1, 2, 3, 4)), (3.75, [space B], (0, 1, 2, 5, 6))) {
    circle((cx, 0.1), radius: 1.05, fill: white, stroke: (paint: luma(150), thickness: 0.6pt))
    content((cx, 1.45), _s(label))
    circle((cx, 0.1), radius: 0.09, fill: black, stroke: none)
    for (i, k) in mine.enumerate() {
      let ang = (i * 72 + 20) * 1deg
      let q = (cx + 0.68 * calc.cos(ang), 0.1 + 0.68 * calc.sin(ang))
      circle(q, radius: 0.16, fill: if k < 3 { dark } else { white }, stroke: 0.7pt + dark)
      content(q, text(6.5pt, fill: if k < 3 { white } else { black })[#(k + 1)])
    }
  }
  note(2.5, [One anchor and its nearest anchors in each space. Three of five are the same: an overlap of 60%.])
  // (b) RSA
  title(7.95, [RSA])
  let a = (9, 6, 3, 2, 6, 9, 5, 3, 3, 5, 9, 7, 2, 3, 7, 9)
  let b = (9, 7, 2, 3, 7, 9, 4, 3, 2, 4, 9, 6, 3, 3, 6, 9)
  for (x0, m, label) in ((6.2, a, [cosines in A]), (8.5, b, [cosines in B])) {
    content((x0 + 0.6, 1.45), _s(label))
    for i in range(4) { for j in range(4) {
      rect((x0 + j * 0.3, 0.75 - i * 0.3), (x0 + j * 0.3 + 0.28, 0.75 - i * 0.3 + 0.28), fill: luma(255 - m.at(i * 4 + j) * 22), stroke: none)
    } }
  }
  content((7.95, 0.45), text(11pt)[↔])
  note(7.95, [Every pair of anchors has a cosine in each space. RSA is the rank correlation of the two tables.])
  // (c) CKA
  title(13.4, [Linear CKA])
  let cloud = ((-0.55, -0.3), (-0.2, 0.35), (0.25, -0.1), (0.6, 0.4), (0.1, -0.5), (-0.5, 0.25), (0.5, -0.35))
  let turn(p, deg) = (p.at(0) * calc.cos(deg * 1deg) - p.at(1) * calc.sin(deg * 1deg), p.at(0) * calc.sin(deg * 1deg) + p.at(1) * calc.cos(deg * 1deg))
  for (cx, deg, label) in ((12.2, 0, [space A]), (14.6, 70, [space B])) {
    content((cx, 1.45), _s(label))
    for q in cloud { let r = turn(q, deg); circle((cx + r.at(0), 0.25 + r.at(1)), radius: 0.07, fill: dark, stroke: none) }
  }
  content((13.4, 0.25), text(11pt)[↻])
  note(13.4, [Compares the two clouds as wholes. A turned copy scores 1; the more the shapes differ, the lower.])
})

// How reciprocal rank fusion joins a dense and a lexical ranking.
#let fusion = _draw({
  import cetz.draw: *
  let list(x, title, items, fill) = {
    content((x + 1.3, 0.8), strong(title))
    for (i, it) in items.enumerate() {
      let y = -i * 0.62
      rect((x, y - 0.25), (x + 2.6, y + 0.25), radius: 2pt, fill: fill, stroke: 0.6pt)
      content((x + 0.3, y), _s[#(i + 1).])
      content((x + 1.0, y), strong(it.at(0)))
      content((x + 2.0, y), _s(it.at(1)))
    }
  }
  list(0, [Dense ranking], (("C", [1/61]), ("A", [1/62]), ("D", [1/63]), ("B", [1/64]), ("E", [1/65])), new)
  list(3.6, [BM25 ranking], (("A", [1/61]), ("B", [1/62]), ("C", [1/63]), ("F", [1/64]), ("D", [1/65])), pub)
  line((6.5, -1.24), (8.0, -1.24), stroke: 0.6pt, mark: (end: "stealth", fill: black, scale: 0.55))
  content((7.25, -1.24), anchor: "south", padding: 3pt, _s[add the scores])
  list(8.3, [Fused], (("A", [0.0325]), ("C", [0.0323]), ("B", [0.0318]), ("D", [0.0313]), ("F", [0.0156])), white)
  content((11.4, -0.3), anchor: "north-west", box(width: 4.5cm, _s[Each ranking gives a passage the score 1/(60 + rank). A passage found by both rises; one found by a single ranking falls behind. With a weight #emph[w] for the dense ranking its scores are multiplied by #emph[w] and the lexical ones by 1 − #emph[w].]))
})

// Which vectors were at hand for which space.
#let available = _draw({
  import cetz.draw: *
  let dark = rgb("#1a4f8b")
  let cols = ((5.7, [Stored \ documents]), (7.7, [Queries]), (9.7, [In-domain \ anchors]), (11.9, [External \ anchors]))
  for (x, h) in cols { content((x, 0.95), align(center, _s(strong(h)))) }
  content((0, 0.95), anchor: "west", _s(strong[Space]))
  content((3.3, 0.95), anchor: "west", _s(strong[Used on]))
  let rows = (
    ([Five open models], [all three testbeds], (true, true, true, true), none),
    ([MiniLM-L12], [all three testbeds], (true, true, true, true), none),
    ([Cohere v3], [Wiki-de], (true, false, true, true), [no stay reference]),
    ([Gemini-001], [Archive], (true, false, true, false), [no stay reference; \ no test with public anchors]),
  )
  for (i, (name, used, have, note)) in rows.enumerate() {
    let y = -i * 0.8
    content((0, y), anchor: "west", strong(name))
    content((3.3, y), anchor: "west", _s(used))
    for (j, ok) in have.enumerate() {
      circle((cols.at(j).at(0), y), radius: 0.16, fill: if ok { dark } else { white }, stroke: 0.8pt + dark)
    }
    if note != none { content((12.9, y), anchor: "west", box(width: 3.0cm, text(7.5pt, note))) }
  }
  rect((11.55, -2.75), (12.25, -2.05), radius: 3pt, stroke: (paint: rgb("#eb6834"), thickness: 1pt, dash: "dashed"))
  content((11.9, -2.95), anchor: "north", box(width: 5.2cm, align(center, text(7.5pt)[what published anchors would supply])))
})
