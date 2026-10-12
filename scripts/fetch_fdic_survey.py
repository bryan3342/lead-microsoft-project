"""FDIC National Survey of Unbanked and Underbanked Households, 2021 and 2023.

Source: the JSON API behind the FDIC's official survey tool (household-survey.fdic.gov), which serves the
published estimates. It is undocumented, so every response is saved raw with provenance.
Checked against the 2023 executive summary: 4.2% unbanked / 14.2% underbanked nationally, 21.8% unbanked
for income under $15k.

Processed:
  fdic_survey_rates   long table: year x geography x measure x (optional) household breakdown, with
                      weighted households and respondent counts (small counts = unreliable estimates)

No race/ethnicity breakdowns are requested (SOW fair-lending guardrail). The survey has no language variable.
"""

import itertools
import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from common import SAMPLE_CBSA, SAMPLE_STATES, raw_dir, write_processed, write_provenance, _session

API = "https://ei-app.app.cloud.gov/api"

YEARS = ["2021", "2023"]
GEOGRAPHIES = [("national", 0, 0, "United States")]
GEOGRAPHIES += [("state", int(fips), 0, abbr) for fips, abbr in SAMPLE_STATES.items()]
GEOGRAPHIES += [("msa", 0, int(SAMPLE_CBSA), "Washington-Arlington-Alexandria, DC-VA-MD-WV")]

# Banking status (unbanked / underbanked / fully banked); variable versions differ by year.
BANK_STATUS = {"2021": "hbankstatv5", "2023": "hbankstatv6"}
# Asked with household breakdowns.
BREAKDOWNS = ["hhincome", "hhtypev3"]
# Asked overall only (universe: unbanked households).
UNBANKED_DETAIL = [
    "hunbnkcashonly",  # cash-only unbanked
    "hbnkint",  # interest in having an account
    "hunbnkrmv5",  # main reason unbanked
    "hunbnkr1v5", "hunbnkr2v5", "hunbnkr3v5", "hunbnkr4v5", "hunbnkr5v5",  # why unbanked (multi-select)
    "hunbnkr6v5", "hunbnkr7v5", "hunbnkr8v5", "hunbnkr9v5", "hunbnkr10v5",
]


def query(year, geo, col_var, row_var):
    geo_type, state, msa, _ = geo
    body = {
        "chartType": "hbar",
        "year": year,
        "colVar": col_var,
        "rowvars": [row_var] if row_var else [],
        "filterVar": "",
        "filterVar2": "",
        "filterVarValue": [],
        "filterVarValue2": [],
        "region": 0,
        "state": state,
        "msa": msa,
        "needNewData": True,
    }
    resp = _session.post(f"{API}/data", json=body, timeout=120)
    if resp.status_code != 200:
        return body, None
    return body, resp.json()


def main():
    jobs = []
    for year, geo in itertools.product(YEARS, GEOGRAPHIES):
        for row_var in [None, *BREAKDOWNS]:
            jobs.append((year, geo, BANK_STATUS[year], row_var))
        for col_var in UNBANKED_DETAIL:
            jobs.append((year, geo, col_var, None))

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda j: (j, *query(*j)), jobs))

    out = raw_dir("fdic_survey") / "responses.json"
    out.write_text(json.dumps([{"request": body, "response": data} for _, body, data in results]))
    failed = [j for j, _, data in results if data is None]
    write_provenance(out, f"{API}/data", {"requests": len(jobs)}, rows=len(jobs) - len(failed),
                     extra={"failed_requests": [[j[0], j[1][0], j[1][3], j[2], j[3]] for j in failed]})

    rows = []
    for (year, geo, col_var, row_var), _, data in results:
        for r in data or []:
            rows.append(
                {
                    "year": int(year),
                    "geography_type": geo[0],
                    "geography_code": str(geo[2] or geo[1] or "US"),
                    "geography_name": geo[3],
                    "measure_var": col_var,
                    "measure": r["colcategory"],
                    "category": r["colheader"],
                    "breakdown_var": row_var or "all",
                    "breakdown": r["rowheader"] if row_var else "All households",
                    "percent": r["percent"],
                    "households_000": r["share"],
                    "base_households_000": r["total"],
                    "respondents": int(r["rowcount"]),
                    "respondents_base": int(r["dcount"]),
                }
            )
    df = pd.DataFrame(rows)
    write_processed(df, "fdic_survey_rates")
    print(f"  {len(jobs)} queries, {len(failed)} failed")

    headline = df[(df.breakdown_var == "all") & df.measure_var.isin(BANK_STATUS.values())]
    print(headline.pivot_table(index=["geography_name", "year"], columns="category", values="percent").round(2).to_string())


if __name__ == "__main__":
    main()
