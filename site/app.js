// Interactive figures of "Publish the Anchors". Reads data.json, written by experiments/site_data.py.
// Conventions as in the paper: source is the old model, target the new one, in both modes; every
// percentage is nDCG@10 relative to a full re-embed with the new model. Orange marks the old model's
// space, blue the new model's.
"use strict";

const BED_LOOK = {
  "wiki-de": { color: "blue", symbol: "circle" },
  "miracl-de": { color: "green", symbol: "square" },
  "archive": { color: "orange", symbol: "triangle" },
};
const MEASURES = {
  knn: "overlap of the ten nearest anchors",
  rsa: "RSA (Spearman)",
  cka: "linear CKA",
  acc1: "held-out anchors nearest to their counterpart",
};
const MODE_LABEL = { index: "index translation", query: "query translation" };

let D;   // data.json
let C;   // colours of the current theme

// ---------------------------------------------------------------- helpers

const $ = (id) => document.getElementById(id);
const pct = (x, digits = 1) => (x == null ? "n/a" : `${(100 * x).toFixed(digits)}%`);
const pts = (x) => `${x >= 0 ? "+" : "−"}${Math.abs(x).toFixed(1)}`;
const f3 = (x) => (x == null ? "n/a" : x.toFixed(3));
const int = (x) => Number(x).toLocaleString("en-US");
const short = (k) => (k >= 1000 ? `${k / 1000}k` : `${k}`);
const name = (m) => D.names[m] || m;
const arrow = (s, t) => `${name(s)} → ${name(t)}`;
const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
const prefix = (bed) => bed.split("-")[0];       // wiki, miracl, archive: the keys of the paper's numbers
const paper = (key) => D.paper[key];

function objects(fields, rows) {
  return rows.map((r) => Object.fromEntries(fields.map((f, i) => [f, r[i]])));
}

function colours() {
  const s = getComputedStyle(document.documentElement);
  const get = (v) => s.getPropertyValue(v).trim();
  const c = {};
  for (const v of ["bg", "surface", "ink", "muted", "faint", "grid", "band", "blue", "orange", "green", "heat-lo", "heat-hi"]) {
    c[v.replace("-l", "L").replace("-h", "H")] = get(`--${v}`);
  }
  c.dark = window.matchMedia("(prefers-color-scheme: dark)").matches && document.documentElement.dataset.theme !== "light"
    || document.documentElement.dataset.theme === "dark";
  c.sans = get("--sans");
  return c;
}

function form(id) {
  const el = $(id);
  const out = {};
  for (const input of el.elements) {
    if (!input.name) continue;
    if (input.type === "radio") { if (input.checked) out[input.name] = input.value; }
    else out[input.name] = input.value;
  }
  return out;
}

// Fill a <select> and keep the current choice if it is still offered.
function options(select, items, preferred) {
  const keep = select.value;
  select.replaceChildren(...items.map(([value, label]) => new Option(label, value)));
  const values = items.map(([v]) => String(v));
  select.value = values.includes(keep) ? keep : values.includes(String(preferred)) ? String(preferred) : values[0];
}

function base(el, extra) {
  const width = Math.max(300, el.clientWidth);
  return {
    width,
    style: { fontSize: width < 520 ? "14px" : "16px", fontFamily: C.sans, background: "transparent", color: C.ink, overflow: "visible" },
    ...extra,
  };
}

function tip(data, pointer, options) {
  return Plot.tip(data, pointer({ fill: C.bg, stroke: C.ink, fontSize: 15, lineHeight: 1.3, ...options }));
}

function draw(el, plot) {
  el.replaceChildren(plot);
}

function legend(el, items) {
  el.replaceChildren(...items.map(({ label, stroke, fill, dash, shape, width = 3 }) => {
    const span = document.createElement("span");
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("width", "34");
    svg.setAttribute("height", "18");
    svg.setAttribute("aria-hidden", "true");
    if (shape === "band") {
      const r = document.createElementNS(ns, "rect");
      Object.entries({ x: 1, y: 3, width: 32, height: 12, fill }).forEach(([k, v]) => r.setAttribute(k, v));
      svg.append(r);
    } else if (shape === "dot" || shape === "ring" || shape === "square" || shape === "triangle") {
      const sym = d3.symbol().type({ dot: d3.symbolCircle, ring: d3.symbolCircle, square: d3.symbolSquare, triangle: d3.symbolTriangle }[shape]).size(110)();
      const p = document.createElementNS(ns, "path");
      p.setAttribute("d", sym);
      p.setAttribute("transform", "translate(17,9)");
      p.setAttribute("fill", shape === "ring" ? C.bg : fill || stroke);
      p.setAttribute("stroke", stroke || fill);
      p.setAttribute("stroke-width", "2");
      svg.append(p);
    } else if (shape === "gradient") {
      const id = `g${Math.random().toString(36).slice(2)}`;
      svg.setAttribute("width", "120");
      svg.innerHTML = `<defs><linearGradient id="${id}">${fill.map((c, i) => `<stop offset="${(100 * i) / (fill.length - 1)}%" stop-color="${c}"/>`).join("")}</linearGradient></defs>`
        + `<rect x="1" y="3" width="118" height="12" fill="url(#${id})" stroke="${C.muted}" stroke-width="0.5"/>`;
    } else {
      const l = document.createElementNS(ns, "line");
      Object.entries({ x1: 1, x2: 33, y1: 9, y2: 9, stroke, "stroke-width": width }).forEach(([k, v]) => l.setAttribute(k, v));
      if (dash) l.setAttribute("stroke-dasharray", dash);
      svg.append(l);
    }
    span.append(svg, document.createTextNode(label));
    return span;
  }));
}

function table(el, caption, header, rows) {
  const t = document.createElement("table");
  const cap = t.createCaption();
  cap.textContent = caption;
  const head = t.createTHead().insertRow();
  for (const h of header) {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = h;
    head.append(th);
  }
  const body = t.createTBody();
  for (const r of rows) {
    const tr = body.insertRow();
    r.forEach((v, i) => {
      const cell = i === 0 ? document.createElement("th") : document.createElement("td");
      if (i === 0) cell.scope = "row";
      cell.textContent = v;
      tr.append(cell);
    });
  }
  el.replaceChildren(t);
}

function bedOptions(select, filter = () => true) {
  options(select, Object.entries(D.beds).filter(([k, b]) => filter(k, b)).map(([k, b]) => [k, b.label]), "wiki-de");
}

const ADAPTERS = () => Object.entries(D.adapters).map(([k, v]) => [k, `${v[0].toUpperCase()}${v.slice(1)}`]);

// ---------------------------------------------------------------- data

function prepare() {
  for (const [key, b] of Object.entries(D.beds)) {
    b.key = key;
    b.bridgeRows = objects(b.bridgeFields, b.bridges);
    b.mixedRows = objects(b.mixedFields, b.mixed);
    b.hybridRows = objects(b.hybridFields, b.hybrid);
    b.predictRows = objects(b.predictFields, b.predict).map((r) => ({ ...r, bed: key }));
    b.isOpen = (s) => b.open.includes(s);
    b.kmaxOf = (anchors, adapter) => Math.max(...b.bridgeRows.filter((r) => r.anchors === anchors && r.adapter === adapter).map((r) => r.k));
  }
}

// ---------------------------------------------------------------- 1. quality against the number of anchor pairs

function renderCurve() {
  const el = $("c-curve");
  let f = form("c-curve");
  const b = D.beds[f.bed];
  options(el.elements.source, [...b.open, ...b.closed].map((m) => [m, name(m)]), "bge-m3");
  f = form("c-curve");
  options(el.elements.target, b.open.filter((m) => m !== f.source).map((m) => [m, name(m)]), "me5-large");
  const sets = Object.keys(b.anchorSets).filter((a) => b.bridgeRows.some((r) => r.anchors === a && r.source === f.source));
  options(el.elements.anchors, sets.map((a) => [a, b.anchorSets[a].label === "in-domain" ? "In-domain" : b.anchorSets[a].label]), "in-domain");
  options(el.elements.adapter, ADAPTERS(), D.main);
  f = form("c-curve");

  const rows = b.bridgeRows.filter((r) => r.adapter === f.adapter && r.mode === f.mode && r.anchors === f.anchors);
  const ks = [...new Set(rows.map((r) => r.k))].sort((x, y) => x - y);
  const band = ks.map((k) => {
    const v = rows.filter((r) => r.k === k && b.isOpen(r.source)).map((r) => r.rel);
    return { k, lo: Math.min(...v), hi: Math.max(...v), mean: mean(v), n: v.length };
  }).filter((d) => d.n);
  const at = Object.fromEntries(band.map((d) => [d.k, d]));
  const sel = rows.filter((r) => r.source === f.source && r.target === f.target).sort((x, y) => x.k - y.k);
  const stay = b.stay[`${f.source}|${f.target}`];
  const native = b.native[f.target][0];

  const chart = $("f-curve");
  const marks = [
    Plot.areaY(band, { x: "k", y1: "lo", y2: "hi", fill: C.band }),
    Plot.lineY(band, { x: "k", y: "mean", stroke: C.muted, strokeWidth: 1.5 }),
    Plot.ruleY([1], { stroke: C.ink, strokeWidth: 1.5 }),
    Plot.text([1], { y: (d) => d, frameAnchor: "left", text: () => "full re-embed", dy: -10, fill: C.ink }),
  ];
  if (stay != null) {
    marks.push(
      Plot.ruleY([stay], { stroke: C.orange, strokeWidth: 3, strokeDasharray: "9,6" }),
      Plot.text([stay], { y: (d) => d, x: () => ks[Math.min(1, ks.length - 1)], text: () => `keep ${name(f.source)}`, dy: 16, textAnchor: "start", fill: C.orange, fontWeight: 700, stroke: C.bg, strokeWidth: 4, paintOrder: "stroke" }),
    );
  }
  marks.push(
    Plot.lineY(sel, { x: "k", y: "rel", stroke: C.blue, strokeWidth: 3.5, strokeDasharray: f.mode === "query" ? "8,5" : null }),
    Plot.dot(sel, { x: "k", y: "rel", fill: C.blue, stroke: C.bg, strokeWidth: 1.5, r: 6 }),
    tip(sel, Plot.pointerX, {
      x: "k", y: "rel",
      title: (d) => [`${arrow(d.source, d.target)}, k = ${int(d.k)}`,
        `${pct(d.rel)} of a full re-embed`, `nDCG@10 ${f3(d.ndcg10)} (re-embed ${f3(native)})`,
        `Recall@10 ${f3(d.recall10)}`,
        ...(stay != null ? [`keep the old model: ${pct(stay)}`] : []),
        at[d.k] ? `all ${at[d.k].n} open pairs: ${pct(at[d.k].lo)} to ${pct(at[d.k].hi)}` : ""].filter(Boolean).join("\n"),
    }),
  );
  const desc = sel.length
    ? `${arrow(f.source, f.target)} on ${b.label}, ${D.adapters[f.adapter]} map, ${MODE_LABEL[f.mode]}: from ${pct(sel[0].rel)} at ${int(sel[0].k)} anchor pairs to ${pct(sel.at(-1).rel)} at ${int(sel.at(-1).k)}.`
    : "No measurement for this combination.";
  draw(chart, Plot.plot(base(chart, {
    height: 420, marginLeft: 56, marginRight: 16, marginTop: 24, marginBottom: 48,
    ariaLabel: "Line chart: retrieval quality against the number of anchor pairs", ariaDescription: desc,
    x: { type: "log", label: "anchor pairs k (log scale)", ticks: ks, tickFormat: short, labelAnchor: "center", labelOffset: 40 },
    y: { domain: [0, 1.08], label: "% of full re-embed", tickFormat: (v) => Math.round(100 * v), grid: true, labelAnchor: "top" },
    marks,
  })));
  legend($("l-curve"), [
    { label: arrow(f.source, f.target), stroke: C.blue, dash: f.mode === "query" ? "8,5" : null, width: 3.5 },
    { label: `all ${band.at(-1)?.n ?? 0} pairs of open models: range`, shape: "band", fill: C.band },
    { label: "mean of those pairs", stroke: C.muted, width: 1.5 },
    ...(stay != null ? [{ label: `keep the old model, ${name(f.source)}`, stroke: C.orange, dash: "9,6" }] : []),
  ]);
  const last = sel.at(-1);
  const p = prefix(f.bed);
  let cap = desc;
  if (last) {
    cap += ` The new model's own nDCG@10 is ${f3(native)}; the translated index reaches ${f3(last.ndcg10)}.`;
    cap += stay != null
      ? ` Keeping ${name(f.source)} instead scores ${pct(stay)} of ${name(f.target)}'s nDCG@10.`
      : ` ${name(f.source)} is a commercial space with stored document vectors only, so there is no reference for staying.`;
  }
  if (f.adapter === D.main && f.anchors === "in-domain") {
    const key = `${p}.top.${D.main}.${f.mode === "index" ? "fwd" : "bwd"}`;
    cap += ` Over all pairs of open models, with all ${int(b.kmax)} in-domain anchors, the paper reports a mean of ${paper(`${key}.mean`)}% (range ${paper(`${key}.min`)} to ${paper(`${key}.max`)}%).`;
  }
  $("cap-curve").textContent = cap;
  table($("t-curve"), `${arrow(f.source, f.target)}, ${b.label}, ${D.adapters[f.adapter]} map, ${MODE_LABEL[f.mode]}`,
    ["Anchor pairs k", "% of re-embed", "nDCG@10", "Recall@10", "Lowest pair", "Mean of pairs", "Highest pair"],
    band.map((d) => {
      const r = sel.find((x) => x.k === d.k);
      return [int(d.k), r ? pct(r.rel) : "n/a", r ? f3(r.ndcg10) : "n/a", r ? f3(r.recall10) : "n/a", pct(d.lo), pct(d.mean), pct(d.hi)];
    }));
}

// ---------------------------------------------------------------- 2. pair matrix

function heatRamp() {
  const stops = C.dark
    ? ["#172131", "#1f3a5f", "#2f5f99", "#4f8bd6", "#8cc0ff"]
    : ["#f4f8fe", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"];
  return { stops, at: d3.interpolateRgbBasis(stops) };
}

function renderMatrix() {
  const el = $("c-matrix");
  let f = form("c-matrix");
  const b = D.beds[f.bed];
  options(el.elements.adapter, ADAPTERS(), D.main);
  f = form("c-matrix");
  const ks = [...new Set(b.bridgeRows.filter((r) => r.adapter === f.adapter && r.anchors === "in-domain").map((r) => r.k))].sort((x, y) => x - y);
  if (el.dataset.bed !== f.bed || el.dataset.adapter !== f.adapter) el.elements.k.value = "";
  el.dataset.bed = f.bed;
  el.dataset.adapter = f.adapter;
  options(el.elements.k, ks.map((k) => [k, int(k)]), ks.at(-1));
  f = form("c-matrix");
  const k = Number(f.k);
  const lo = 0.6, hi = 1.0;
  const ramp = heatRamp();
  const sources = [...b.closed, ...b.open];
  const cells = b.bridgeRows
    .filter((r) => r.adapter === f.adapter && r.mode === f.mode && r.anchors === "in-domain" && r.k === k)
    .map((r) => {
      const t = (Math.min(Math.max(r.rel, lo), hi) - lo) / (hi - lo);
      const fill = ramp.at(0.06 + 0.9 * t);
      const stay = b.stay[`${r.source}|${r.target}`];
      const beats = stay != null && r.rel >= stay;
      return { ...r, fill, ink: d3.lab(fill).l > 58 ? "#111111" : "#ffffff", stay, beats,
        label: `${Math.round(100 * r.rel)}${beats ? "*" : ""}`, row: name(r.source), col: name(r.target) };
    });
  const chart = $("f-matrix");
  const width = Math.max(300, chart.clientWidth);
  const ml = width < 520 ? 104 : 130;
  const cell = Math.min(110, (width - ml - 10) / b.open.length);
  const desc = `Heat map, ${b.label}, ${D.adapters[f.adapter]} map, ${MODE_LABEL[f.mode]}, k = ${int(k)}: ${cells.length} pairs between ${pct(Math.min(...cells.map((c) => c.rel)), 0)} and ${pct(Math.max(...cells.map((c) => c.rel)), 0)} of a full re-embed.`;
  draw(chart, Plot.plot(base(chart, {
    width: ml + cell * b.open.length + 10, height: 40 + cell * 0.62 * sources.length + 90,
    marginLeft: ml, marginBottom: 90, marginTop: 10, marginRight: 10,
    ariaLabel: "Heat map of every pair of spaces", ariaDescription: desc,
    x: { domain: b.open.map(name), label: "new model (target) →", tickRotate: -35, labelAnchor: "right" },
    y: { domain: sources.map(name), label: "old model (source)", labelAnchor: "top" },
    marks: [
      Plot.cell(cells, { x: "col", y: "row", fill: (d) => d.fill, inset: 1.5, rx: 3 }),
      Plot.text(cells, { x: "col", y: "row", text: "label", fill: (d) => d.ink, fontSize: width < 520 ? 14 : 17, fontWeight: 600 }),
      tip(cells, Plot.pointer, {
        x: "col", y: "row", maxRadius: cell / 2,
        title: (d) => [`${arrow(d.source, d.target)}`, `${pct(d.rel)} of a full re-embed`, `nDCG@10 ${f3(d.ndcg10)}, Recall@10 ${f3(d.recall10)}`,
          d.stay != null ? `keep ${name(d.source)}: ${pct(d.stay)}${d.beats ? " (reached)" : ""}` : "commercial source: no reference for staying"].join("\n"),
      }),
    ],
  })));
  const p = prefix(f.bed);
  let cap = `${desc} An asterisk marks a bridge whose nDCG@10 is at least that of the old model; it is never above it beyond the uncertainty of the query sample.`;
  if (b.closed.length) cap += ` The row of ${b.closed.map(name).join(", ")} is a commercial space with stored document vectors only, which has no reference for staying.`;
  if (f.adapter === D.main && k === b.kmax) {
    const d = f.mode === "index" ? "fwd" : "bwd";
    cap += ` Between the XLM-R encoders ${paper(`${p}.main.${d}.within.mean`)}% survive on average, across families ${paper(`${p}.main.${d}.cross.mean`)}%.`;
  }
  $("cap-matrix").textContent = cap;
  table($("t-matrix"), `% of a full re-embed, ${b.label}, ${D.adapters[f.adapter]} map, ${MODE_LABEL[f.mode]}, k = ${int(k)}`,
    ["Old model ↓ / new model →", ...b.open.map(name)],
    sources.map((s) => [name(s), ...b.open.map((t) => {
      const c = cells.find((x) => x.source === s && x.target === t);
      return c ? `${pct(c.rel)}${c.beats ? " *" : ""}` : "–";
    })]));
}

// ---------------------------------------------------------------- 3. translated index against the old model

function renderStay() {
  const el = $("c-stay");
  let f = form("c-stay");
  options(el.elements.adapter, ADAPTERS(), D.main);
  f = form("c-stay");
  const b = D.beds[f.bed];
  const k = b.kmaxOf("in-domain", f.adapter);
  const rows = b.bridgeRows
    .filter((r) => r.adapter === f.adapter && r.mode === f.mode && r.anchors === "in-domain" && r.k === k && b.isOpen(r.source))
    .map((r) => {
      const diff = 100 * (r.ndcg10 - b.native[r.source][0]);
      const lo = 100 * r.stayLo, hi = 100 * r.stayHi;
      return { ...r, diff, lo, hi, label: arrow(r.source, r.target), status: hi < 0 ? "below" : lo > 0 ? "above" : "tie" };
    })
    .sort((x, y) => y.diff - x.diff);
  const count = (s) => rows.filter((r) => r.status === s).length;
  const chart = $("f-stay");
  const width = Math.max(300, chart.clientWidth);
  const narrow = width < 560;
  const ml = narrow ? 8 : 210;
  const desc = `${b.label}, ${D.adapters[f.adapter]} map, ${MODE_LABEL[f.mode]}, k = ${int(k)}: below the old model beyond the noise in ${count("below")} of ${rows.length} pairs, tied in ${count("tie")}, above in ${count("above")}.`;
  const xmin = Math.min(-5, ...rows.map((r) => r.lo)), xmax = Math.max(2, ...rows.map((r) => r.hi));
  draw(chart, Plot.plot(base(chart, {
    height: (narrow ? 52 : 34) * rows.length + 80, marginLeft: ml, marginRight: 16, marginBottom: 52, marginTop: 28,
    ariaLabel: "Interval plot: translated index minus old model, per pair", ariaDescription: desc,
    x: { domain: [xmin - 0.5, xmax + 0.5], label: narrow ? "translated minus old model, points" : "nDCG@10 of the translated index minus the old model's, in points", grid: true, labelAnchor: "center", labelOffset: 42 },
    y: { domain: rows.map((r) => r.label), label: null, tickSize: 0, axis: narrow ? null : "left" },
    marks: [
      ...(narrow ? [Plot.text(rows, { y: "label", text: "label", frameAnchor: "left", textAnchor: "start", dy: -17, fill: C.ink, stroke: C.bg, strokeWidth: 5, paintOrder: "stroke" })] : []),
      Plot.ruleX([0], { stroke: C.orange, strokeWidth: 3 }),
      Plot.text([0], { x: (d) => d, frameAnchor: "top", text: () => "old model", dy: -18, fill: C.orange, fontWeight: 700, textAnchor: "end", dx: -4 }),
      Plot.ruleY(rows, { y: "label", x1: "lo", x2: "hi", stroke: C.blue, strokeWidth: 3 }),
      Plot.dot(rows, { y: "label", x: "diff", r: 6.5, stroke: C.blue, strokeWidth: 2.5, fill: (d) => (d.status === "tie" ? C.bg : C.blue) }),
      tip(rows, Plot.pointerY, {
        y: "label", x: "diff",
        title: (d) => [d.label, `difference ${pts(d.diff)} points`, `95% interval ${pts(d.lo)} to ${pts(d.hi)}`,
          d.status === "below" ? "below the old model beyond the noise" : d.status === "tie" ? "tied with the old model" : "above the old model",
          `translated ${f3(d.ndcg10)}, old model ${f3(b.native[d.source][0])}`].join("\n"),
      }),
    ],
  })));
  legend($("l-stay"), [
    { label: "below the old model beyond the noise", shape: "dot", fill: C.blue, stroke: C.blue },
    { label: "tied with the old model", shape: "ring", stroke: C.blue },
    { label: "95% interval of the query sample", stroke: C.blue },
    { label: "the old model, kept as it is", stroke: C.orange },
  ]);
  const p = prefix(f.bed);
  $("cap-stay").textContent = `${desc} Over every measured combination of pair, mode, map, anchor set and anchor budget, ${paper(`${p}.beats-stay.ndcg`)} of ${paper(`${p}.beats-stay.of`)} reach the old model's nDCG@10 on ${b.label}, and none is better beyond the noise; over all three testbeds it is ${paper("all.beats-stay.significant")} of ${paper("all.beats-stay.of")}.`;
  table($("t-stay"), `Translated index minus old model, nDCG@10 points, ${b.label}, ${D.adapters[f.adapter]} map, ${MODE_LABEL[f.mode]}, k = ${int(k)}`,
    ["Pair", "Difference", "95% interval", "Verdict"],
    rows.map((r) => [r.label, pts(r.diff), `${pts(r.lo)} to ${pts(r.hi)}`, r.status === "tie" ? "tie" : r.status]));
}

// ---------------------------------------------------------------- 4. mixed index

function renderMixed() {
  const el = $("c-mixed");
  bedOptions(el.elements.bed, (k, b) => b.mixed.length);
  const f = form("c-mixed");
  const b = D.beds[f.bed];
  const m = f.measure;
  const rows = b.mixedRows.map((r) => ({ ...r, pair: arrow(r.source, r.target) }));
  const shares = [...new Set(rows.map((r) => r.share))].sort((x, y) => x - y);
  const means = shares.map((share) => {
    const v = rows.filter((r) => r.share === share).map((r) => r[m]);
    return { share, [m]: mean(v), lo: Math.min(...v), hi: Math.max(...v), pair: `mean over the ${v.length} pairs` };
  });
  const chart = $("f-mixed");
  const quality = m === "rel";
  const p = prefix(f.bed);
  const desc = quality
    ? `${b.label}: with 10, 50 and 90% of the passages translated the index keeps ${means.filter((d) => [0.1, 0.5, 0.9].includes(d.share)).map((d) => pct(d.rel)).join(", ")} of a full re-embed on average; fully translated ${pct(means.at(-1).rel)}.`
    : `${b.label}: in the half-translated index, translated passages fill ${pct(means.find((d) => d.share === 0.5)[m])} of the top ten on average, not half of it.`;
  const marks = [
    Plot.lineY(rows, { x: "share", y: m, z: "pair", stroke: C.faint, strokeWidth: 1.5 }),
    quality ? Plot.ruleY([1], { stroke: C.ink, strokeWidth: 1.5 }) : Plot.line([[0, 0], [1, 1]], { stroke: C.ink, strokeWidth: 1.5, strokeDasharray: "3,4" }),
    Plot.lineY(means, { x: "share", y: m, stroke: C.blue, strokeWidth: 3.5 }),
    Plot.dot(means, { x: "share", y: m, fill: C.blue, stroke: C.bg, strokeWidth: 1.5, r: 6.5 }),
    tip([...means, ...rows], Plot.pointer, {
      x: "share", y: m,
      title: (d) => [d.pair, `${pct(d.share, 0)} of the index translated`,
        quality ? `${pct(d.rel)} of a full re-embed` : `${pct(d[m])} of the top ten are translated passages`,
        d.lo != null ? `pairs: ${pct(d.lo)} to ${pct(d.hi)}` : ""].filter(Boolean).join("\n"),
    }),
  ];
  draw(chart, Plot.plot(base(chart, {
    height: 400, marginLeft: 56, marginRight: 24, marginBottom: 52, marginTop: 24,
    ariaLabel: "Line chart: share of translated passages in the index against the result", ariaDescription: desc,
    x: { domain: [0, 1], ticks: shares, tickFormat: (v) => Math.round(100 * v), label: "translated share of the index, %", labelAnchor: "center", labelOffset: 42 },
    y: { domain: quality ? [Math.min(0.6, Math.floor(10 * Math.min(...rows.map((r) => r.rel))) / 10), 1.03] : [0, 1], label: quality ? "% of full re-embed" : "translated in the top ten, %", tickFormat: (v) => Math.round(100 * v), grid: true, labelAnchor: "top" },
    marks,
  })));
  legend($("l-mixed"), [
    { label: "mean over the pairs", stroke: C.blue, width: 3.5 },
    { label: "single pairs", stroke: C.faint, width: 1.5 },
    quality ? { label: "full re-embed", stroke: C.ink, width: 1.5 } : { label: "share in the top ten equal to share in the index", stroke: C.ink, dash: "3,4", width: 1.5 },
  ]);
  $("cap-mixed").textContent = `${desc} The paper: ${paper(`${p}.x.mixed.90.mean`)}% with nine tenths translated, less than the fully translated index; the weakest pair falls to ${paper(`${p}.x.mixed.90.min`)}%. Both ends of each line are the pure indexes: 0% is the full re-embed, 100% the fully translated index (orthogonal map, all in-domain anchors).`;
  table($("t-mixed"), `Mixed index, ${b.label}, mean over the pairs and range`,
    ["Translated share", quality ? "Mean, % of re-embed" : "Mean, translated in top ten", "Lowest pair", "Highest pair"],
    means.map((d) => [pct(d.share, 0), pct(d[m]), pct(d.lo), pct(d.hi)]));
}

// ---------------------------------------------------------------- 5. similarity of the anchor matrices against the outcome

function renderPredict() {
  const el = $("c-predict");
  const acc = el.elements.measure.value === "acc1";
  for (const r of el.querySelectorAll('input[name="mode"]')) {
    r.disabled = acc && r.value === "query";
    if (acc && r.value === "index") r.checked = true;
  }
  const f = form("c-predict");
  const m = f.measure;
  const rows = Object.values(D.beds).flatMap((b) => b.predictRows).filter((r) => r.mode === f.mode && r[m] != null)
    .map((r) => ({ ...r, pair: arrow(r.source, r.target), bedLabel: D.beds[r.bed].label }));
  const beds = Object.keys(D.beds);
  const chart = $("f-predict");
  const d = f.mode === "index" ? "fwd" : "bwd";
  const rho = beds.map((bed) => {
    const p = prefix(bed);
    const v = m === "acc1" ? paper(`${p}.x.retrieval.in-domain.rho`) : paper(`${p}.predict.${m}.${d}`);
    return `${D.beds[bed].label} ${v ? v.replace("-", "−") : "n/a"}`;
  }).join(", ");
  const desc = `Scatter plot of ${rows.length} pairs of spaces: ${MEASURES[m]} of the two anchor matrices against nDCG@10 of ${MODE_LABEL[f.mode]} in % of a full re-embed. Rank correlation within each testbed: ${rho}.`;
  draw(chart, Plot.plot(base(chart, {
    height: 440, marginLeft: 56, marginRight: 20, marginBottom: 56, marginTop: 24,
    ariaLabel: "Scatter plot: anchor similarity against the outcome", ariaDescription: desc,
    x: { label: m === "acc1" ? `${MEASURES[m]}, %` : MEASURES[m], grid: true, nice: true, labelAnchor: "center", labelOffset: 44,
      ...(m === "acc1" ? { tickFormat: (v) => Math.round(100 * v) } : {}) },
    y: { label: "% of full re-embed", tickFormat: (v) => Math.round(100 * v), grid: true, nice: true, labelAnchor: "top" },
    symbol: { domain: beds, range: beds.map((b) => BED_LOOK[b].symbol) },
    marks: [
      Plot.ruleY([1], { stroke: C.ink, strokeWidth: 1.5 }),
      Plot.dot(rows, { x: m, y: "rel", symbol: "bed", r: 7, fill: (r) => C[BED_LOOK[r.bed].color], stroke: C.bg, strokeWidth: 1.25 }),
      tip(rows, Plot.pointer, {
        x: m, y: "rel",
        title: (r) => [`${r.bedLabel}: ${r.pair}`, `${MEASURES[m]}: ${m === "acc1" ? pct(r[m]) : r[m].toFixed(2)}`, `${pct(r.rel)} of a full re-embed`].join("\n"),
      }),
    ],
  })));
  legend($("l-predict"), beds.map((b) => ({ label: D.beds[b].label, shape: BED_LOOK[b].symbol === "circle" ? "dot" : BED_LOOK[b].symbol, fill: C[BED_LOOK[b].color], stroke: C[BED_LOOK[b].color] })));
  let cap = `${desc} The predictors are computed from the in-domain anchors of each testbed; commercial sources are included where their anchors are at hand.`;
  if (m !== "acc1" && f.mode === "index") cap += ` Pooled over the testbeds the correlation is ${paper(`all.predict.${m}`).replace("-", "−")}: the measures do not transfer from one collection to another.`;
  if (m === "acc1") cap += ` On the two Wikipedia testbeds this accuracy is saturated near 100%, although the outcomes differ by more than ten points.`;
  $("cap-predict").textContent = cap;
  table($("t-predict"), `${MEASURES[m]} against ${MODE_LABEL[f.mode]}`, ["Testbed and pair", MEASURES[m], "% of re-embed"],
    rows.sort((a, b) => a.bed.localeCompare(b.bed) || b.rel - a.rel).map((r) => [`${r.bedLabel}: ${r.pair}`, m === "acc1" ? pct(r[m]) : r[m].toFixed(3), pct(r.rel)]));
}

// ---------------------------------------------------------------- 6. hybrid search

function renderHybrid() {
  const el = $("c-hybrid");
  const f = form("c-hybrid");
  const b = D.beds[f.bed];
  const k = b.kmax;
  const alt = D.alt[f.bed];
  const native = Object.values(b.hybridNative);
  const groups = [
    { group: "Re-embedded index", label: "Re-embedded index", values: native.map((v) => v[0]), colour: C.ink },
    { group: "Re-embedded index", label: "+ BM25, equal weights", values: native.map((v) => v[1]), colour: C.ink },
    { group: "Re-embedded index", label: "+ BM25, tuned weight", values: native.map((v) => v[2]), colour: C.ink },
  ];
  const sets = [["in-domain", k, C.blue, "in-domain anchors"]];
  if (alt && b.hybridRows.some((r) => r.anchors === alt)) {
    sets.push([alt, Math.min(k, b.kmaxOf(alt, D.main)), C.green, `${b.anchorSets[alt].label} anchors`]);
  }
  for (const [anchors, size, colour, what] of sets) {
    const rows = b.hybridRows.filter((r) => r.anchors === anchors && r.k === size);
    groups.push(
      { label: `Translated, ${what}`, values: rows.map((r) => r.bridge), colour, k: size },
      { label: "+ BM25, equal weights", values: rows.map((r) => r.fused), colour, k: size, what },
      { label: "+ BM25, tuned weight", values: rows.map((r) => r.tuned), colour, k: size, what },
    );
  }
  groups.push({ label: "BM25 alone", values: [b.bm25[0]], colour: C.muted });
  // The band scale needs unique keys; the fusion rows repeat their labels under each heading.
  groups.forEach((g, i) => {
    g.key = String(i);
    g.sub = g.label.startsWith("+");
    g.long = g.sub ? `${g.group || `translated, ${g.what}`} ${g.label}` : g.label;
    g.mean = mean(g.values); g.lo = Math.min(...g.values); g.hi = Math.max(...g.values); g.n = g.values.length;
  });
  const label = Object.fromEntries(groups.map((g) => [g.key, g.sub ? `\u00a0\u00a0\u00a0${g.label}` : g.label]));
  const chart = $("f-hybrid");
  const width = Math.max(300, chart.clientWidth);
  const narrow = width < 560;
  const ml = narrow ? 8 : 330;
  const p = prefix(f.bed);
  const bm = b.bm25[0];
  const desc = `${b.label}: BM25 alone ${f3(bm)}; translated index alone (${int(k)} in-domain anchors) ${f3(groups[3].mean)}, fused with BM25 ${f3(groups[4].mean)} with equal weights and ${f3(groups[5].mean)} with a tuned weight; re-embedded index ${f3(groups[0].mean)}.`;
  const xs = groups.flatMap((g) => [g.lo, g.hi]);
  draw(chart, Plot.plot(base(chart, {
    height: (narrow ? 58 : 44) * groups.length + 80, marginLeft: ml, marginRight: 20, marginBottom: 52, marginTop: 16,
    ariaLabel: "Dot plot: dense, lexical and fused retrieval", ariaDescription: desc,
    x: { domain: [Math.min(...xs) - 0.02, Math.max(...xs) + 0.02], label: "nDCG@10", grid: true, labelAnchor: "center", labelOffset: 42 },
    y: { domain: groups.map((g) => g.key), label: null, tickSize: 0, axis: narrow ? null : "left", tickFormat: (d) => label[d] },
    marks: [
      Plot.ruleX([bm], { stroke: C.muted, strokeWidth: 2, strokeDasharray: "10,3,2,3" }),
      ...(narrow ? [Plot.text(groups, { y: "key", text: (g) => label[g.key], frameAnchor: "left", textAnchor: "start", dy: -19, fill: C.ink, stroke: C.bg, strokeWidth: 5, paintOrder: "stroke", fontWeight: (g) => (g.sub ? 400 : 700) })] : []),
      Plot.ruleY(groups, { y: "key", x1: "lo", x2: "hi", stroke: (g) => g.colour, strokeWidth: 3 }),
      Plot.dot(groups, { y: "key", x: "mean", r: 7, fill: (g) => g.colour, stroke: C.bg, strokeWidth: 1.5 }),
      tip(groups, Plot.pointerY, {
        y: "key", x: "mean",
        title: (g) => [g.long, g.n > 1 ? `mean ${f3(g.mean)} over ${g.n} ${g.group ? "models" : "pairs"}` : f3(g.mean),
          g.n > 1 ? `range ${f3(g.lo)} to ${f3(g.hi)}` : "", g.k ? `k = ${int(g.k)}` : "",
          `BM25 alone ${f3(bm)}`].filter(Boolean).join("\n"),
      }),
    ],
  })));
  legend($("l-hybrid"), [
    { label: "re-embedded: the five open models", shape: "dot", fill: C.ink, stroke: C.ink },
    { label: "translated with in-domain anchors", shape: "dot", fill: C.blue, stroke: C.blue },
    ...(sets.length > 1 ? [{ label: "translated with external anchors", shape: "dot", fill: C.green, stroke: C.green }] : []),
    { label: "BM25", stroke: C.muted, dash: "10,3,2,3", width: 2 },
  ]);
  let cap = `${desc} Dots are means, lines the range over the pairs of open models (translated) or over the five models (re-embedded).`;
  if (paper(`${p}.hy.fused-beats-bm25`)) {
    cap += ` With ${paper(`${p}.hybrid.k`)} anchors the fused translated index is above BM25 alone in ${paper(`${p}.hy.fused-beats-bm25`)} of ${paper(`${p}.hy.n`)} pairs, the translated index alone in ${paper(`${p}.hy.bridge-beats-bm25`)}.`;
  }
  $("cap-hybrid").textContent = cap;
  table($("t-hybrid"), `nDCG@10, ${b.label}`, ["Setting", "Mean", "Lowest", "Highest", "n"],
    groups.map((g) => [g.long, f3(g.mean), f3(g.lo), f3(g.hi), String(g.n)]));
}

// ---------------------------------------------------------------- page

const RENDER = { "c-curve": renderCurve, "c-matrix": renderMatrix, "c-stay": renderStay, "c-mixed": renderMixed, "c-predict": renderPredict, "c-hybrid": renderHybrid };

function renderAll() {
  C = colours();
  for (const [id, render] of Object.entries(RENDER)) {
    try { render(); } catch (e) { console.error(id, e); }
  }
}

function hero() {
  const means = Object.keys(D.beds).map((b) => Number(paper(`${prefix(b)}.top.${D.main}.fwd.mean`)));
  $("message").textContent = `A translated index keeps ${Math.round(Math.min(...means))}–${Math.round(Math.max(...means))}% of a full re-embed and is never better than the old model.`;
  const detail = document.createElement("p");
  detail.className = "byline";
  detail.textContent = `Orthogonal map, all in-domain anchors, index translation: ${Object.entries(D.beds).map(([k, b]) => `${b.label} ${paper(`${prefix(k)}.top.${D.main}.fwd.mean`)}%`).join(", ")}. Of ${paper("all.beats-stay.of")} measured combinations, none beat the old model beyond the noise of the query sample.`;
  $("message").after(detail);
}

async function main() {
  try {
    D = await (await fetch("data.json")).json();
  } catch (e) {
    for (const el of document.querySelectorAll(".chart")) el.textContent = "The data could not be loaded. Serve this folder with a static web server, for example: python -m http.server -d site";
    throw e;
  }
  prepare();
  for (const id of ["c-curve", "c-matrix", "c-stay", "c-mixed", "c-hybrid"]) bedOptions($(id).elements.bed);
  hero();
  for (const id of Object.keys(RENDER)) {
    $(id).addEventListener("change", () => { C = colours(); RENDER[id](); });
    $(id).addEventListener("submit", (e) => e.preventDefault());
  }
  renderAll();
  let width = document.body.clientWidth, timer;
  new ResizeObserver(() => {
    if (document.body.clientWidth === width) return;
    width = document.body.clientWidth;
    clearTimeout(timer);
    timer = setTimeout(renderAll, 150);
  }).observe(document.body);
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", renderAll);

  $("copy-bibtex").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("bibtex").textContent);
      $("copy-status").textContent = "Copied.";
    } catch {
      $("copy-status").textContent = "Select the text above and copy it.";
    }
  });
}

main();
