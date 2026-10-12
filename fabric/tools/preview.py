"""Preview the dashboard skeleton in a terminal: page wireframes and the data model.

    python3 fabric/tools/preview.py            every page of every report, then the models
    python3 fabric/tools/preview.py pages      page wireframes only
    python3 fabric/tools/preview.py model      tables, measures and relationships only
    python3 fabric/tools/preview.py pages --report DapaPlaybook

Reads the files in fabric/workspace directly. Standard library only.
"""
import argparse
import json
import re
import shutil
import textwrap
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1] / "workspace"
KIND = {"card": "CARD", "slicer": "SLICER", "tableEx": "TABLE", "azureMap": "MAP", "lineChart": "LINE",
        "clusteredColumnChart": "COLUMNS", "clusteredBarChart": "BARS", "textbox": "NOTE"}


def visual_label(v: dict) -> tuple:
    vis = v.get("visual", {})
    kind = KIND.get(vis.get("visualType"), vis.get("visualType", "?").upper())
    if vis.get("visualType") == "textbox":
        paras = vis["objects"]["general"][0]["properties"]["paragraphs"]
        text = " ".join(run["value"] for p in paras for run in p["textRuns"])
    else:
        title = vis.get("visualContainerObjects", {}).get("title", [{}])[0].get("properties", {})
        text = title.get("text", {}).get("expr", {}).get("Literal", {}).get("Value", "").strip("'")
        text = text.removeprefix("PLACEHOLDER: ")
    return kind, text


def render_page(page_dir: Path, cols: int) -> str:
    page = json.loads((page_dir / "page.json").read_text())
    sx = page["width"] / cols
    rows = round(page["height"] / (sx * 2.1))  # terminal cells are about twice as tall as wide
    sy = page["height"] / rows
    grid = [[" "] * cols for _ in range(rows)]
    visuals = [json.loads(f.read_text()) for f in sorted((page_dir / "visuals").glob("*/visual.json"))]
    for v in sorted(visuals, key=lambda v: v["position"].get("z", 0)):
        p = v["position"]
        x0, y0 = int(p["x"] / sx), int(p["y"] / sy)
        x1 = min(cols - 1, max(x0 + 2, int((p["x"] + p["width"]) / sx) - 1))
        y1 = min(rows - 1, max(y0 + 2, int((p["y"] + p["height"]) / sy) - 1))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                edge_x, edge_y = x in (x0, x1), y in (y0, y1)
                grid[y][x] = ("+" if edge_x and edge_y else "-" if edge_y else "|" if edge_x else " ")
        kind, text = visual_label(v)
        width = x1 - x0 - 1
        lines = textwrap.wrap(f"[{kind}] {text}", width) if width > 3 else []
        for i, line in enumerate(lines[: max(0, y1 - y0 - 1)]):
            for j, ch in enumerate(line):
                grid[y0 + 1 + i][x0 + 1 + j] = ch
    return "\n".join("".join(r).rstrip() for r in grid)


def pages(report_filter: str, cols: int):
    for report in sorted(WORKSPACE.glob("*.Report")):
        if report_filter and report_filter.lower() not in report.name.lower():
            continue
        meta = json.loads((report / ".platform").read_text())["metadata"]
        order = json.loads((report / "definition" / "pages" / "pages.json").read_text())["pageOrder"]
        for n, name in enumerate(order, 1):
            page_dir = report / "definition" / "pages" / name
            title = json.loads((page_dir / "page.json").read_text())["displayName"]
            print(f"\n{meta['displayName']}  |  page {n} of {len(order)}: {title}")
            print(render_page(page_dir, cols))


def model():
    for sm in sorted(WORKSPACE.glob("*.SemanticModel")):
        meta = json.loads((sm / ".platform").read_text())["metadata"]
        print(f"\n{meta['displayName']} model")
        for f in sorted((sm / "definition" / "tables").glob("*.tmdl")):
            text = f.read_text()
            name = re.search(r"^table (\S+)", text, re.M).group(1)
            desc = re.search(r"^/// (.+)$", text, re.M)
            columns = re.findall(r"^\tcolumn (\S+)", text, re.M)
            measures = [m.strip("'") for m in re.findall(r"^\tmeasure ('[^']+'|\S+) =", text, re.M)]
            print(f"  {name}  ({len(columns)} columns)")
            if desc:
                print(f"      {desc.group(1).removeprefix('PLACEHOLDER. ')}")
            print("      columns:  " + ", ".join(columns))
            if measures:
                print("      measures: " + ", ".join(measures))
        rel = sm / "definition" / "relationships.tmdl"
        if rel.exists():
            print("  links (many -> one):")
            for frm, to in re.findall(r"fromColumn: (\S+)\n\ttoColumn: (\S+)", rel.read_text()):
                print(f"      {frm}  ->  {to}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", nargs="?", choices=["all", "pages", "model"], default="all")
    parser.add_argument("--report", default="", help="only reports whose folder name contains this text")
    parser.add_argument("--width", type=int, default=min(160, shutil.get_terminal_size((120, 40)).columns))
    args = parser.parse_args()
    if args.what in ("all", "pages"):
        pages(args.report, max(60, args.width))
    if args.what in ("all", "model"):
        model()


if __name__ == "__main__":
    main()
