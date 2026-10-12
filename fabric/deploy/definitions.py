"""Turn the item folders in fabric/workspace into Fabric REST API definitions.

Pure functions only: no network, no files written. The repo copies stay untouched;
deploy-time values (lakehouse, SQL endpoint, model IDs) are injected in memory.
"""
import base64
import json
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parents[1] / "workspace"
PLACEHOLDERS = ("<SQL_ENDPOINT_HOST>", "<SQL_ENDPOINT_ID>")


def item_meta(folder: str) -> dict:
    """Type, display name and description from the item's .platform file."""
    return json.loads((WORKSPACE_DIR / folder / ".platform").read_text())["metadata"]


def _part(path: str, data: bytes) -> dict:
    return {"path": path, "payload": base64.b64encode(data).decode(), "payloadType": "InlineBase64"}


def _folder_parts(folder: str, transform=None) -> list:
    root = WORKSPACE_DIR / folder
    parts = []
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.name == ".platform":
            continue
        rel = f.relative_to(root).as_posix()
        data = f.read_bytes()
        parts.append(_part(rel, transform(rel, data) if transform else data))
    return parts


def notebook_definition(lakehouse_id: str, lakehouse_name: str, workspace_id: str) -> dict:
    nb = json.loads((WORKSPACE_DIR / "LoadSampleData.Notebook" / "notebook-content.ipynb").read_text())
    nb["metadata"]["dependencies"] = {"lakehouse": {
        "default_lakehouse": lakehouse_id,
        "default_lakehouse_name": lakehouse_name,
        "default_lakehouse_workspace_id": workspace_id,
    }}
    return {"format": "ipynb", "parts": [_part("artifact.content.ipynb", json.dumps(nb).encode())]}


def semantic_model_definition(folder: str, sql_host: str, sql_endpoint_id: str) -> dict:
    def connect(rel, data):
        if rel != "definition/expressions.tmdl":
            return data
        text = data.decode()
        if not all(p in text for p in PLACEHOLDERS):
            raise ValueError(f"{folder}: expressions.tmdl is missing the connection placeholders")
        return text.replace(PLACEHOLDERS[0], sql_host).replace(PLACEHOLDERS[1], sql_endpoint_id).encode()

    return {"format": "TMDL", "parts": _folder_parts(folder, connect)}


def report_definition(folder: str, semantic_model_id: str) -> dict:
    """The API cannot resolve byPath, so bind the report to the deployed model by ID."""
    def rebind(rel, data):
        if rel != "definition.pbir":
            return data
        pbir = json.loads(data)
        pbir["datasetReference"] = {"byConnection": {"connectionString": f"semanticmodelid={semantic_model_id}"}}
        return json.dumps(pbir, indent=2).encode()

    return {"parts": _folder_parts(folder, rebind)}
