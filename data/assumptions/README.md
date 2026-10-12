# Assumptions

Every number the dashboards assume rather than measure lives here, one row per assumption, with its source.
The deploy script uploads these files to the lakehouse, and the `Load Public Data` notebook in `fabric/workspace` reads them.
Edit a value, deploy again, and the tables update. Nothing is hardcoded in the notebook.

| File | What's in it |
|---|---|
| `fdic_rates_by_income.csv` | Unbanked and underbanked rates per household income bracket, and the ACS B19001 variables that make up each bracket |
| `ltv_assumptions.csv` | Inputs to the 5-year lifetime value model, per scenario (conservative, base, optimistic) |

## `fdic_rates_by_income.csv`

- **Source:** FDIC National Survey of Unbanked and Underbanked Households, 2023, banking status by household income, United States (collected by `scripts/fetch_fdic_survey.py`).
- **Why national rates:** each national bracket rests on 2,378 to 13,211 surveyed households. Metro cuts are too thin to split by income: Houston's under-$15,000 bracket rests on 35 households.
- **Calibration:** the notebook then scales every tract so the metro total matches the FDIC survey's overall rate for that metro, read from the metro's `fdic_survey_rates`. For Houston that multiplies the unbanked estimate by 2.47 and the underbanked estimate by 1.25. The metro rate itself rests on a small sample (39 unbanked households of 439 surveyed in Houston). Set `CALIBRATE_TO_METRO = False` in the notebook to use the national rates as published.
- **What that implies:** tract figures are estimates. Income decides how the metro's unbanked households are spread across tracts; the survey decides how many there are. Label them "estimated" wherever they are shown.
- **Unbanked** means no one in the household has a checking or savings account. **Underbanked** means the household has an account but also used a nonbank product such as a check casher, money order or payday loan in the past 12 months.

## `ltv_assumptions.csv`

- **Every value is a placeholder** until the team's sourced LTV spreadsheet replaces it. Put the citation in `source` and change `basis` from `Assumption` to `Sourced` when you do.
- `scenario = all` applies to every scenario. Only retention, cross-sell probability and adoption rate vary by scenario.
- The dashboard labels the scenarios Low, Base and High.
