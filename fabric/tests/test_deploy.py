"""Offline checks for the deploy script: definitions it sends and config it accepts."""
import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"
sys.path.insert(0, str(DEPLOY))
import definitions as defs  # noqa: E402
import deploy  # noqa: E402

LH, WS, SQL_ID, MODEL_ID = "lh-id", "ws-id", "sql-id", "model-id"


def decoded(definition):
    return {p["path"]: base64.b64decode(p["payload"]).decode() for p in definition["parts"]}


def test_notebook_gets_the_deployed_lakehouse_as_default():
    parts = decoded(defs.notebook_definition(LH, "DapaLakehouse", WS))
    nb = json.loads(parts["artifact.content.ipynb"])
    assert nb["metadata"]["dependencies"]["lakehouse"] == {
        "default_lakehouse": LH, "default_lakehouse_name": "DapaLakehouse", "default_lakehouse_workspace_id": WS}


@pytest.mark.parametrize("model", ["DapaBank.SemanticModel", "DapaPlaybook.SemanticModel"])
def test_model_connection_is_filled_in_memory_only(model):
    on_disk = (defs.WORKSPACE_DIR / model / "definition" / "expressions.tmdl").read_text()
    parts = decoded(defs.semantic_model_definition(model, "host.example", SQL_ID))
    expr = parts["definition/expressions.tmdl"]
    assert 'Sql.Database("host.example", "sql-id")' in expr
    assert not any(p in expr for p in defs.PLACEHOLDERS)
    assert (defs.WORKSPACE_DIR / model / "definition" / "expressions.tmdl").read_text() == on_disk
    assert "definition.pbism" in parts and ".platform" not in parts
    assert all(p == "definition.pbism" or p.startswith("definition/") for p in parts)


@pytest.mark.parametrize("report", ["DapaBank.Report", "DapaPlaybook.Report"])
def test_report_is_rebound_to_the_deployed_model(report):
    parts = decoded(defs.report_definition(report, MODEL_ID))
    pbir = json.loads(parts["definition.pbir"])
    assert pbir["datasetReference"] == {"byConnection": {"connectionString": f"semanticmodelid={MODEL_ID}"}}
    assert any(p.endswith("visual.json") for p in parts)


def test_deploy_order_pairs_each_report_with_its_bound_model():
    for model, report in deploy.MODELS_AND_REPORTS:
        pbir = json.loads((defs.WORKSPACE_DIR / report / "definition.pbir").read_text())
        assert pbir["datasetReference"]["byPath"]["path"] == f"../{model}"


def write_config(tmp_path, **overrides):
    lines = (DEPLOY / "config.env.example").read_text().splitlines()
    for key, value in overrides.items():
        lines = [f"{key}={value}" if ln.startswith(f"{key}=") else ln for ln in lines]
    path = tmp_path / "config.env"
    path.write_text("\n".join(lines))
    return path


def test_example_config_loads(tmp_path):
    cfg = deploy.load_config(write_config(tmp_path))
    assert cfg["CAPACITY_SKU"] == "F2" and cfg["WORKSPACE_NAME"] == "DAPA Dev"


@pytest.mark.parametrize("name", ["Dapa-Dev", "dapa_dev", "DAPA"])
def test_invalid_capacity_names_are_rejected(tmp_path, name):
    with pytest.raises(SystemExit):
        deploy.load_config(write_config(tmp_path, CAPACITY_NAME=name))


def test_dry_run_builds_every_definition_without_azure(tmp_path):
    result = subprocess.run(
        [sys.executable, str(DEPLOY / "deploy.py"), "up", "--dry-run", "--config", str(write_config(tmp_path))],
        capture_output=True, text=True, check=True)
    for name in ["DapaLakehouse", "Create Tables", "DAPA Bank Dashboard", "DAPA Mastercard Playbook"]:
        assert name in result.stdout
