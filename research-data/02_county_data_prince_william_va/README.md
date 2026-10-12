# Prince William County banking-access data pack

County: Prince William, VA (FIPS 51153). Window: 2021–2026, except the ACS tract file (2019–2023 five-year).
Checked against live sources on Oct 12, 2026.

## Files

| File | Source | Period | Grain | Status |
| --- | --- | --- | --- | --- |
| `acs_2019_2023_by_tract.csv` | Census ACS 5-year | 2019–2023 | 93 tracts | Not re-verified (Census API needs a key). Replace with 2020–2024 via `pull_sources.py`. |
| `fdic_household_survey_2019_2023.csv` | FDIC Household Survey, appendix tables A.2–A.4 | 2019–2023 | US, VA, DC, MD, DC metro, income bracket | Read from FDIC tables Oct 12, 2026 |
| `fdic_sod_county_trend.csv` | FDIC Summary of Deposits | 2021–2025 | County by year | 2021 and 2025 verified live |
| `fdic_sod_by_bank_2021_vs_2025.csv` | FDIC Summary of Deposits | 2021, 2025 | Bank | 2025 bank totals verified live |
| `fdic_branches_2026.csv` | FDIC BankFind `/locations` | Current (run Oct 9, 2026) | Branch | Count (55) and first record verified live |
| `hmda_2021_2025_county_trend.csv` | HMDA Data Browser | 2021–2025 | County by year | 2021 and 2025 verified live |
| `hmda_2025_by_tract.csv` | HMDA Data Browser | 2025 | 92 tracts | Sums to within 11 applications of county total (loans without a tract) |
| `hmda_2025_top_lenders.csv` | HMDA Data Browser | 2025 | Lender | Not re-verified |
| `cfpb_complaints_*.csv` (5 files) | CFPB Consumer Complaint Database | Jan 2021 – Oct 12, 2026 | Year, product, issue, company, ZIP | Not re-verified (API errors); all breakdowns sum to 800 |
| `tract_geography.csv` | Derived: tract centers + FDIC branches | 2026 | Tract | Straight-line distance, not travel time |
| `merged_tract_profile.csv` | ACS + HMDA + geography joined on `tract_geoid` | Mixed | 93 tracts | Rebuilt by `build/build_map.py` |
| `tract_paths.json` | Simplified tract outlines, projected to a 1000×1143 SVG frame | 2020 tracts | Tract | For the map only, not for GIS |

## Key columns

- `tract_geoid`: 11-digit state + county + tract FIPS. Join key across files.
- `pct_*` / `pct_*_moe`: ACS share in percent and its 90% margin of error in percentage points.
- `reliability_*`: Low or medium. A coefficient of variation (MOE ÷ 1.645 ÷ estimate) above 40% means the tract value is too noisy to rank.
- `denial_rate_pct` (HMDA): denied ÷ (originated + approved not accepted + denied). Withdrawn and incomplete files are excluded.
- `tract_income_pct_of_msa` (HMDA/FFIEC): tract median family income as % of metro. Under 80 = low- or moderate-income (LMI) tract under CRA.
- `km_to_nearest_branch`: straight-line km from tract center to the nearest FDIC office.
- `deposits_*_usd_thousands`: FDIC reports deposits in thousands of dollars.

## Rules for using this data

1. No file measures whether anyone has a bank account at the tract level. ACS layers are correlates; FDIC survey rates stop at state and large metro.
2. Use tracts with CV over 40% for context, not rankings.
3. HMDA covers mortgages only. Do not use HMDA race, ethnicity or sex fields in any scoring or eligibility logic.
4. CFPB complaints are self-selected. Compare issue mix, not raw counts, and remember ZIPs cross county lines.
5. Deposits are booked to a branch, not to where customers live.

## Refresh

```
pip install requests pandas
export CENSUS_API_KEY=your_key      # https://api.census.gov/data/key_signup.html
python pull_sources.py --state 51 --county 153 --out ./data
python build/build_map.py            # rebuilds the map page from the CSVs in this folder
```

`pull_sources.py` could not be run from the build sandbox (no network to these APIs). Its FDIC filters were checked live; check the first rows of every other output before use.

## More related data worth pulling

- Bank On National Data Hub ZIP-level account data (St. Louis Fed): https://www.stlouisfed.org/community-development/bank-on-national-data-hub
- FDIC Household Survey custom tables (state and MSA underbanked rates, not pulled here): https://household-survey.fdic.gov/
- Fed SHED 2025 microdata (adult-level banking and finances): https://www.federalreserve.gov/consumerscommunities/shed.htm
- Boston Fed underbanked data tool: https://www.bostonfed.org/data/data-tools/underbanked-data-tool
