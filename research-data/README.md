# Research findings: Mastercard × partner banks, financial inclusion

Microsoft ASPIRE hackathon. Assembled October 12, 2026.

## What's here

| Path | What it is | Use it for |
| --- | --- | --- |
| `01_research_handoff/research_handoff.md` | Full Phase 1–4 research handoff: evidence tables, customer problems, bank business case, four opportunities, recommendation, open questions, source register | Deciding what the team builds and pitches |
| `01_research_handoff/unit_economics_model.py` | The illustrative per-account payback model behind Section 5 | Showing judges how payback flips on bank-held inputs |
| `02_county_data_prince_william_va/` | Real data for one county (FIPS 51153) from Census ACS, FDIC Summary of Deposits and branches, FDIC Household Survey, HMDA and CFPB complaints, 2021–2026 | The prototype's sample footprint |
| `02_county_data_prince_william_va/README.md` | Data dictionary, verification status of every file, usage rules | Read before using any CSV |
| `02_county_data_prince_william_va/pull_sources.py` | Re-pulls all sources for any county; gets ACS 2020–2024 with a Census key | Switching to another county or refreshing |
| `02_county_data_prince_william_va/build/prince_william_banking_access.html` | Tract heat map with reliability hatching, trends and tables. Opens offline in a browser | Demo and exploration |
| `02_county_data_prince_william_va/build/build_map.py` | Rebuilds the map from the CSVs | After changing data |

## Verification status (Oct 12, 2026)

- Verified against live sources: FDIC deposits 2021 and 2025, FDIC branch list, HMDA county totals 2021 and 2025, FDIC survey tables A.2–A.4.
- Not re-verified: ACS tract file (Census API needs a key), CFPB complaint files (API errors), HMDA top-lender file.
- Not run: `pull_sources.py` (the build sandbox had no access to these APIs). Check the first rows of each output.

## Known gaps to decide on

- ACS tract file is the 2019–2023 release; 2020–2024 is newest.
- FDIC state and metro *underbanked* rates (tables G.2/G.3) not pulled.
- Final status of the 2025 CRA rescission proposal and the current Reg II debit cap not confirmed.
- All profitability figures in the handoff are illustrative until a partner bank supplies its own inputs.

## Quick start

```
cd 02_county_data_prince_william_va
pip install requests pandas
python build/build_map.py                         # rebuild the map from the CSVs
python ../01_research_handoff/unit_economics_model.py
```
