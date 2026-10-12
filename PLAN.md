# DAPA — Data Sources

**Goal:** find real local-bank branches worth marketing to, meaning branches that sit in or near underserved communities, so that
**Mastercard can prove to each bank** that the community around its branches is worth investing in.
(Per the SOW: Mastercard already finds communities. The bottleneck is convincing local banks, which won't act on forecasts
or promises. They need evidence from their own market.)
**How the data serves it:** public data documents the underserved community. Bank data ties that evidence to a specific
bank's real branches. The output is a branch-by-branch evidence base for Mastercard's pitch to each bank.
**Guardrail (SOW §4, §15):** target by place and need, never by race or ethnicity. Race/ethnicity fields in HMDA and the
FDIC survey are not collected for targeting. Language and household composition are outreach context only.

**Sample:** Washington DC metro (DC, MD, VA, WV). **Period:** 2021 onward (post-COVID). All sources tested live 2026-10-12.

---

## 1. Census ACS 5-Year (American Community Survey)
- **What it is:** the Census Bureau's annual household survey, published for every census tract (~4,000 people).
- **What we collect:** income (brackets, median, poverty ratio), household composition (household and family type),
  language (limited-English households). Each comes with a margin of error.
- **Why it matters:** it's the only dataset that describes *every neighborhood*. It tells us how many low-income,
  single-parent and limited-English households live around each branch, the groups the FDIC finds most likely to be unbanked.
- **Role in the project:** the foundation of the community map. Every other dataset is joined to these tracts.
- **Details:** 2020–2024 is the newest release; tract data only comes as 5-year pools. API key required. It never asks about bank accounts.

## 2. FDIC National Survey of Unbanked and Underbanked Households
- **What it is:** the FDIC's survey of ~30,000 households, run every two years with the Census Bureau.
- **What we collect:** unbanked and underbanked rates by income, household type, language, state and the Washington metro;
  reasons for not having an account (minimum balances, distrust, fees); interest in opening one.
- **Why it matters:** it's the only dataset that measures banking status. Applying its rates to the ACS counts gives an
  estimate of unbanked and underbanked households in each neighborhood. The reasons explain *why* people stay out of banks.
- **Role in the project:** turns "low-income area" into "estimated underbanked households here," which is the core evidence for Mastercard.
- **Details:** 2023 is the latest (2021 for comparison); 2025 results are not yet published. No API, so tables are entered by hand
  with a source link per row. It covers states and large metros only, so neighborhood figures are labeled as estimates.

## 3. FDIC BankFind (branches and deposits)
- **What it is:** the FDIC's registry of every insured bank and branch.
- **What we collect:** every branch's location and type, which bank owns it and its size, deposits held at each branch (2021–2026),
  branch openings and closings since 2021, and minority-owned bank status.
- **Why it matters:** these are the **real branches** that become marketing opportunities. Deposits show how established each branch is.
  Recent closures show communities losing access.
- **Role in the project:** connects each underserved community to the specific local banks (under $10B, not national banks) that could serve it.
- **Details:** no key needed. The newest deposit data (June 2026) is already available. Filter by branch location, not bank headquarters.

## 4. HMDA (Home Mortgage Disclosure Act) lending data
- **What it is:** loan-level mortgage applications reported by ~4,800 lenders each year.
- **What we collect:** applications, approvals, denials and loan pricing by census tract and by lender.
- **Why it matters:** it shows where mainstream credit isn't reaching (high denial rates, few loans, expensive loans).
  It's observed behavior, not a survey, so it independently confirms the underserved estimate.
- **Role in the project:** strengthens the case for each community. It also shows whether a nearby bank already lends there.
- **Details:** 2021–2025 available, no key. The DC metro's area codes changed in 2024, so filter by state and county.
  Lenders use a different ID than the FDIC, so a crosswalk links them.

## 5. CFPB Consumer Complaint Database
- **What it is:** public complaints consumers file against financial companies (18M+ records).
- **What we collect:** complaints since 2021 by ZIP code: product (checking/savings, money transfer, credit cards), issue, company.
- **Why it matters:** distrust is the #2 reason people stay unbanked. Complaint volume and type show where trust in banks is
  breaking down and what problems (fees, closed accounts) people are running into.
- **Role in the project:** adds a trust signal to each community, and tells a bank what to get right when it approaches that community.
- **Details:** no key. Only available by ZIP code, so it's mapped to tracts with a Census ZIP-to-tract file. Large banks dominate the company field.

---

## How the datasets fit together
| Dataset | Answers | Links by |
|---|---|---|
| Census ACS | Who lives here? | Census tract |
| FDIC Survey | How likely are they to be unbanked or underbanked, and why? | Income/household group → applied to tracts |
| HMDA | Is credit reaching them? | Census tract |
| CFPB | Do they trust banks? | ZIP → tract |
| FDIC BankFind | Which real branches serve them? | Branch location → tract |

**Result:** a list of real local-bank branches, each with documented evidence about its surrounding community. Mastercard
brings this to the bank that owns those branches: proof from the bank's own market, not a forecast.

Needed to start collecting: a Census API key.
