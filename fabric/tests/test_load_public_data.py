"""Offline checks for the Load Public Data notebook, run against each collected metro in data/processed."""
import json
import os
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

REPO = Path(__file__).resolve().parents[2]
WORKSPACE = REPO / "fabric" / "workspace"
NOTEBOOK = WORKSPACE / "LoadPublicData.Notebook" / "notebook-content.ipynb"
SAMPLES = sorted(p.name for p in (REPO / "data" / "processed").iterdir() if (p / "acs_tracts.csv").exists())


def code_cells(path):
    return [("".join(c["source"])) for c in json.loads(path.read_text())["cells"] if c["cell_type"] == "code"]


@pytest.fixture(scope="module")
def schemas():
    ns = {}
    exec(code_cells(WORKSPACE / "CreateTables.Notebook" / "notebook-content.ipynb")[0], ns)
    return ns["SCHEMAS"]


@pytest.fixture(scope="module", params=SAMPLES)
def loaded(request, tmp_path_factory):
    cwd = os.getcwd()
    os.environ.update(DAPA_REPO=str(REPO), DAPA_SAMPLE=request.param)
    os.chdir(tmp_path_factory.mktemp(request.param))
    try:
        ns = {}
        exec(compile("\n\n".join(code_cells(NOTEBOOK)), str(NOTEBOOK), "exec"), ns)
    finally:
        os.chdir(cwd)
        del os.environ["DAPA_REPO"], os.environ["DAPA_SAMPLE"]
    return ns


def test_filled_tables_match_the_create_tables_contract(loaded, schemas):
    for name, columns in schemas.items():
        if name in loaded["TABLES"]:
            assert list(loaded["TABLES"][name].columns) == [c for c, _ in columns], name


def test_pilot_tables_are_never_filled(loaded):
    assert not {"fact_tract_accounts", "dim_event", "fact_attendee", "agg_playbook"} & set(loaded["TABLES"])


def test_keys_are_unique_and_facts_join_to_tracts(loaded):
    t = loaded["TABLES"]
    assert t["dim_tract"]["tract_geoid"].is_unique and t["dim_bank"]["cert"].is_unique and t["dim_branch"]["uninum"].is_unique
    # Every row must join, or the dashboard shows a "(Blank)" group in its slicers and charts.
    for fact in ("dim_branch", "fact_branch_events", "fact_tract_lending", "fact_tract_complaints", "tract_ltv"):
        assert t[fact]["tract_geoid"].isin(t["dim_tract"]["tract_geoid"]).all(), fact
    assert t["dim_tract"]["county_fips"].isin(t["dim_county"]["county_fips"]).all()
    assert t["dim_branch"]["cert"].isin(t["dim_bank"]["cert"]).all()
    assert t["fact_branch_deposits"]["uninum"].isin(t["dim_branch"]["uninum"]).all()
    for fact in ("fact_branch_deposits", "fact_branch_events", "fact_tract_lending", "fact_tract_complaints"):
        assert t[fact]["year"].isin(t["dim_year"]["year"]).all(), fact


def test_estimates_add_up_to_the_metro_survey_rate(loaded):
    tracts, metro = loaded["dim_tract"], loaded["metro"]
    rate = metro.loc[metro["category"] == "Unbanked", "percent"].iloc[0] / 100
    assert tracts["est_unbanked_households"].sum() / tracts["households"].sum() == pytest.approx(rate, rel=0.01)


def test_ltv_scenarios_are_ordered_and_every_input_has_a_source(loaded):
    ltv = loaded["scenario_ltv"]
    final = ltv[ltv["year"] == ltv["year"].max()].set_index("scenario")["cumulative_ltv_usd"]
    assert final["Conservative"] < final["Base"] < final["Optimistic"]
    net = loaded["tract_ltv"].groupby("scenario")["net_value_5yr_usd"].sum()
    assert net["Conservative"] < net["Base"] < net["Optimistic"]
    assert loaded["ltv_assumptions"]["source"].notna().all()


def test_website_snapshot_is_complete_and_consistent(loaded):
    site = json.loads(loaded["site_json"])
    assert set(site["scenarios"]) == {"Conservative", "Base", "Optimistic"}
    for s in site["scenarios"].values():
        assert sum(s["components"].values()) == pytest.approx(s["ltv_net"], abs=3)
        assert s["footprint_value"] == pytest.approx(site["reachable_households"] * s["adoption_rate"] * s["ltv_net"], rel=0.01)
    pilot = site["pilot"]
    assert len(pilot["pilot_offices"]) == len(pilot["control_offices"]) == pilot["branches"]
    assert not set(pilot["pilot_offices"]) & set(pilot["control_offices"])
    assert pilot["opened"]["pilot"] > pilot["opened"]["control"] > 0
    assert site["map"]["tiles"] and site["counties"] and site["trust"]["reasons"]
