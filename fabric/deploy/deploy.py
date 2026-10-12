"""Stand up the DAPA Fabric workspace in an Azure subscription, using your Azure CLI sign-in.

    python fabric/deploy/deploy.py up          create or update everything, then print report links
    python fabric/deploy/deploy.py up --dry-run show the plan without calling Azure
    python fabric/deploy/deploy.py status      show capacity state and workspace items
    python fabric/deploy/deploy.py pause       stop capacity billing (the workspace and data are kept)
    python fabric/deploy/deploy.py resume      start the capacity again

Settings come from fabric/deploy/config.env (copy config.env.example). See RUNBOOK.md.
Safe to re-run: existing items are updated in place, never deleted.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import definitions as defs  # noqa: E402
from fabric_api import ARM, FABRIC, POWERBI, ApiError, Client, az  # noqa: E402

CONFIG = Path(__file__).parent / "config.env"
CAPACITY_API = "2023-11-01"
REQUIRED = ["SUBSCRIPTION_ID", "RESOURCE_GROUP", "LOCATION", "CAPACITY_NAME", "CAPACITY_SKU",
            "CAPACITY_ADMINS", "WORKSPACE_NAME"]
LAKEHOUSE = "DapaLakehouse.Lakehouse"
NOTEBOOK = "CreateTables.Notebook"
MODELS_AND_REPORTS = [("DapaBank.SemanticModel", "DapaBank.Report"),
                      ("DapaPlaybook.SemanticModel", "DapaPlaybook.Report")]


def step(msg):
    print(f"\n==> {msg}", flush=True)


def load_config(path=CONFIG) -> dict:
    if not path.exists():
        sys.exit(f"Missing {path}. Copy config.env.example to config.env and fill it in.")
    cfg = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            cfg[key.strip()] = value.strip().strip('"')
    missing = [k for k in REQUIRED if not cfg.get(k)]
    if missing:
        sys.exit(f"config.env is missing: {', '.join(missing)}")
    if not cfg["CAPACITY_NAME"].isalnum() or not cfg["CAPACITY_NAME"].islower():
        sys.exit("CAPACITY_NAME must be lowercase letters and digits only (an Azure naming rule).")
    return cfg


def split(value: str) -> list:
    return [v.strip() for v in value.split(",") if v.strip()]


def capacity_url(cfg):
    return (f"{ARM}/subscriptions/{cfg['SUBSCRIPTION_ID']}/resourceGroups/{cfg['RESOURCE_GROUP']}"
            f"/providers/Microsoft.Fabric/capacities/{cfg['CAPACITY_NAME']}")


# ---------------------------------------------------------------- capacity (Azure)
def get_capacity(api, cfg):
    try:
        return api.get(f"{capacity_url(cfg)}?api-version={CAPACITY_API}")
    except ApiError as e:
        if e.status == 404:
            return None
        raise


def wait_capacity(api, cfg, want_state):
    while True:
        cap = get_capacity(api, cfg)
        props = cap["properties"]
        if props.get("provisioningState") == "Succeeded" and props.get("state") == want_state:
            return cap
        if props.get("provisioningState") == "Failed":
            sys.exit(f"Capacity provisioning failed: {props}")
        time.sleep(10)


def ensure_capacity(api, cfg):
    step(f"Fabric capacity {cfg['CAPACITY_NAME']} ({cfg['CAPACITY_SKU']}) in {cfg['RESOURCE_GROUP']}")
    az("provider", "register", "--namespace", "Microsoft.Fabric", "--subscription", cfg["SUBSCRIPTION_ID"], "--wait")
    cap = get_capacity(api, cfg)
    if cap is None:
        print("creating (takes a minute or two)")
        api.request("PUT", f"{capacity_url(cfg)}?api-version={CAPACITY_API}", {
            "location": cfg["LOCATION"],
            "sku": {"name": cfg["CAPACITY_SKU"], "tier": "Fabric"},
            "properties": {"administration": {"members": split(cfg["CAPACITY_ADMINS"])}},
        })
    elif cap["properties"].get("state") == "Paused":
        print("paused; resuming")
        api.request("POST", f"{capacity_url(cfg)}/resume?api-version={CAPACITY_API}")
    else:
        print("already exists")
    wait_capacity(api, cfg, "Active")
    for _ in range(30):  # the Fabric API can lag a little behind Azure on new capacities
        for c in api.list_all("/capacities"):
            if c["displayName"] == cfg["CAPACITY_NAME"]:
                return c["id"]
        time.sleep(10)
    sys.exit("Capacity is active in Azure but not visible in Fabric. Check you are a capacity admin.")


# ---------------------------------------------------------------- workspace (Fabric)
def ensure_workspace(api, cfg, capacity_id):
    name = cfg["WORKSPACE_NAME"]
    step(f"Workspace {name}")
    ws = next((w for w in api.list_all("/workspaces") if w["displayName"] == name), None)
    if ws is None:
        ws = api.fabric("POST", "/workspaces", {"displayName": name, "capacityId": capacity_id,
                                                "description": "DAPA ROI Engine dashboards (skeleton, no data yet)."})
        print("created")
    elif ws.get("capacityId") != capacity_id:
        api.fabric("POST", f"/workspaces/{ws['id']}/assignToCapacity", {"capacityId": capacity_id})
        print("moved onto the capacity")
    else:
        print("already exists")
    for email in split(cfg.get("WORKSPACE_ADMINS", "")):
        user_id = az("ad", "user", "show", "--id", email, "--query", "id", "-o", "tsv")
        try:
            api.fabric("POST", f"/workspaces/{ws['id']}/roleAssignments",
                       {"principal": {"id": user_id, "type": "User"}, "role": "Admin"})
            print(f"added admin {email}")
        except ApiError as e:
            if e.status != 409:  # 409: already has access
                raise
    return ws["id"]


def ensure_item(api, ws, folder, definition=None):
    """Create the item, or update its definition if one with the same name and type exists."""
    meta = defs.item_meta(folder)
    existing = next((i for i in api.list_all(f"/workspaces/{ws}/items?type={meta['type']}")
                     if i["displayName"] == meta["displayName"]), None)
    if existing:
        if definition:
            api.fabric("POST", f"/workspaces/{ws}/items/{existing['id']}/updateDefinition", {"definition": definition})
        print(f"{meta['type']} {meta['displayName']}: updated")
        return existing["id"]
    body = {"displayName": meta["displayName"], "type": meta["type"], "description": meta.get("description", "")}
    if definition:
        body["definition"] = definition
    item = api.fabric("POST", f"/workspaces/{ws}/items", body)
    print(f"{meta['type']} {meta['displayName']}: created")
    return item["id"]


def sql_endpoint(api, ws, lakehouse_id):
    for _ in range(60):
        props = api.get(f"{FABRIC}/workspaces/{ws}/lakehouses/{lakehouse_id}")["properties"]
        sql = props.get("sqlEndpointProperties") or {}
        if sql.get("provisioningStatus") == "Success":
            return sql["connectionString"], sql["id"]
        time.sleep(10)
    sys.exit("Lakehouse SQL endpoint did not finish provisioning.")


def run_notebook(api, ws, notebook_id, lakehouse_id, lakehouse_name):
    step("Running Create Tables notebook to make the empty tables (a few minutes while Spark starts)")
    _, headers, _ = api.request("POST", f"{FABRIC}/workspaces/{ws}/items/{notebook_id}/jobs/instances?jobType=RunNotebook", {
        "executionData": {"configuration": {"defaultLakehouse": {
            "name": lakehouse_name, "id": lakehouse_id, "workspaceId": ws}}}})
    job_url = headers["Location"]
    while True:
        time.sleep(15)
        job = api.get(job_url)
        print(f"  {job['status']}", flush=True)
        if job["status"] == "Completed":
            return
        if job["status"] in ("Failed", "Cancelled", "Deduped"):
            sys.exit(f"Notebook run {job['status']}: {job.get('failureReason')}")


def refresh_model(api, ws, model_id, name):
    """Direct Lake refresh (framing). Retries while the SQL endpoint catches up with new tables."""
    url = f"{POWERBI}/groups/{ws}/datasets/{model_id}/refreshes"
    for attempt in range(1, 5):
        api.request("POST", url, {"notifyOption": "NoNotification"})
        while True:
            time.sleep(10)
            history = api.get(f"{url}?$top=1")["value"]
            latest = history[0] if history else {"status": "Unknown"}
            if latest["status"] != "Unknown":  # Unknown means still running
                break
        if latest["status"] == "Completed":
            print(f"{name}: refreshed")
            return
        print(f"{name}: refresh attempt {attempt} failed, retrying in 30s")
        time.sleep(30)
    print(f"WARNING {name}: refresh kept failing: {latest.get('serviceExceptionJson')}. See RUNBOOK.md troubleshooting.")


def up(api, cfg):
    capacity_id = ensure_capacity(api, cfg)
    ws = ensure_workspace(api, cfg, capacity_id)

    step("Lakehouse and notebook")
    lakehouse_id = ensure_item(api, ws, LAKEHOUSE)
    lakehouse_name = defs.item_meta(LAKEHOUSE)["displayName"]
    notebook_id = ensure_item(api, ws, NOTEBOOK, defs.notebook_definition(lakehouse_id, lakehouse_name, ws))
    host, endpoint_id = sql_endpoint(api, ws, lakehouse_id)
    run_notebook(api, ws, notebook_id, lakehouse_id, lakehouse_name)
    try:
        api.fabric("POST", f"/workspaces/{ws}/sqlEndpoints/{endpoint_id}/refreshMetadata", {})
    except ApiError as e:
        print(f"(SQL endpoint metadata refresh skipped: HTTP {e.status}; the model refresh retries instead)")

    step("Semantic models and reports")
    links = []
    for model_folder, report_folder in MODELS_AND_REPORTS:
        model_id = ensure_item(api, ws, model_folder, defs.semantic_model_definition(model_folder, host, endpoint_id))
        refresh_model(api, ws, model_id, defs.item_meta(model_folder)["displayName"])
        report_id = ensure_item(api, ws, report_folder, defs.report_definition(report_folder, model_id))
        links.append((defs.item_meta(report_folder)["displayName"],
                      f"https://app.fabric.microsoft.com/groups/{ws}/reports/{report_id}"))

    step("Done. Open the dashboards:")
    for name, link in links:
        print(f"  {name}: {link}")
    print(f"\nPause billing when finished:  python {Path(__file__).as_posix()} pause")


def dry_run(cfg):
    step("Dry run: nothing is sent to Azure")
    print(f"capacity  {cfg['CAPACITY_NAME']} {cfg['CAPACITY_SKU']} in {cfg['LOCATION']}, "
          f"resource group {cfg['RESOURCE_GROUP']}, admins {split(cfg['CAPACITY_ADMINS'])}")
    print(f"workspace {cfg['WORKSPACE_NAME']}, extra admins {split(cfg.get('WORKSPACE_ADMINS', ''))}")
    fake = "00000000-0000-0000-0000-000000000000"
    plan = [(LAKEHOUSE, None), (NOTEBOOK, defs.notebook_definition(fake, "DapaLakehouse", fake))]
    for model_folder, report_folder in MODELS_AND_REPORTS:
        plan += [(model_folder, defs.semantic_model_definition(model_folder, "host.example", fake)),
                 (report_folder, defs.report_definition(report_folder, fake))]
    for folder, definition in plan:
        meta = defs.item_meta(folder)
        parts = len(definition["parts"]) if definition else 0
        print(f"item      {meta['type']:<14} {meta['displayName']:<26} {parts} definition parts")
    print("then: run the notebook, refresh both models, print report links")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["up", "status", "pause", "resume"])
    parser.add_argument("--dry-run", action="store_true", help="with up: print the plan only")
    parser.add_argument("--config", type=Path, default=CONFIG)
    args = parser.parse_args()
    cfg = load_config(args.config)
    if args.dry_run:
        return dry_run(cfg)

    az("account", "set", "--subscription", cfg["SUBSCRIPTION_ID"])
    api = Client()
    if args.command == "up":
        up(api, cfg)
    elif args.command in ("pause", "resume"):
        action = "suspend" if args.command == "pause" else "resume"
        api.request("POST", f"{capacity_url(cfg)}/{action}?api-version={CAPACITY_API}")
        cap = wait_capacity(api, cfg, "Paused" if action == "suspend" else "Active")
        print(f"capacity {cfg['CAPACITY_NAME']}: {cap['properties']['state']}")
    else:
        cap = get_capacity(api, cfg)
        print(f"capacity {cfg['CAPACITY_NAME']}: {cap['properties']['state'] if cap else 'not created'}")
        ws = next((w for w in api.list_all("/workspaces") if w["displayName"] == cfg["WORKSPACE_NAME"]), None)
        if not ws:
            return print(f"workspace {cfg['WORKSPACE_NAME']}: not created")
        for item in api.list_all(f"/workspaces/{ws['id']}/items"):
            print(f"  {item['type']:<14} {item['displayName']}")


if __name__ == "__main__":
    main()
