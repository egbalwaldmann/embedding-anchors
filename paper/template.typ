// Layout of the paper: title block, running head, headings, captions and lists.

#let accent = rgb("#1a4f8b")

// A caption with a short form for the lists of figures and tables.
#let in-outline = state("in-outline", false)
#let cap(short, long) = context if in-outline.get() { short } else { long }

// Consistent marks in the running text, explained at the start of the glossary:
// a model or space in a grey box, a testbed and an abbreviation in small capitals,
// a term of the glossary linked to its entry. In the lists and the outline they stay plain.
#let mo(name) = box(fill: luma(234), radius: 1.8pt, inset: (x: 2.2pt), outset: (y: 1.8pt), text(0.93em, name))
#let tb(name) = smallcaps(all: true, name)
#let gl(key, body) = context if in-outline.get() { body } else { link(label("gl-" + key), text(fill: black, body)) }
#let ab(key, body) = context {
  let b = smallcaps(all: true, body)
  if in-outline.get() { b } else { link(label("gl-" + key), text(fill: black, b)) }
}

// A table in the style of the generated ones: three rules, no vertical lines.
#let ruled(columns: (), align: left, header: (), ..cells) = table(
  columns: columns, align: align, stroke: none, inset: (x: 5pt, y: 3.2pt),
  table.hline(stroke: 0.8pt),
  table.header(..header.map(h => strong(h))),
  table.hline(stroke: 0.4pt),
  ..cells,
  table.hline(stroke: 0.8pt),
)

// A sentence lifted out of the text for readers who only leaf through.
#let _pullquote(body) = block(width: 100%, above: 1.5em, below: 1.5em, breakable: false, pad(x: 10mm,
  block(width: 100%, stroke: (left: 2.4pt + accent), inset: (left: 5mm, y: 1.5mm), {
    set par(justify: false, leading: 0.62em)
    text(13pt, style: "italic", body)
  })))
#let pullquote(body) = context if target() == "html" { quote(block: true, body) } else { _pullquote(body) }


// Spoken descriptions for formulas, which an accessible PDF needs: pairs of formula and text.
#let described(formulas, body) = formulas.fold(body, (rest, f) => {
  show math.equation.where(body: f.at(0).body): set math.equation(alt: f.at(1))
  rest
})

#let orcid-mark = box(height: 0.72em, baseline: 0.02em, image("fig/orcid.svg", alt: "ORCID iD"))

#let paper(
  title: "",
  subtitle: none,
  short-title: "",
  authors: (),
  date: none,
  date-of: none,
  note: none,
  abstract: none,
  keywords: (),
  availability: none,
  lead: none,
  front: none,
  body,
) = {
  set document(
    title: title + if subtitle != none { ": " + subtitle },
    author: authors.map(a => a.name),
    keywords: keywords,
    date: date-of,
  )
  set page(
    paper: "a4",
    margin: (x: 25mm, top: 28mm, bottom: 28mm),
    header-ascent: 9mm,
    header: context {
      set text(8.5pt)
      if counter(page).get().first() == 1 {
        note
        h(1fr)
        date
      } else {
        emph(short-title)
        h(1fr)
        authors.map(a => a.name).join(", ")
        v(-0.75em)
        line(length: 100%, stroke: 0.4pt)
      }
    },
    footer: context align(center, text(8.5pt, counter(page).display("1"))),
  )
  set text(font: "New Computer Modern", size: 11pt, lang: "en", region: "GB")
  set par(justify: true)
  show math.equation: set text(weight: 400)

  // Headings.
  set heading(numbering: "1.1")
  show heading: set block(sticky: true)
  show heading.where(level: 1): it => block(above: 1.7em, below: 0.9em, text(14pt, it))
  show heading.where(level: 2): it => block(above: 1.4em, below: 0.8em, text(12pt, it))

  // Links, references and citations.
  show link: set text(fill: accent)
  show ref: set text(fill: accent)
  show cite: set text(fill: accent)

  // Figures and tables: tables carry their caption above; a caption that fits on one line is centred.
  set figure(placement: auto, gap: 0.9em)
  show figure.where(kind: table): set figure.caption(position: top)
  show figure.where(kind: table): set text(size: 0.9em)
  show table: set par(justify: false)
  show table: set text(hyphenate: false)
  show figure.where(kind: raw): set figure(placement: none)
  show figure.caption: set text(size: 0.9em)
  // Every figure, table and listing sits in a thin frame with its caption, so that a reader of the text can skip it and see where the text goes on.
  show figure: it => context if target() == "html" {
    // The text version (HTML, and from it Markdown) keeps captions, tables and listings; a drawing is named by its description.
    let alt = if it.body.func() == image and it.body.alt != none { it.body.alt } else { none }
    let number = if it.numbering != none { it.counter.display(it.numbering) }
    let cap = if it.caption != none { [*#it.supplement #number.* #it.caption.body] }
    if it.kind == image {
      par(cap)
      if alt != none { par(emph([Figure description: #alt])) }
    } else {
      par(cap)
      it.body
    }
  } else {
    let parts = if it.caption == none { (it.body,) } else if it.kind == table { (it.caption, it.body) } else { (it.body, it.caption) }
    let framed = block(width: 100%, stroke: 0.5pt + luma(150), radius: 2pt, outset: (x: 3.5mm), inset: (y: 3mm),
      breakable: it.kind == raw, stack(spacing: it.gap, ..parts.map(p => align(center, p))))
    if it.placement == none { block(above: 1.4em, below: 1.4em, framed) } else { place(it.placement, float: true, clearance: 1.6em, framed) }
  }
  show figure.caption: it => layout(size => context {
    let whole = [*#it.supplement #it.counter.display(it.numbering).* #it.body]
    if measure(whole).width <= size.width {
      align(center, whole)
    } else {
      align(left, par(justify: true, whole))
    }
  })
  show raw.where(block: true): set text(size: 8pt)
  show raw.where(block: true): set par(justify: false, leading: 0.5em)

  // The lists take the short form of a caption.
  show outline: it => {
    in-outline.update(true)
    it
    in-outline.update(false)
  }

  // Title block.
  line(length: 100%, stroke: 1.6pt)
  v(1.5mm)
  align(center, {
    block(text(21pt, weight: "bold", title))
    if subtitle != none {
      v(-1.5mm)
      block(width: 88%, par(justify: false, leading: 0.55em, text(13.5pt, subtitle)))
    }
  })
  v(1.5mm)
  line(length: 100%, stroke: 1.6pt)
  v(3mm)
  align(center, grid(
    columns: (1fr,) * calc.min(3, authors.len()),
    gutter: 1em,
    ..authors.map(a => {
      set par(justify: false, leading: 0.55em)
      strong(a.name)
      if "orcid" in a { h(3pt); link("https://orcid.org/" + a.orcid, orcid-mark) }
      linebreak()
      a.affiliation
      linebreak()
      link("mailto:" + a.email, raw(a.email))
      if "orcid" in a { linebreak(); text(9pt, link("https://orcid.org/" + a.orcid)[ORCID #a.orcid]) }
    }),
  ))
  v(3mm)

  // Abstract, keywords, where to find code and data.
  pad(x: 9mm, {
    set text(10pt)
    align(center, text(11pt, smallcaps[Abstract]))
    v(-1mm)
    abstract
    v(1mm)
    set par(justify: false)
    [*Keywords* #h(0.6em) #keywords.join(" · ")]
    if availability != none {
      parbreak()
      availability
    }
    if lead != none {
      v(2mm)
      block(width: 100%, breakable: false, stroke: (left: 2.4pt + accent), inset: (left: 5mm, y: 1.5mm), {
        set par(justify: false, leading: 0.62em)
        text(12.5pt, style: "italic", lead)
      })
    }
  })
  v(3mm)

  front
  body
}

// Contents and the lists of figures, tables and listings, set small in two columns.
#let _lists(body) = {
  set text(9pt)
  set par(justify: false, leading: 0.5em)
  show outline.entry: set block(spacing: 0.62em)
  show outline.entry.where(level: 1): it => {
    set text(weight: "bold") if it.element.func() == heading
    it
  }
  body
}
#let _part(name) = block(above: 1.1em, below: 0.7em, text(10.5pt, weight: "bold", name))

// Two columns of equal length: the entries before and after the middle one.
#let _halves(target, ..args) = context {
  let all = query(target)
  if all.len() < 2 {
    outline(title: none, target: target, ..args)
  } else {
    let mid = all.at(calc.ceil(all.len() / 2)).location()
    grid(
      columns: (1fr, 1fr),
      column-gutter: 9mm,
      outline(title: none, target: target.before(mid, inclusive: false), ..args),
      outline(title: none, target: target.after(mid), ..args),
    )
  }
}

#let contents-list() = _lists({
  line(length: 100%, stroke: 0.4pt)
  _part[Contents]
  _halves(heading.where(outlined: true), depth: 2, indent: 1.2em)
  v(1mm)
  line(length: 100%, stroke: 0.4pt)
})

#let figure-lists() = _lists({
  line(length: 100%, stroke: 0.4pt)
  _part[List of Figures]
  _halves(figure.where(kind: image))
  _part[List of Tables]
  _halves(figure.where(kind: table))
  _part[List of Listings]
  _halves(figure.where(kind: raw))
  v(1mm)
  line(length: 100%, stroke: 0.4pt)
})

// Everything after this is an appendix, lettered A, B, ...
#let appendix(body) = {
  counter(heading).update(0)
  // "Appendix A. Title", so that the letter is not read as part of the title.
  set heading(numbering: (..n) => "Appendix " + numbering("A", ..n), supplement: none)
  // Every appendix starts on a new page.
  show heading.where(level: 1): it => pagebreak(weak: true) + block(above: 1.7em, below: 0.9em, sticky: true,
    text(14pt, weight: "bold")[#counter(heading).display(it.numbering). #it.body])
  body
}
