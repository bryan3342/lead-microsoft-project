"""Offline checks for the Fabric workspace skeleton.

Run from the repo root: pytest fabric/tests
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

FABRIC = Path(__file__).resolve().parents[1]
WORKSPACE = FABRIC / "workspace"
NOTEBOOK = WORKSPACE / "CreateTables.Notebook" / "notebook-content.ipynb"
PROTECTED = {"race", "ethnicity", "religion", "gender", "sex", "national", "origin", "born", "citizenship"}
PERSONAL_KEYS = {"referral_code", "tract_geoid", "event_id", "cert", "uninum"}
TMDL_TYPE = {"string": "string", "double": "double", "bigint": "int64", "boolean": "boolean", "date": "dateTime"}


def unquote(name):
    return name.strip().strip("'")


def parse_model(folder):
    """Return {table: {"columns": {name: dataType}, "measures": set}} for a TMDL semantic model."""
    tables = {}
    for f in (WORKSPACE / folder / "definition" / "tables").glob("*.tmdl"):
        text = f.read_text()
        table = unquote(re.search(r"^table (.+)$", text, re.M).group(1))
        tables[table] = {
            "columns": dict(re.findall(r"^\tcolumn (\S+)\n\t\tdataType: (\S+)", text, re.M)),
            "measures": {unquote(m) for m in re.findall(r"^\tmeasure ('[^']+'|\S+) =", text, re.M)},
        }
    return tables


def models():
    return sorted(p.name for p in WORKSPACE.glob("*.SemanticModel"))


def reports():
    return sorted(p.name for p in WORKSPACE.glob("*.Report"))


def bound_model(report):
    pbir = json.loads((WORKSPACE / report / "definition.pbir").read_text())
    return Path(pbir["datasetReference"]["byPath"]["path"]).name


def field_refs(node):
    """Yield (kind, table, property) for every Column or Measure reference in a visual."""
    if isinstance(node, dict):
        for kind in ("Column", "Measure"):
            ref = node.get(kind)
            if isinstance(ref, dict) and "SourceRef" in ref.get("Expression", {}):
                yield kind, ref["Expression"]["SourceRef"]["Entity"], ref["Property"]
        for value in node.values():
            yield from field_refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from field_refs(value)


@pytest.fixture(scope="session")
def schemas():
    """Run the notebook's code cells locally (no Spark), which only defines and prints the schemas."""
    nb = json.loads(NOTEBOOK.read_text())
    code = "\n\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    ns = {}
    exec(compile(code, str(NOTEBOOK), "exec"), ns)
    return ns["SCHEMAS"]


def test_every_definition_file_is_json_with_a_schema():
    files = [p for p in WORKSPACE.rglob("*") if p.is_file() and p.suffix in {".json", ".pbir", ".pbism", ".pbip", ""}]
    assert files
    for f in files:
        doc = json.loads(f.read_text())  # fails loudly on malformed JSON
        if f.name != "lakehouse.metadata.json":  # Fabric writes this one without a schema
            assert "$schema" in doc, f


def test_notebook_only_creates_tables_and_never_overwrites(schemas):
    code = "".join("".join(c["source"]) for c in json.loads(NOTEBOOK.read_text())["cells"] if c["cell_type"] == "code")
    assert "CREATE TABLE IF NOT EXISTS" in code
    for risky in ("overwrite", "INSERT", "DROP", "DELETE", "read_parquet", "read_csv"):
        assert risky not in code, f"notebook must not load or replace data: found {risky}"
    assert schemas


@pytest.mark.parametrize("report", reports())
def test_report_is_bound_to_a_model_in_the_workspace(report):
    assert (WORKSPACE / bound_model(report) / "definition.pbism").exists()


@pytest.mark.parametrize("report", reports())
def test_visual_fields_exist_in_bound_model(report):
    model = parse_model(bound_model(report))
    visuals = list((WORKSPACE / report).rglob("visual.json"))
    assert visuals
    for v in visuals:
        for kind, table, prop in field_refs(json.loads(v.read_text())):
            assert table in model, f"{v}: unknown table {table}"
            pool = model[table]["columns"] if kind == "Column" else model[table]["measures"]
            assert prop in pool, f"{v}: {kind} {table}[{prop}] not in model"


@pytest.mark.parametrize("report", reports())
def test_every_data_visual_is_labeled_a_placeholder(report):
    for v in (WORKSPACE / report).rglob("visual.json"):
        vis = json.loads(v.read_text())["visual"]
        if vis["visualType"] == "textbox":
            continue
        title = vis["visualContainerObjects"]["title"][0]["properties"]["text"]["expr"]["Literal"]["Value"]
        assert title.startswith("'PLACEHOLDER: "), f"{v}: {title}"


@pytest.mark.parametrize("report", reports())
def test_every_page_has_a_skeleton_banner(report):
    for page in (WORKSPACE / report / "definition" / "pages").iterdir():
        if not page.is_dir():
            continue
        texts = [json.dumps(json.loads(v.read_text())) for v in page.rglob("visual.json")]
        assert any("SKELETON, no data loaded" in t for t in texts), page


@pytest.mark.parametrize("model", models())
def test_relationships_reference_real_columns(model):
    rel = WORKSPACE / model / "definition" / "relationships.tmdl"
    if not rel.exists():
        pytest.skip("no relationships")
    tables = parse_model(model)
    for table, column in re.findall(r"^\t(?:from|to)Column: (\S+)\.(\S+)$", rel.read_text(), re.M):
        assert column in tables[table]["columns"], (table, column)


@pytest.mark.parametrize("model", models())
def test_model_columns_and_types_match_the_notebook(model, schemas):
    for table, spec in parse_model(model).items():
        expected = {col: TMDL_TYPE[t] for col, t in schemas[table]}
        assert spec["columns"] == expected, f"{model}/{table} drifted from the notebook"


def test_every_notebook_table_is_used_by_a_model(schemas):
    used = {t for m in models() for t in parse_model(m)}
    assert used == set(schemas)


def test_playbook_model_reads_only_the_aggregate(schemas):
    assert set(parse_model("DapaPlaybook.SemanticModel")) == {"agg_playbook"}
    agg_columns = {col for col, _ in schemas["agg_playbook"]}
    assert not PERSONAL_KEYS & agg_columns


def test_no_protected_attributes_anywhere(schemas):
    for table, columns in schemas.items():
        for col, _ in columns:
            assert not PROTECTED & set(col.lower().split("_")), f"{table}.{col}"


def test_terminal_preview_renders_every_page():
    result = subprocess.run([sys.executable, str(FABRIC / "tools" / "preview.py"), "--width", "100"],
                            capture_output=True, text=True, check=True)
    pages = sum(len(json.loads((WORKSPACE / r / "definition/pages/pages.json").read_text())["pageOrder"])
                for r in reports())
    assert len(re.findall(r"\|  page \d+ of \d+: ", result.stdout)) == pages
    assert "links (many -> one)" in result.stdout


def test_web_preview_places_every_visual_at_its_report_position(tmp_path):
    out = tmp_path / "preview.html"
    subprocess.run([sys.executable, str(FABRIC / "tools" / "web_preview.py"), "--out", str(out)], check=True,
                   capture_output=True)
    page = out.read_text()
    for report in reports():
        for v in (WORKSPACE / report).rglob("visual.json"):
            p = json.loads(v.read_text())["position"]
            assert f"left:{p['x']}px;top:{p['y']}px;width:{p['width']}px;height:{p['height']}px" in page, v
