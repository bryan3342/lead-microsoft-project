"""Offline checks for the Fabric workspace definitions.

Run from the repo root: pytest fabric/tests
"""
import json
import os
import re
from pathlib import Path

import pandas as pd
import pytest

WORKSPACE = Path(__file__).resolve().parents[1] / "workspace"
NOTEBOOK = WORKSPACE / "LoadSampleData.Notebook" / "notebook-content.ipynb"
PROTECTED = {"race", "ethnicity", "religion", "gender", "sex", "national", "origin", "born", "citizenship"}


def unquote(name):
    return name.strip().strip("'")


def parse_model(folder):
    """Return {table: {"columns": set, "measures": set}} for a TMDL semantic model."""
    tables = {}
    for f in (WORKSPACE / folder / "definition" / "tables").glob("*.tmdl"):
        text = f.read_text()
        table = unquote(re.search(r"^table (.+)$", text, re.M).group(1))
        tables[table] = {
            "columns": {unquote(m) for m in re.findall(r"^\tcolumn (.+)$", text, re.M)},
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
def sample_tables(tmp_path_factory):
    """Run the notebook's code cells locally (no Spark), which writes CSVs to sample-output/."""
    nb = json.loads(NOTEBOOK.read_text())
    code = "\n\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    cwd = os.getcwd()
    os.chdir(tmp_path_factory.mktemp("notebook"))
    try:
        ns = {}
        exec(compile(code, str(NOTEBOOK), "exec"), ns)
        written = {p.stem for p in Path("sample-output").glob("*.csv")}
    finally:
        os.chdir(cwd)
    assert written == set(ns["TABLES"]), "notebook did not write every table"
    return ns


def test_every_definition_file_is_json_with_a_schema():
    files = [p for p in WORKSPACE.rglob("*") if p.is_file() and p.suffix in {".json", ".pbir", ".pbism", ".pbip", ""}]
    assert files
    for f in files:
        doc = json.loads(f.read_text())  # fails loudly on malformed JSON
        if f.name != "lakehouse.metadata.json":  # Fabric writes this one without a schema
            assert "$schema" in doc, f


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


@pytest.mark.parametrize("model", models())
def test_relationships_reference_real_columns(model):
    rel = WORKSPACE / model / "definition" / "relationships.tmdl"
    if not rel.exists():
        pytest.skip("no relationships")
    tables = parse_model(model)
    for ref in re.findall(r"^\t(?:from|to)Column: (\S+)\.(\S+)$", rel.read_text(), re.M):
        assert ref[1] in tables[ref[0]]["columns"], ref


@pytest.mark.parametrize("model", models())
def test_model_columns_match_notebook_output(model, sample_tables):
    for table, spec in parse_model(model).items():
        produced = set(sample_tables["TABLES"][table].columns)
        assert spec["columns"] == produced, f"{model}/{table} drifted from the notebook"


def test_playbook_model_reads_only_the_aggregate(sample_tables):
    assert set(parse_model("DapaPlaybook.SemanticModel")) == {"agg_playbook"}
    agg = sample_tables["agg_playbook"]
    assert not {"referral_code", "tract_id", "event_id", "bank_id"} & set(agg.columns)
    assert (agg["attendees"] >= sample_tables["MIN_GROUP_SIZE"]).all()
    assert len(agg) > 0, "suppression removed every group; the sample is too small"


def test_no_protected_attributes_in_any_model():
    for model in models():
        for table, spec in parse_model(model).items():
            for col in spec["columns"]:
                assert not PROTECTED & set(col.lower().split("_")), f"{model}/{table}.{col}"


def test_outcomes_only_for_opted_in_attendees(sample_tables):
    fa = sample_tables["fact_attendee"]
    unmatched = fa[~(fa["consented"] & fa["attended"])]
    outcomes = ["account_opened", "funded_30d", "active_90d", "products_held", "trust_before", "trust_after"]
    assert unmatched[outcomes].isna().all().all()


def test_matched_control_tracts_have_no_events(sample_tables):
    tracts = sample_tables["dim_tract"]
    control = set(tracts.loc[tracts["pilot_arm"] == "Control", "tract_id"])
    assert len(control) == 2
    assert not control & set(sample_tables["dim_event"]["tract_id"])


def test_scenario_values_are_labeled_assumptions(sample_tables):
    ltv = sample_tables["scenario_ltv"]
    assert set(ltv["basis"]) == {"Assumption"}
    for _, rows in ltv.groupby("scenario"):
        assert pd.Series(rows.sort_values("year")["cumulative_ltv_usd"]).is_monotonic_increasing
