// Graphical abstract: the paper in one picture, 1200 × 627 px (1.91 : 1) for social networks and journals.
//   typst compile --root . --ppi 127 paper/graphical-abstract.typ paper/graphical-abstract.png
//   typst compile --root . paper/graphical-abstract.typ paper/graphical-abstract.svg
#import "@preview/cetz:0.5.3"
#import "generated.typ": n
#import "figures.typ": old, new, pub

#let ink = rgb("#1a1a1a")
#let muted = rgb("#5a5a5a")
#let blue = rgb("#2f6fb3")
#let orange = rgb("#d9772b")
#let num(key) = float(n.at(key))

#set document(title: "Publish the Anchors: graphical abstract", author: "Egbal Waldmann")
#set page(width: 24cm, height: 12.54cm, margin: (x: 1.1cm, y: 0.9cm), fill: white)
#set text(font: "New Computer Modern", size: 12pt, fill: ink)
#set par(justify: false, leading: 0.5em)

#grid(columns: (1fr,), rows: (auto, 1fr, auto), gutter: 0pt,
  // Title
  {
    text(26pt, weight: "bold")[Publish the Anchors]
    v(-3mm)
    text(13pt, fill: muted)[What happens to a vector index when the embedding model changes?]
    v(4mm)
  },
  // Body: the idea on the left, the result on the right
  grid(columns: (1.15fr, 1fr), column-gutter: 0.9cm, align: horizon,
    {
      set text(10.5pt)
      cetz.canvas(length: 1cm, {
        import cetz.draw: *
        let bx(name, x, y, w, h, fill, body) = {
          rect((x - w / 2, y - h / 2), (x + w / 2, y + h / 2), radius: 3pt, fill: fill, stroke: 0.7pt, name: name)
          content((x, y), align(center, body))
        }
        let arrow(a, b) = line(a, b, stroke: 0.8pt, mark: (end: "stealth", fill: black, scale: 0.7))
        bx("anchors", 5.5, 2.3, 5.4, 1.15, pub, [*Public anchor texts* \ #text(9pt)[embedded by every model version]])
        bx("old", 1.6, 0, 3.2, 1.3, old, [*Old index* \ #text(9pt)[vectors of model A]])
        bx("map", 5.5, 0, 3.0, 1.3, white, [*Map A → B* \ #text(9pt)[fitted on anchor pairs]])
        bx("new", 9.5, 0, 3.4, 1.3, new, [*Translated index* \ #text(9pt)[searchable by model B]])
        arrow("old.east", "map.west")
        arrow("map.east", "new.west")
        arrow("anchors.south", "map.north")
        content((5.5, -1.45), text(10pt, fill: muted)[No stored document is embedded again.])
      })
    },
    {
      let bar(label, key) = {
        let x = num(key)
        grid(columns: (2.3cm, 1fr), column-gutter: 3mm, align: horizon,
          align(right, text(11pt, label)),
          box(width: 100%, {
            box(width: x * 1%, height: 6.5mm, fill: blue, radius: 1.5pt, inset: (right: 2mm),
              align(right + horizon, text(11pt, fill: white, weight: "bold", n.at(key) + "%")))
          }))
        v(1.6mm)
      }
      text(11pt, fill: muted)[Search quality kept, in % of embedding everything again]
      v(2mm)
      bar("Wiki-de", "wiki.top.procrustes.fwd.mean")
      bar("MIRACL-de", "miracl.top.procrustes.fwd.mean")
      bar("Archive", "archive.top.procrustes.fwd.mean")
      v(2.5mm)
      block(stroke: (left: 2.4pt + orange), inset: (left: 3mm, y: 1mm), text(11.5pt)[
        *Never better than keeping the old model:* \
        none of #n.at("all.beats-stay.of") combinations beat it beyond the noise, not even when the old model is much weaker.
      ])
    },
  ),
  // Footer
  {
    line(length: 100%, stroke: 0.5pt + muted)
    v(-1.5mm)
    text(10pt, fill: muted)[Egbal Waldmann · 5 open models, 2 commercial spaces, 3 German testbeds · doi.org/10.5281/zenodo.24484736]
  },
)
