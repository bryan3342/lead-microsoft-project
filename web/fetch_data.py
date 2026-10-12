"""Download the ROI Engine page's data from the Fabric lakehouse into web/data.json.

    python3 web/fetch_data.py

The Load Public Data notebook writes Files/dapa/site_data.json every time it runs, so the page shows
whatever metro and assumptions were last deployed. Uses your Azure CLI sign-in and fabric/deploy/config.env.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "fabric" / "deploy"))
import definitions as defs  # noqa: E402
from deploy import LAKEHOUSE, load_config  # noqa: E402
from fabric_api import Client  # noqa: E402


def main():
    cfg = load_config()
    api = Client()
    ws = next((w["id"] for w in api.list_all("/workspaces") if w["displayName"] == cfg["WORKSPACE_NAME"]), None)
    if not ws:
        sys.exit(f"Workspace {cfg['WORKSPACE_NAME']} not found. Run fabric/deploy/deploy.py up first.")
    name = defs.item_meta(LAKEHOUSE)["displayName"]
    lakehouse = next(i["id"] for i in api.list_all(f"/workspaces/{ws}/items?type=Lakehouse") if i["displayName"] == name)
    data = api.download(ws, lakehouse, "dapa/site_data.json")
    (ROOT / "web" / "data.json").write_bytes(data)
    print(f"wrote web/data.json ({len(data) / 1024:.0f} KB) from {cfg['WORKSPACE_NAME']} / {name}")


if __name__ == "__main__":
    main()
