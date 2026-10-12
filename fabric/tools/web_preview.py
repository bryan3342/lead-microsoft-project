"""Render the report skeleton as a web page that mirrors what Fabric shows for these files.

    python3 fabric/tools/web_preview.py --open        write fabric/tools/out/dashboard-preview.html and open it
    python3 fabric/tools/web_preview.py --out PATH    write somewhere else

Every visual sits at its exact position and size on the 1280 x 720 page, with the same title, text
and font sizes as the report files. With empty tables, each visual shows Power BI's empty state:
cards read "(Blank)", tables show only column headers, slicers show only their header, charts show
only their title. Two things cannot be reproduced outside Power BI and are marked on the page: the
Azure Maps base map, and the Segoe UI font on machines that lack it.

Standard library only. Reads fabric/workspace directly.
"""
import argparse
import html
import json
import re
import webbrowser
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1] / "workspace"
DEFAULT_OUT = Path(__file__).resolve().parent / "out" / "dashboard-preview.html"
NUMERIC = {"int64", "double", "decimal"}


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def column_types(model_dir: Path) -> dict:
    """{(table, column): dataType} from the model's TMDL files."""
    types = {}
    for f in (model_dir / "definition" / "tables").glob("*.tmdl"):
        text = f.read_text()
        table = re.search(r"^table (\S+)", text, re.M).group(1)
        for col, dtype in re.findall(r"^\tcolumn (\S+)\n\t\tdataType: (\S+)", text, re.M):
            types[(table, col)] = dtype
    return types


def projections(vis: dict) -> dict:
    """{role: [(kind, table, property, displayName)]} from a visual's query."""
    out = {}
    for role, state in vis.get("query", {}).get("queryState", {}).items():
        items = []
        for p in state.get("projections", []):
            kind, ref = next(iter(p["field"].items()))
            items.append((kind, ref["Expression"]["SourceRef"]["Entity"], ref["Property"],
                          p.get("displayName", ref["Property"])))
        out[role] = items
    return out


def title_of(vis: dict):
    props = vis.get("visualContainerObjects", {}).get("title", [{}])[0].get("properties", {})
    if props.get("show", {}).get("expr", {}).get("Literal", {}).get("Value") != "true":
        return None
    return props.get("text", {}).get("expr", {}).get("Literal", {}).get("Value", "").strip("'").replace("''", "'")


def body_html(vis: dict, types: dict) -> str:
    vtype = vis["visualType"]
    roles = projections(vis)
    if vtype == "textbox":
        paras = vis["objects"]["general"][0]["properties"]["paragraphs"]
        out = []
        for p in paras:
            runs = []
            for r in p["textRuns"]:
                st = r.get("textStyle", {})
                css = f"font-size:{esc(st.get('fontSize', '11pt'))};"
                if st.get("fontWeight") == "bold":
                    css += "font-weight:700;"
                runs.append(f'<span style="{css}">{esc(r["value"])}</span>')
            out.append(f'<p class="para">{"".join(runs)}</p>')
        return f'<div class="textbox">{"".join(out)}</div>'
    if vtype == "card":
        label = roles["Values"][0][3]
        return f'<div class="card"><div class="callout">(Blank)</div><div class="catlabel">{esc(label)}</div></div>'
    if vtype == "slicer":
        _, table, col, name = roles["Values"][0]
        if types.get((table, col)) in NUMERIC:
            return (f'<div class="slicer"><div class="slicer-head">{esc(name)}</div>'
                    '<div class="between"><span class="range-box"></span><span class="range-box"></span></div>'
                    '<div class="track"></div></div>')
        return f'<div class="slicer"><div class="slicer-head">{esc(name)}</div></div>'
    if vtype == "tableEx":
        heads = "".join(f"<th>{esc(n)}</th>" for _, _, _, n in roles["Values"])
        return f'<div class="tablewrap"><table><thead><tr>{heads}</tr></thead></table></div>'
    if vtype == "azureMap":
        return '<div class="map"><span>Azure Maps base map draws here in Fabric</span></div>'
    return ""  # charts with no rows show only their title


def visual_html(path: Path, types: dict) -> tuple:
    doc = json.loads(path.read_text())
    pos, vis = doc["position"], doc["visual"]
    title = title_of(vis)
    fields = "; ".join(f"{role}: " + ", ".join(f"{t}[{p}]" for _, t, p, _ in items)
                       for role, items in projections(vis).items())
    tip = f'{vis["visualType"]}' + (f" | {fields}" if fields else "")
    style = (f"left:{pos['x']}px;top:{pos['y']}px;width:{pos['width']}px;height:{pos['height']}px;"
             f"z-index:{int(pos.get('z', 0))}")
    head = f'<div class="vtitle">{esc(title)}</div>' if title else ""
    cls = "visual is-text" if vis["visualType"] == "textbox" else "visual"
    return pos.get("tabOrder", pos.get("z", 0)), (
        f'<div class="{cls}" style="{style}" title="{esc(tip)}">{head}{body_html(vis, types)}</div>')


def report_sections(report: Path):
    meta = json.loads((report / ".platform").read_text())["metadata"]
    pbir = json.loads((report / "definition.pbir").read_text())
    model_dir = WORKSPACE / Path(pbir["datasetReference"]["byPath"]["path"]).name
    types = column_types(model_dir)
    order = json.loads((report / "definition" / "pages" / "pages.json").read_text())["pageOrder"]
    pages = []
    for name in order:
        pdir = report / "definition" / "pages" / name
        page = json.loads((pdir / "page.json").read_text())
        visuals = sorted(visual_html(f, types) for f in (pdir / "visuals").glob("*/visual.json"))
        pages.append((name, page, [v for _, v in visuals]))
    return meta, pages


def model_html() -> str:
    blocks = []
    for sm in sorted(WORKSPACE.glob("*.SemanticModel")):
        meta = json.loads((sm / ".platform").read_text())["metadata"]
        rows = []
        for f in sorted((sm / "definition" / "tables").glob("*.tmdl")):
            text = f.read_text()
            name = re.search(r"^table (\S+)", text, re.M).group(1)
            desc = re.search(r"^/// (.+)$", text, re.M)
            cols = re.findall(r"^\tcolumn (\S+)\n\t\tdataType: (\S+)", text, re.M)
            measures = [m.strip("'") for m in re.findall(r"^\tmeasure ('[^']+'|\S+) =", text, re.M)]
            col_list = "".join(f"<li><code>{esc(c)}</code> <span class=\"dtype\">{esc(t)}</span></li>" for c, t in cols)
            m_list = "".join(f"<li>{esc(m)}</li>" for m in measures) or "<li class=\"none\">None</li>"
            rows.append(
                f'<article class="tbl"><h4><code>{esc(name)}</code></h4>'
                f'<p class="desc">{esc(desc.group(1).removeprefix("PLACEHOLDER. ")) if desc else ""}</p>'
                f'<div class="cols"><div><h5>Columns</h5><ul>{col_list}</ul></div>'
                f'<div><h5>Measures</h5><ul>{m_list}</ul></div></div></article>')
        rel = sm / "definition" / "relationships.tmdl"
        links = ""
        if rel.exists():
            pairs = re.findall(r"fromColumn: (\S+)\n\ttoColumn: (\S+)", rel.read_text())
            items = "".join(f"<li><code>{esc(a)}</code><span class=\"arrow\">many to one</span><code>{esc(b)}</code></li>"
                            for a, b in pairs)
            links = f'<h4 class="links-head">Relationships</h4><ul class="links">{items}</ul>'
        blocks.append(f'<section class="model" id="model-{esc(sm.stem.lower())}"><h3>{esc(meta["displayName"])} '
                      f'semantic model</h3><div class="tbl-grid">{"".join(rows)}</div>{links}</section>')
    return "".join(blocks)


CSS = """
:root {
  /* Layout: Fabric-style report viewer. Pages pane on the left, each 1280x720 page scaled to fit. */
  --chrome: #f3f2f1; --chrome-ink: #252423; --chrome-muted: #605e5c; --line: #e1dfdd;
  --canvas: #ffffff; --wallpaper: #eaeaea; --ink: #252423; --muted: #605e5c; --accent: #117865;
  --map: #dfe7ec; --map-ink: #5d6b75; --flag: #8a5a00; --flag-bg: #fff4ce;
  --ui: "Segoe UI", "Segoe UI Web (West European)", -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, "Cascadia Mono", "SF Mono", Menlo, Consolas, monospace;
  color-scheme: light;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--chrome); color: var(--chrome-ink); font-family: var(--ui); font-size: 14px; }
.shell { padding-block: 16px 40px; padding-inline: 16px; max-width: 1560px; margin: 0 auto; display: grid; gap: 16px; }
header.top { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 16px; }
header.top h1 { font-size: 20px; font-weight: 600; margin: 0; text-wrap: balance; }
header.top .sub { color: var(--chrome-muted); }
.flags { display: flex; flex-wrap: wrap; gap: 8px; }
.flag { background: var(--flag-bg); color: var(--flag); border: 1px solid #f2d27a; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
.report { display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 16px; align-items: start; }
@media (max-width: 760px) { .report { grid-template-columns: minmax(0, 1fr); } }
nav.pages { background: #fff; border: 1px solid var(--line); border-radius: 4px; padding: 8px; position: sticky; top: env(safe-area-inset-top, 0px); }
nav.pages h2 { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--chrome-muted); margin: 4px 8px 8px; font-weight: 600; }
nav.pages a { display: block; padding: 6px 8px; border-radius: 3px; color: var(--chrome-ink); text-decoration: none; }
nav.pages a:hover, nav.pages a:focus-visible { background: var(--chrome); outline: 2px solid transparent; }
nav.pages a:focus-visible { box-shadow: inset 0 0 0 2px var(--accent); }
nav.pages .rpt { font-weight: 600; margin-top: 8px; padding: 6px 8px 2px; font-size: 13px; }
.pages-col { display: grid; gap: 24px; min-width: 0; }
.page-block { display: grid; gap: 8px; min-width: 0; scroll-margin-top: 16px; }
.page-label { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
.page-label h3 { margin: 0; font-size: 15px; font-weight: 600; }
.page-label span { color: var(--chrome-muted); font-size: 12px; font-variant-numeric: tabular-nums; }
.stage { background: var(--wallpaper); padding: 12px; border-radius: 4px; overflow: hidden; }
.fit { position: relative; width: 100%; aspect-ratio: 16 / 9; max-width: 100%; }
.page { position: absolute; left: 0; top: 0; width: 1280px; height: 720px; background: var(--canvas); transform-origin: 0 0; box-shadow: 0 1px 3px rgba(0,0,0,.12); }
.visual { position: absolute; overflow: hidden; background: var(--canvas); color: var(--ink); display: flex; flex-direction: column; padding: 8px; }
.visual:hover { box-shadow: inset 0 0 0 1px #c8c6c4; }
.visual.is-text { background: transparent; }
.vtitle { font-size: 14px; font-weight: 600; line-height: 1.3; color: var(--ink); flex: none; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.textbox { color: var(--ink); line-height: 1.35; }
.para { margin: 0; }
.card { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 0; }
.callout { font-size: 27px; font-weight: 600; line-height: 1.1; }
.catlabel { font-size: 12px; color: var(--muted); margin-top: 2px; text-align: center; }
.slicer { display: grid; gap: 8px; align-content: start; }
.slicer-head { font-size: 12px; font-weight: 600; color: var(--ink); }
.between { display: flex; gap: 8px; }
.range-box { flex: 1; height: 26px; border: 1px solid #c8c6c4; border-radius: 2px; }
.track { height: 3px; background: #c8c6c4; border-radius: 2px; margin: 8px 6px 0; }
.tablewrap { overflow: hidden; margin-top: 6px; }
table { border-collapse: collapse; width: 100%; font-size: 12px; }
th { text-align: left; font-weight: 600; padding: 4px 6px; border-bottom: 1px solid #c8c6c4; white-space: nowrap; color: var(--ink); }
.map { flex: 1; margin-top: 6px; background: var(--map); display: flex; align-items: center; justify-content: center; min-height: 0; border-radius: 2px; }
.map span { color: var(--map-ink); font-size: 12px; background: rgba(255,255,255,.7); padding: 2px 6px; border-radius: 3px; }
.model-wrap { display: grid; gap: 16px; }
.model { background: #fff; border: 1px solid var(--line); border-radius: 4px; padding: 16px; display: grid; gap: 12px; min-width: 0; }
.model h3 { margin: 0; font-size: 16px; font-weight: 600; }
.tbl-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr)); gap: 12px; }
.tbl { border: 1px solid var(--line); border-radius: 4px; padding: 12px; min-width: 0; }
.tbl h4 { margin: 0 0 4px; font-size: 14px; }
.desc { margin: 0 0 8px; color: var(--chrome-muted); font-size: 12px; line-height: 1.4; }
.cols { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 8px; }
.cols h5 { margin: 0 0 4px; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: var(--chrome-muted); font-weight: 600; }
.cols ul, .links { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; font-size: 12px; }
.cols li { overflow-wrap: anywhere; }
.dtype { color: var(--chrome-muted); font-family: var(--mono); font-size: 11px; }
.none { color: var(--chrome-muted); }
code { font-family: var(--mono); font-size: 12px; }
.links-head { margin: 4px 0 0; font-size: 14px; }
.links li { display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: baseline; }
.arrow { color: var(--chrome-muted); font-size: 11px; }
h2.section { font-size: 16px; margin: 8px 0 0; font-weight: 600; }
"""

SCALE_JS = """
(function () {
  function fit() {
    document.querySelectorAll('.fit').forEach(function (box) {
      var page = box.querySelector('.page');
      page.style.transform = 'scale(' + (box.clientWidth / 1280) + ')';
    });
  }
  fit();
  window.addEventListener('resize', fit);
  if (window.ResizeObserver) { new ResizeObserver(fit).observe(document.body); }
})();
"""


def build(fragment: bool) -> str:
    nav, blocks = [], []
    for report in sorted(WORKSPACE.glob("*.Report")):
        meta, pages = report_sections(report)
        nav.append(f'<div class="rpt">{esc(meta["displayName"])}</div>')
        for n, (name, page, visuals) in enumerate(pages, 1):
            anchor = f"{report.stem.lower()}-{n}"
            nav.append(f'<a href="#{anchor}">{esc(page["displayName"])}</a>')
            w, h = page["width"], page["height"]
            blocks.append(
                f'<section class="page-block" id="{anchor}"><div class="page-label">'
                f'<h3>{esc(meta["displayName"])}: {esc(page["displayName"])}</h3>'
                f'<span>page {n} of {len(pages)}, {w} x {h}, {len(visuals)} visuals</span></div>'
                f'<div class="stage"><div class="fit" style="aspect-ratio:{w}/{h}">'
                f'<div class="page" style="width:{w}px;height:{h}px">{"".join(visuals)}</div></div></div></section>')
    nav.append('<div class="rpt">Data model</div>')
    for sm in sorted(WORKSPACE.glob("*.SemanticModel")):
        display = json.loads((sm / ".platform").read_text())["metadata"]["displayName"]
        nav.append(f'<a href="#model-{esc(sm.stem.lower())}">{esc(display)}</a>')
    body = f"""
<div class="shell">
  <header class="top">
    <h1>DAPA Dashboard Skeleton</h1>
    <span class="sub">Every page as Fabric lays it out, with no data loaded. Hover a visual to see its type and bound fields.</span>
  </header>
  <div class="flags">
    <span class="flag">Same positions, sizes, titles, text and empty states as the report files</span>
    <span class="flag">Map backgrounds come from Azure Maps and only draw inside Fabric</span>
    <span class="flag">Fabric uses Segoe UI; this page falls back to your system font if it is missing</span>
  </div>
  <div class="report">
    <nav class="pages" aria-label="Pages"><h2>Pages</h2>{"".join(nav)}</nav>
    <div class="pages-col">{"".join(blocks)}
      <h2 class="section">Semantic models (behind the report, not shown on its pages)</h2>
      <div class="model-wrap">{model_html()}</div>
    </div>
  </div>
</div>
<script>{SCALE_JS}</script>"""
    head = f"<title>DAPA Dashboard Skeleton</title>\n<style>{CSS}</style>"
    if fragment:
        return head + body
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">{head}</head>'
            f"<body>{body}</body></html>\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--open", action="store_true", help="open the page in your browser")
    parser.add_argument("--fragment", action="store_true", help="omit the html/head/body wrapper")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build(args.fragment))
    print(f"wrote {args.out}")
    if args.open:
        webbrowser.open(args.out.resolve().as_uri())


if __name__ == "__main__":
    main()
