# Collected data

**Purpose:** find real local-bank branches in or near underserved communities, so Mastercard can show each bank
evidence from its own market. **Period:** 2021+.

## Samples
Each metro has its own folders, with the same table names in each.

| Sample | Metro | Counties | Why |
|---|---|---|---|
| `dc` | Washington-Arlington-Alexandria (CBSA 47900) | 23 (DC/MD/VA/WV) | First test sample. Low-need comparison: 1.5% unbanked (2023) |
| `houston` | Houston-Pasadena-The Woodlands (CBSA 26420) | 10 (TX) | Showcase: 9.4% unbanked, about 307k households; 234 local-bank branches. Texas has the most unbanked households of any state |

- `processed/<sample>/` holds clean, typed tables as `.parquet` (for Fabric) and `.csv` (for inspection).
- `raw/<sample>/` (git-ignored) holds each source exactly as downloaded, next to a `.provenance.json` (URL, parameters, timestamp, row count, SHA-256).
- `raw/shared/` holds national files every sample reuses (CFPB bulk export, Census delineation and ZIP crosswalk, HMDA lender panels).
- Rebuild a sample by running the scripts in `scripts/` with `--sample <name>`, in this order:
  `fetch_geography` → `fetch_fdic` → `fetch_fdic_survey` → `fetch_hmda` → `fetch_cfpb` → `fetch_acs`.
  Add a new metro by adding an entry to `SAMPLES` in `scripts/common.py`.

The figures in the sections below are for the `dc` sample.

Keys that join everything: **`tract_geoid`** (11-digit census tract), **`county_fips`**, **`zip`/`zcta`**,
**`cert`** (FDIC bank ID), **`fed_rssd`** (Fed bank ID), **`lei`** (HMDA lender ID), **`uninum`** (FDIC branch ID).

---

## 1. FDIC National Survey of Unbanked and Underbanked Households: *who is unbanked, and why*
| Table | Grain | What's in it |
|---|---|---|
| `fdic_survey_rates` | year × geography × measure × breakdown | Unbanked / underbanked / fully banked rates; cash-only unbanked; interest in an account; main and all reasons for being unbanked. 2021 and 2023, for the US, DC/MD/VA/WV, and the DC metro. Income and household-type breakdowns. |

- **Why it matters:** it's the only source that measures banking status. Its rates by income and household type, applied to Census counts, estimate underbanked households per neighborhood.
- **Source:** the JSON API behind the FDIC's official survey tool. National figures match the published 2023 report exactly (4.22% unbanked, 14.18% underbanked).
- **Read with care:** `respondents` is the number of surveyed households behind each figure. The DC metro's 2023 unbanked rate (1.49%) rests on 34 unbanked households out of 889. Virginia's (0.87%) rests on 4. Small counts mean wide uncertainty.
- No race/ethnicity breakdowns were collected (SOW guardrail). The survey has no language variable.

## 2. FDIC BankFind: *which real branches serve these communities*
| Table | Grain | What's in it |
|---|---|---|
| `institutions` | bank | All 4,220 active FDIC-insured banks: assets, deposits, HQ, `fed_rssd`, **`target_issuer`** (assets < $10B = local issuer, Reg II-exempt) |
| `branches` | branch | All 1,196 offices in the metro: address, lat/long, **`tract_geoid`** (Census geocoder, 100% matched), service type, **`is_mdi`** (minority depository institution) |
| `branch_deposits` | branch × year | Summary of Deposits (June 30), 2021–2026, deposits in $000s |
| `branch_events` | event | Branch openings, closings, relocations and sales in the 23 counties since 2021 |

- **Why it matters:** these are the marketing opportunities. **161 full-service branches at 43 local banks** (7 of them MDIs, with 14 branches) out of 1,157 full-service branches in the metro.
- **Signal already visible:** 391 branch closings vs 130 openings since 2021. The branch count in deposit data fell from 1,383 (2021) to 1,170 (2026).
- 98% of target branches have 2026 deposit data; 85% have all six years (the rest opened or changed hands mid-period).

## 3. HMDA mortgage lending: *is mainstream credit reaching these neighborhoods*
| Table | Grain | What's in it |
|---|---|---|
| `hmda_loans` | application | Every mortgage application in the 23 counties, 2021–2025: lender (`lei`), tract, action (originated/denied/…), amount, income, rate spread, denial reasons. **Race, ethnicity, sex and age fields removed at ingest.** |
| `hmda_tract_year` | tract × year | Applications, originations, denials, denial rate, high-cost share, originations per 1,000 owner-occupied homes |
| `hmda_lenders` | lender | LEI → `fed_rssd` crosswalk (HMDA reporter panels 2021–2023), joins HMDA lenders to FDIC banks |

- **Why it matters:** it's observed behavior, not a survey. High denial rates, few loans and expensive loans mark credit deserts that independently corroborate the underserved estimate. It also shows whether a target bank already lends in a neighborhood.
- **Coverage:** 1,661,843 applications (record counts match the HMDA API totals for every year); 99.9% have a tract.
  97.5% of target-branch tracts have 2025 lending data. **39 of 43** target banks link to their HMDA filings via the crosswalk (24,199 applications).
- **Spread (2025, by tract):** denial rate median 22% (middle half 17–29%); high-cost share median 0.9%, up to 29%. That's enough variation to distinguish neighborhoods.
- **Read with care:** the 2024–2025 reporter panels aren't published yet, so lenders that first filed in 2024+ lack the crosswalk. The metro's division codes changed in 2024, so data is pulled by county. 2021 volume is inflated by the refinance boom.

## 4. CFPB Consumer Complaint Database: *where trust in financial companies breaks down*
| Table | Grain | What's in it |
|---|---|---|
| `complaints` | complaint | 322,998 complaints from ZIPs in the sample, 2021–2026: product, `product_group`, issue, company, response (narratives excluded) |
| `complaints_zip_year` | ZIP × year × product | Complaint counts for mapping |

- **Why it matters:** distrust is the #2 reason households stay unbanked. Complaints show where it concentrates and what goes wrong (fees, account closures, transfers).
- **Read with care:** 84% are credit-reporting complaints, largely mass-filed through credit-repair services. Use **`product_group = banking_access`** (12,751 complaints: checking/savings, money transfer, prepaid) as the trust signal. ZIP-masked complaints (51,620) were dropped. Volumes rise sharply after 2023 nationally, so compare areas within a year, not across years.

## 5. Census ACS 5-Year (2020–2024): *who lives in each neighborhood*
| Table | Grain | What's in it |
|---|---|---|
| `acs_tracts` | tract | Income brackets (B19001), median income (B19013), poverty ratio (C17002), household type (B11012), families with children (B11003), limited-English households (C16002), each with margin of error |
| `acs_variables` | variable | Code → label dictionary for Power BI |

- **Why it matters:** the only source covering every neighborhood. Combined with the FDIC survey rates, it gives the estimated underbanked households near each branch. Language and household type support outreach planning; they are not targeting criteria.
- **Coverage:** 1,464 tracts, 2.37M households; 100% of HMDA 2025 tracts and 98% of target-branch tracts match.
- **Read with care:** single income brackets are noisy per tract (92% of tracts have a coefficient of variation above 0.4 on the under-$10k bracket). Combine brackets or aggregate the tracts around a branch; margins of error are stored next to every estimate.
- Requires `CENSUS_API_KEY` in `.env`.

## Geography helpers
| Table | What's in it |
|---|---|
| `sample_counties` | The 23 counties of the DC metro (OMB 2023 delineation) |
| `zcta_tract` | ZIP (ZCTA) → census tract overlap (Census 2020 relationship file), used to place complaints on tracts |
