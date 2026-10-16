# Mastercard × Partner Banks: Financial Inclusion Research Handoff

Oct 12, 2026 · @Team

## How to read this handoff

Every substantive claim carries one of five labels so the team never pitches an inference as a fact.

| Label | Meaning |
| --- | --- |
| **Observed** | Stated directly in a published source or returned by a live API call we ran |
| **Estimate** | A survey or modeled statistic with sampling error (FDIC, ACS, Fed SHED) |
| **Inference** | Our reasoning from observed or estimated evidence |
| **Hypothesis** | Plausible but untested; needs Mastercard, bank, or customer validation |
| **Illustrative** | Made-up numbers that show how a calculation works; never a projection |

**Research date:** October 12, 2026. **Live checks:** FDIC BankFind `/locations`, `/sod` and `/demographics` were queried and returned real JSON. The Census API now requires a key, so ACS table IDs are standard tables named from general knowledge, not checked against `variables.json`; confirm them there before coding. The FDIC Household Survey interactive tool (household-survey.fdic.gov) is a JavaScript app our fetcher could not render; figures come from FDIC's published 2023 report pages instead.

**Three distinctions that must survive into the pitch.** *Unbanked* = no one in the household has a bank or credit union account. *Underbanked* = has an account but used a nonbank transaction or credit service in the past year. Census demographics never measure either; they are only correlates.

## 1. Executive Summary

**Banks don't lack maps of underserved communities; they lack bank-specific proof that serving them pays back. Microsoft's best contribution is a transparent business-case builder that turns public data plus a bank's own inputs into a payback answer and a small, stoppable pilot.**

- **The market is real but smaller than headlines.** 5.6M households (4.2%) are unbanked and 19.0M (14.2%) underbanked (FDIC 2023). Only 29.1% of unbanked households want an account, so the near-term pool is roughly 1.6M. The 19M underbanked already bank somewhere and leak spending to nonbanks.
- **The top barrier is fixable product design.** A third of unbanked households cite fees or minimum balances as the main reason. Distrust is second and least understood.
- **Low-cost accounts work behaviorally.** 14M+ Bank On accounts are open; 84% went to customers new to the bank; closures fell to 15% (31% at community banks); holders average $1,273 and 33 debit transactions a month.
- **Profitability evidence is missing.** No public source reports per-account profit, CAC or cross-sell for these accounts at a named bank. Our illustrative model shows payback flips on four bank-held inputs: servicing cost, CAC, retention and cross-sell.
- **Timing favors action.** Federal paper checks ended Sept 30, 2025, pushing benefit recipients onto electronic rails; Direct Express (\~3.4M, on Mastercard's network) is a natural graduation pool.
- **Regulatory pull is weaker.** The modernized CRA rule faces rescission and the federal overdraft cap was repealed, so the case must stand on commercial value.

**Recommendation:** build O1, a Partner-Bank Business Case Builder (Fabric + Power BI, with Foundry drafting a cited memo), demoed on one real bank footprint. Validate with 2–3 bank finance leads, then a 6-month test-and-control pilot.

**Limits:** Census data never measures banking status, FDIC rates stop at state and large-metro level, and all profit figures here are illustrative.

## 2. High-Value Evidence (Phase 1)

**The three sources answer different questions and cannot be merged naively.** The FDIC survey says *who* is unbanked and *why*, but only down to state and large metro. ACS says *where* the correlated conditions sit, down to tract and block group. BankFind says *which banks* are physically present and how much they hold. None of them measures account ownership at the tract level.

### Source A: Census ACS 5-Year (newest = 2020–2024, API page dated Jan 29, 2026)

| Dataset / variable | Finding or use | Geography, period | Why Mastercard cares | Why banks care | Limitations | URL |
| --- | --- | --- | --- | --- | --- | --- |
| ACS5 Detailed Tables, `api.census.gov/data/2024/acs/acs5` | Newest 5-year release; Detailed Tables reach block group, Subject Tables and Data Profiles reach tract, Comparison Profiles only reach place/county subdivision (Observed) | US to block group; pooled 2020–2024 | One consistent nationwide base layer for any tract-level model | Tracts are the unit of CRA assessment-area analysis | Pooled 5-year average, not a 2026 snapshot; API key now mandatory; tract MOEs often large | [ACS 5-year API](https://www.census.gov/data/developers/data-sets/acs-5year.html) |
| Income: `B19013` median HH income, `B19001` income brackets, `C17002` ratio of income to poverty | Households under $15k had a 21.8% unbanked rate in 2023 (FDIC), so bracket counts are the strongest single proxy (Inference) | Tract, block group | Sizes the low-income household base per tract | Defines LMI tracts banks already track | Proxy only; never measures account ownership | [Variables](https://api.census.gov/data/2024/acs/acs5/variables.html) |
| Household type: `B11003` / `B11012` single-parent families | FDIC: single-parent HHs 12.3% unbanked vs 2.3% for married couples with kids (Estimate) | Tract | Points outreach at a high-need segment | Indicates product need (low-cost, mobile, bill pay) | Aggregate targeting only; never an eligibility input | [Variables](https://api.census.gov/data/2024/acs/acs5/variables.html) |
| Disability: `B18101` disability by age | FDIC: working-age HHs with a disability 11.2% unbanked vs 3.7% without (Estimate) | Tract | Accessibility requirements for any onboarding flow | ADA and UDAAP exposure in product design | Protected-class sensitivity; aggregate use only | [Variables](https://api.census.gov/data/2024/acs/acs5/variables.html) |
| Benefits: `B22010` SNAP receipt, `B19058` public assistance or SNAP | Benefit receipt is a known “bankable moment”: 34.9% of recently banked HHs credited a government payment (FDIC 2021) (Estimate) | Tract | Ties to Direct Express and paper-check phase-out | Recurring direct deposit is what makes an account primary | Receipt ≠ unbanked; SNAP via EBT, not bank rails | [Variables](https://api.census.gov/data/2024/acs/acs5/variables.html) |
| Digital access: `B28002` internet subscription type, `B28001` device types | FDIC: 48.3% of banked HHs use mobile as primary channel; 54.5% of underbanked do (Estimate) | Tract | Decides mobile-first vs assisted onboarding by area | Determines branch vs digital cost-to-serve | Device ownership ≠ mobile-banking adoption | [Variables](https://api.census.gov/data/2024/acs/acs5/variables.html) |
| Language: `C16002` limited-English households | Hispanic HHs were 14.8% of all HHs but 33.4% of unbanked (FDIC 2023) (Estimate) | Tract | Language of materials and support | Staffing and disclosure translation cost | Language is not a banking measure | [Variables](https://api.census.gov/data/2024/acs/acs5/variables.html) |
| Cost stress & mobility: `B25070` rent burden, `B25003` tenure, `B08201` vehicles available | Context for minimum-balance barrier and real travel time to a branch (Inference) | Tract | Explains *why* an area is cash-reliant | Branch distance matters more where cars are scarce | Indirect; needs local validation | [Variables](https://api.census.gov/data/2024/acs/acs5/variables.html) |

### Source B: FDIC BankFind Suite API (live, no key currently required)

| Endpoint | Finding or use | Geography, period | Why Mastercard cares | Why banks care | Limitations | URL |
| --- | --- | --- | --- | --- | --- | --- |
| `/banks/locations` | Every insured office with lat/long, `SERVTYPE`, `CBSA`, `CERT`. Live call returned 26 offices for Manassas, VA; index rebuilt Oct 9, 2026 (Observed) | Point-level, current | Map partner-bank vs competitor presence per tract | Shows white space and overlap in footprint | Presence ≠ access: no hours, fees, languages or products. No tract field in sample; geocode lat/long to tracts | [Docs](https://api.fdic.gov/banks/docs/) |
| `/banks/sod` Summary of Deposits | Branch-level deposits (`DEPSUMBR`, $000s) as of June 30. 2025 data loaded: 1,517 Virginia branch records; index Sept 18, 2026 (Observed) | Branch, annual | Which partner bank dominates which local deposit markets | Deposit-share benchmark against local competitors | Deposits are booked to a branch, not to where customers live; annual only | [Docs](https://api.fdic.gov/banks/docs/) |
| `/banks/institutions` + `/banks/financials` | Asset size, deposits, ROA, NIM and other Call Report items, quarterly | Institution, quarterly | Segments partners (community vs large) to tailor the pitch | Peer benchmarking | Institution-level; no product-line or low-balance-account economics | [Docs](https://api.fdic.gov/banks/docs/) |
| `/banks/demographics` | Institution office metadata: `OFFTOT`, metro/micro flags, `CBSANAME`, minority depository code `MNRTYCDE` (Observed) | Institution, quarterly history | Identifies MDI partners and community footprint | Peer and MDI context | Not consumer demographics despite the name; first record returned was 1984, so sort by `REPDTE` | [Docs](https://api.fdic.gov/banks/docs/) |
| `/history`, `/failures`, `/summary` | Branch openings and closings over time; failures; aggregates | Institution, historical | Branch-closure trends flag newly underserved areas | Shows exit and entry decisions of peers | Event logs need cleaning to compute tract-level net change | [Docs](https://api.fdic.gov/banks/docs/) |

### Source C: FDIC National Survey of Unbanked and Underbanked Households (newest = 2023, published Nov 2024)

| Finding | Value | Geography, period | Why Mastercard cares | Why banks care | Limitations | URL |
| --- | --- | --- | --- | --- | --- | --- |
| Unbanked rate | 4.2% of HHs, \~5.6M (Estimate) | National, June 2023 | Core inclusion target | Small, hard-to-reach segment | Not statistically different from 2021 (4.5%) | [2023 Exec Summary](https://fdic.gov/household-survey/2023-fdic-national-survey-unbanked-and-underbanked-households-executive-summary) |
| Underbanked rate | 14.2% of HHs, \~19.0M (Estimate) | National, 2023 | Larger pool already on bank rails | **Existing customers** leaking wallet share to nonbanks | Not comparable to 2021 because a question changed | Same |
| Interest in an account | Only 29.1% of unbanked HHs very/somewhat interested; 70.9% not (Estimate) | National, 2023 | Realistic addressable unbanked market is \~1.6M HHs, not 5.6M (Inference) | Pitch must segment the willing from the distrustful | Stated intent, not behavior | Same |
| Main reasons for being unbanked | Minimum balance: 42.3% any / 23.3% main. Distrust: 15.7% main. Fees or minimum balance combined: 33.4% main (Estimate) | National, 2023 | A third of the barrier is product design that banks control | Bank On-style accounts address it directly | Multi-select; small subgroup samples | Same |
| What differs by interest | ID requirements cited by 16.4% of interested vs 11.7% of uninterested; distrust and privacy dominate the uninterested (Estimate) | National, 2023 | Two segments need two strategies | ID flexibility (ITIN, consular ID) is a lever | Descriptive only | Same |
| Cash-only unbanked | 66.2% of unbanked HHs; 2.8% of all HHs (Estimate) | National, 2023 | The hardest-to-reach core of the brief | Highest servicing cost | Small sample | Same |
| Nonbank substitutes | Unbanked users of prepaid cards: 90.7% use them for bills, income or saving; of online payment apps: 71.5% (Estimate) | National, 2023 | Card rails already function as the on-ramp | Shows the jobs a starter account must do | Users only, not all unbanked | Same |
| Credit gap | 78.4% of unbanked and 17.4% of underbanked HHs had no mainstream credit (Estimate) | National, 2023 | Credit-building is a credible next product | Cross-sell path, with risk | No credit-score data in survey | Same |
| Underbanked BNPL distress | 20.8% of underbanked BNPL users missed or paid late vs 8.1% of fully banked (Estimate) | National, 2023 | Responsible-credit design need | Credit-loss risk signal | Small base (9.7% use BNPL) | Same |
| Channel | Mobile primary for 48.3% of banked HHs; teller use higher for lower-income, older and non-metro HHs (Estimate) | National, 2023 | Assisted channels still matter for the target | Cost-to-serve differs by segment | Primary channel only | Same |
| Geography available | Nation, states, large MSAs; often pooled 2019–2023 with MOEs, e.g. Colorado 4.5% ±1.6 (Estimate) | State, large MSA | Cannot be pushed down to tracts | Bank market areas rarely match MSAs | No county or tract estimates | [Data & downloads](https://www.fdic.gov/household-survey/data-downloads-and-resources) |
| 2025 survey | Fielded June 2025 with new questions on opinions about banks; **no results published as of Oct 12, 2026** (Observed) | National, state, MSA | Trust data will sharpen the pitch | Same | 2023 results took 17 months to publish | [OMB filing](https://omb.report/icr/202505-3064-002/doc/158020901.pdf) |

### Added sources: HMDA and CFPB complaints (pulled for Prince William County, VA, FIPS 51153)

| Dataset / variable | Finding or use | Geography, period | Why Mastercard cares | Why banks care | Limitations | URL |
| --- | --- | --- | --- | --- | --- | --- |
| HMDA Data Browser API, `/v2/data-browser-api/view/aggregations` | County mortgage decisions fell from 40,050 (2021) to 14,728 (2025); denial rate rose from 14.8% to 22.2%. Both years verified live (Observed) | County, 2021–2025; tract-level via CSV download | Shows which partner banks lend in LMI tracts and where credit access is tight | CRA lending benchmark against local peers | Mortgages only, says nothing about deposit accounts. 2021 inflated by refinancing. Race, ethnicity and sex fields must stay out of any scoring | [HMDA Data Browser](https://ffiec.cfpb.gov/data-browser/) |
| HMDA `census_tract`, `tract_to_msa_income_percentage` | 40 of 93 county tracts are LMI (tract income under 80% of metro) (Observed in pulled file) | Tract, 2025 | Official LMI flag to line up with ACS need layers | Same definition examiners use under CRA | FFIEC income vintages lag ACS | [HMDA Data Browser](https://ffiec.cfpb.gov/data-browser/) |
| CFPB Consumer Complaint Database API | 800 complaints from county ZIPs, Jan 2021–Oct 12, 2026: checking/savings 559, money transfer 229, prepaid 12. Top issue: managing an account (313). Volume jumped from 114 (2024) to 274 (2025) (Observed in pulled file; not re-verified live) | ZIP, 2021–2026 | Direct evidence on trust and account-management pain; Cash App (71) and Chime (31) among top companies shows nonbank use | Account closures, fee disputes and fraud are pain points to design out of a starter account | Self-selected, not a sample; ZIPs cross county lines; counts track company size. Cause of the 2025 jump unknown | [Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/) |
| FDIC Household Survey tables A.3, A.4 | Virginia unbanked 0.9% (90% CI 0.4–2.1); DC metro 1.5% (1.0–2.3); 2023 (Estimate) | State, MSA, 2019–2023 | Places the county in a low-unbanked market, so underbanked leakage may be the bigger prize there | Sets realistic expectations for unbanked conversion | Wide CIs; underbanked state/MSA tables not retrieved | [Appendix tables](https://fdic.gov/household-survey/2023-fdic-national-survey-unbanked-and-underbanked-households-appendix-tables) |

**Heat-map reliability check (Observed).** In the county's 2019–2023 ACS file, 71 of 92 tracts have a coefficient of variation above 40% for the under-$25k income share, and 87 of 92 for the no-vehicle share. Tract heat maps built from these fields need reliability hatching, or they rank noise.

### Unanswered business questions after Phase 1

1. **Unit economics.** What does a low-balance starter account cost a partner bank per year, and what revenue does it generate? No public source answers this for a specific bank.
2. **Conversion.** Of the \~1.6M interested unbanked HHs, how many can a single bank in a single market realistically convert, and at what acquisition cost?
3. **Underbanked leakage.** How much of an existing customer's wallet goes to check cashers, money orders and remittance shops, and could the bank capture it?
4. **Local rates.** What is the unbanked share in a partner bank's actual footprint? Only modeled small-area estimates exist, and they must carry uncertainty bands.
5. **What already exists.** Does the partner bank already offer a Bank On-certified account? If so, the gap is adoption and activation, not product.
6. **Decision criteria.** What hurdle rate, payback period and evidence standard does each partner bank's investment committee use?

## 3. Modern Research Findings (2024–2026)

**The strongest new evidence is behavioral, not demographic: 14M+ low-cost Bank On accounts are open, actively used and churning less every year, and the federal paper-check phase-out has created a once-a-decade “bankable moment” on Mastercard's own rails.** Meanwhile, two regulatory levers banks once relied on for motivation (modernized CRA, a federal overdraft cap) have both been withdrawn, so the business case now has to stand on commercial value.

### New developments

| Development | What the evidence shows | Date | Implication for the pitch | Label |
| --- | --- | --- | --- | --- |
| [Fed SHED 2025](https://www.federalreserve.gov/publications/files/2025-report-economic-well-being-us-households-202605.pdf) | 94% of adults banked; only 77% of adults under $25k income. 63% could cover $400 with cash or equivalent. Well-being fell for low-income, young and Black adults. 11% of BNPL users triggered an overdraft or NSF fee | Fielded Oct 2025, pub. May 2026 | The low-income gap is not closing; adult-level rate (6% unbanked) differs from FDIC's household rate, so never mix them | Estimate |
| [Bank On National Data Hub, 2024 data](https://www.stlouisfed.org/community-development/bank-on-national-data-hub/bank-on-report-2024) | 23M+ certified accounts ever opened, 14M+ open; 4.8M opened in 2024; 84% opened by customers new to the bank; closures fell from 21% to 15%; avg balance $1,273; 33 debit transactions per holder per month; 39% use direct deposit | 2024 data, pub. Nov 2025 | The best public proof that low-cost accounts acquire new customers who transact. Community-bank closures ran 31% vs 15% overall, so small partners face a retention problem | Observed (voluntary reporting by 45 FIs) |
| [Federal paper-check phase-out](https://www.stlouisfed.org/on-the-economy/2026/feb/tracking-banking-access-using-bank-on-national-data-hub) (EO 14247) | Treasury stopped most paper checks for federal payments on Sept 30, 2025; unbanked recipients are routed to Direct Express. Hardship waivers remain | Effective Sept 30, 2025 | Hundreds of thousands of benefit recipients had to choose a payment rail; many default to prepaid | Observed |
| [Direct Express](https://www.paymentsjournal.com/as-paper-checks-sunset-fifth-third-bank-scales-up-prepaid-program/amp/) | \~3.4M cardholders, most without a bank account; Mastercard is the network; Fifth Third became financial agent Sept 2025, enrolling from 2026 | 2025–2026 | A large, identifiable pool already on Mastercard rails that a partner bank could graduate to a full account | Observed |
| [CRA rescission proposal](https://www.federalreserve.gov/newsevents/pressreleases/bcreg20250716a.htm) | Agencies proposed rescinding the 2023 modernized rule and returning to the 1995 framework; 1995 rules still apply | Proposed July 16, 2025 | CRA credit is a weaker motivator than in 2023 plans; don't lead with compliance. Final status not confirmed here | Observed |
| [Overdraft rule repeal](https://www.everycrsreport.com/reports/IN12513.html) | Congress voided the CFPB $5 overdraft cap via the Congressional Review Act, signed May 9, 2025 | 2025 | Large banks keep overdraft revenue, so a no-overdraft account looks less attractive to them unless other revenue is shown | Observed |
| [Mastercard Inclusive Growth Score](https://www.mastercard.com/news/perspectives/2023/inclusive-growth-score-for-everyone-to-win-you-have-to-keep-score) | Tract-level score for every U.S. census tract, blending public data with aggregated Mastercard transaction data | Available since 2019, all tracts by 2023 | Confirms the interview: Mastercard already *finds* communities. Rebuilding a heat map would duplicate an existing asset | Observed |
| [Mastercard 2025 Impact Report](https://ffnews.com/news/mastercard-surpasses-1-billion-digital-inclusion-goal-and-slashes-emissions-in-2025-impact-report) | Reports 1.06B people connected to the digital economy since 2015 | July 2026 | Mastercard has global scale; the gap is U.S. partner-bank conversion | Observed (company-reported, secondary source) |

### Case studies with measured outcomes

| Program | Original problem | Intervention | Measured results | Why it worked or didn't | Transfers to partner-bank model? |
| --- | --- | --- | --- | --- | --- |
| [FDIC Model Safe Accounts Pilot](https://www.fdic.gov/consumer-research/model-safe-accounts-pilot) (9 banks, 2011) | Banks doubted low-cost accounts could be viable | Checkless, card-based, no-overdraft transaction and savings accounts | 3,545 accounts opened; 81% of transaction and 95% of savings accounts stayed open; most banks said cost to serve was equal or lower | Low risk and electronic-only servicing kept costs down. Banks struggled to *market* the accounts | **Yes**: proves viability, but shows marketing and front-line training are the bottleneck. Small scale; 15 years old |
| [Bank On certified accounts](https://www.stlouisfed.org/community-development/bank-on-national-data-hub/bank-on-report-2024) (500+ institutions) | Fees, minimum balances and overdraft kept people out | National Account Standards: ≤$25 to open, no overdraft, no low-balance fees | See BOND Hub row above; 84% new-to-bank; usage rising yearly | Standardized product plus local coalitions and a public scorecard | **Yes**: the product question is largely solved. What's missing is bank-specific profitability evidence |
| Direct Express (Treasury, 2008–) | Unbanked benefit recipients cashing paper checks | Treasury-sponsored prepaid Mastercard | \~3.4M cardholders | Default electronic rail when no account exists | **Partly**: a graduation pathway from prepaid to a full account is untested at scale |
| [Bank On 2017 pilot](https://www.stlouisfed.org/open-vault/2019/january/affordable-banking-movement) (4 large banks) | No data on how low-cost accounts are used | Shared standardized usage data | Estimated \~$200/yr saved per holder vs check cashing and money orders | Aggregated reporting created credibility | **Yes**: the template for a shared measurement layer |

**What the case evidence does not show.** No public source reports per-account profitability, cross-sell rates or customer lifetime value for low-cost accounts at a named bank. Every profitability claim in the pitch must therefore come from the partner bank's own data or be labeled illustrative.

## 4. Customer Problems (ranked by evidence strength)

**Cost and minimum-balance barriers are the best-evidenced problem and the one banks can fix fastest; distrust is the second-largest barrier but has almost no tested remedy.** Ranking weighs how strongly the evidence supports the problem and whether a partner bank can act on it.

| Rank | Barrier | Evidence | Strength | Can a bank fix it? | Still needs customer interviews? |
| --- | --- | --- | --- | --- | --- |
| 1 | **Cannot afford minimum balances or fees** | 42.3% of unbanked cite minimum balance (23.3% as main reason); 33.4% cite a fee or balance reason as main (FDIC 2023) | Strong (national survey, repeated since 2009) | Yes. Bank On standards (≤$25 open, no overdraft, no low-balance fee) remove it | Low: problem is clear |
| 2 | **Do not trust banks / prefer privacy** | Distrust 15.7% main reason; privacy and distrust dominate the 70.9% who are *not interested* in an account (FDIC 2023) | Strong that it exists; weak on what fixes it | Partly. Trusted messengers, transparent fees, no surprise closures | **High**: 2025 FDIC survey adds opinion-of-banks questions; results pending |
| 3 | **Income too low or volatile for a fee-based product** | Unbanked rate 21.8% for HHs under $15k; 34% of adults under $25k missed a bill last month; 4 in 10 adults under $50k can't cover $100 from savings (Fed SHED 2025) | Strong | Partly. Free accounts, early direct-deposit access, fee caps | Medium |
| 4 | **Leakage to costly nonbank services among the *underbanked*** | 14.2% of HHs underbanked; money orders, check cashing, remittances used for bills and income; \~$200/yr spent on check cashing and money orders (2017 Bank On pilot estimate) | Strong on usage; moderate on cost | Yes. Bill pay, P2P, low-cost remittance, early wage access | Medium: which service a bank should replace first |
| 5 | **Missing ID or documentation** | Cited by 16.4% of *interested* unbanked vs 11.7% of uninterested (FDIC 2023) | Moderate (multi-select, small base) | Yes, within BSA/CIP rules: accept ITIN, consular and municipal IDs | Medium: varies by bank's CIP policy |
| 6 | **Past banking history blocks** (e.g., ChexSystems reports) | 13.2% / 11.9% cite past banking or credit problems; CFE Fund and NCLC document screening-database exclusions | Moderate | Yes. Second-chance accounts, lighter screening for no-overdraft products | Medium |
| 7 | **No mainstream credit, so no credit score** | 78.4% of unbanked and 17.4% of underbanked HHs had no mainstream credit (FDIC 2023) | Strong | Yes, as a *second* product after the account (cash-flow underwriting) | Medium: appetite and risk vary |
| 8 | **Branch access and inconvenient locations** | 13.8% / 17.3% cite inconvenient locations; teller use higher for lower-income, older and rural HHs | Moderate; real but secondary | Partly. Mobile onboarding, retail-agent cash-in, extended hours | High: travel time is local |
| 9 | **Digital access and skills** | Mobile is the primary channel for 54.5% of *underbanked* HHs, so digital is not the main barrier for them; device gaps persist for older and disabled HHs | Mixed | Yes, via assisted onboarding | High |
| 10 | **Financial literacy** | Commonly asserted; no source we reviewed ranks it as a leading cited reason | **Weak** | Unclear | **High**: treat as a hypothesis |

**What meaningful problems could banks solve that would also sustain adoption? (Inference)** The behavioral data point to three: remove fee and balance risk (rank 1), become the account where income lands (direct deposit, benefits) so it becomes primary, and replace one costly nonbank service the customer already pays for (rank 4). Each creates a reason to keep using the account, which is what drives bank value.

## 5. Partner-Bank Business Case

**A bank executive will fund this when shown a per-account payback period from the bank's own costs, a credible retention curve, and a small controlled pilot that can be stopped.** Public data can size the market and show behavior; it cannot show any one bank's profitability. Our illustrative model below shows the answer flips from loss to gain on four bank-specific inputs: servicing cost, acquisition cost, retention, and cross-sell.

### Metrics a credit committee needs

| Metric | Why it decides funding | Public proxy available? | Requires private partner-bank data? |
| --- | --- | --- | --- |
| Addressable households in the bank's footprint | Sizes the prize | Yes: ACS + FDIC state/MSA rates, as a modeled range | No (but must be labeled modeled) |
| Customer acquisition cost (fully loaded) | Largest upfront cost | Weak: vendor estimates of $200–$400 per checking account; credit-union member cost \~$428 (industry reports) | **Yes** |
| Activation rate (first deposit, first debit within 90 days) | Inactive accounts nearly double effective CAC | No | **Yes** |
| Primacy rate (direct deposit or recurring benefit deposit) | Primary customers hold far more deposits and stay longer | Partly: 39% of Bank On holders use direct deposit | **Yes** |
| Average balance and deposit funding value | Main revenue line on a no-fee account | Partly: $1,273 avg Bank On balance (aggregate) | **Yes** (bank's own funds-transfer price) |
| Debit interchange per transaction | Second revenue line | Partly: 33 txns/month, \~$38 avg ticket (BOND); Reg II caps covered issuers | **Yes** (bank's actual rates and exemption status) |
| Annual servicing cost per account | Decides whether the account breaks even | No | **Yes** (branch vs digital cost-to-serve) |
| Fraud and charge-off losses | Risk committee's first question | Partly: FDIC pilot banks reported low risk | **Yes** |
| 12- and 24-month retention | Spreads CAC over more years | Partly: 15% annual closure overall, 31% at community FIs (BOND 2024) | **Yes** |
| Cross-sell rate (savings, secured card, small-dollar loan) | Converts a break-even account into a relationship | No public evidence | **Yes** |
| Customer outcomes: fees avoided, savings balance, credit-file creation | Needed for Mastercard's inclusion goals and reputation | Partly: \~$200/yr avoided check-cashing cost (2017 estimate) | **Yes** (anonymized cohort data) |

### Illustrative ROI model (not a projection)

Per-account net present value over five years:

```latex
\mathrm{NPV}_5 = \sum_{t=1}^{5} \frac{(R - C)\,(1-c)^t}{(1+d)^t} - \mathrm{CAC}
```

where R = annual revenue (balance × funding value + debit transactions × interchange + cross-sell margin), C = servicing cost + losses, c = annual closure rate, d = discount rate (10%). We ran four scenarios in code. Only the balance ($1,273), transactions (33/month), average ticket ($38.12) and closure rates (15% and 31%) come from BOND Hub; **every other input is invented to show sensitivity.**

| Scenario (Illustrative) | Servicing + losses / yr | CAC | Closure | Cross-sell margin / yr | Net / yr | 5-yr NPV | Payback |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A. Branch-served, bank >$10B | $160 | $250 | 15% | $0 | −$34 | −$333 | Never |
| B. Digital-first, bank >$10B | $70 | $250 | 15% | $0 | $56 | −$111 | Beyond 5 yrs |
| C. Digital + Mastercard partner channel + cross-sell | $70 | $120 | 15% | $40 | $96 | **+$118** | Year 2 |
| D. Community bank (debit-exempt), digital | $70 | $250 | 31% | $0 | $157 | −$11 | Year 7 |

Assumptions: 2.5% funding value on balances; covered-issuer interchange ≈ $0.24 per transaction under the Reg II cap structure (21¢ + 5 bps + 1¢); exempt-issuer interchange ≈ $0.49 (assumed). Verify the current Reg II cap before use.

**What the model tells the team (Inference).** The account alone rarely pays back at a branch-served large bank. It can pay back when servicing is digital, acquisition comes through a cheaper channel such as a Mastercard-convened partner or benefit-graduation program, and a second product follows. Community banks earn more per transaction but lose more customers, so retention is their lever. These are exactly the inputs only the partner bank holds, which is why the deliverable must be a model the bank fills in, not a number we assert.

## 6. Business Opportunities

**Four concepts survive the evidence test; the one that best fits the interview is a bank-specific business-case builder, because the stated friction is persuading banks, not finding communities.** None of the four rebuilds Mastercard's existing heat maps or Inclusive Growth Score.

- **O1. Partner-Bank Business Case Builder.** A transparent model that sizes the opportunity in one bank's footprint and computes payback from that bank's own inputs, with every number traced to its source.
- **O2. Inclusion Pilot Evidence Network.** A standard pilot design and shared measurement layer (test vs control cohorts) so Mastercard can show banks real, aggregated results from peer banks.
- **O3. Benefits-to-Bank Graduation.** Move prepaid benefit recipients (Direct Express, post paper-check) and payroll-card users into a partner bank's low-cost account.
- **O4. Underbanked Wallet Recapture.** Help banks spot existing customers who pay check cashers, money-order or remittance shops and offer an in-bank replacement.

### Ten-point analysis

| Dimension | O1. Business Case Builder | O2. Pilot Evidence Network | O3. Benefits-to-Bank Graduation | O4. Wallet Recapture |
| --- | --- | --- | --- | --- |
| **Problem** | Banks lack bank-specific, credible ROI; Mastercard lacks a repeatable way to show it | No public per-account profitability evidence exists (Section 3) | Benefit recipients default to prepaid; acquisition is expensive | 19.0M underbanked HHs leak transactions to nonbanks |
| **Evidence** | Interview; BOND Hub gaps; Section 5 sensitivity | BOND Hub shows the shared-reporting model works for usage, not profit | Paper-check end Sept 30, 2025; 3.4M Direct Express users; 2021: 34.9% of recently banked credited a benefit payment | FDIC 2023 underbanked usage; 61% of unbanked app users pay bills there |
| **Customer value** | Indirect: more banks launch low-cost accounts | Products improved on measured outcomes | Lower fees than check cashing, a credit-file path | \~$200/yr in avoided fees (2017 estimate) |
| **Bank value** | Clear go/no-go with payback and downside | Peer proof reduces perceived risk | Lower CAC, recurring deposits drive primacy | Deeper wallet share from customers already acquired |
| **Mastercard value** | Directly removes the stated sales friction | Builds a defensible evidence asset across its network | Volume stays on Mastercard rails as cards graduate | More debit volume on existing cards |
| **Microsoft role** | Fabric lakehouse joins ACS, BankFind, FDIC survey; Power BI what-if model; Foundry drafts a cited narrative from verified numbers only | Fabric + Purview for governed, aggregated cohort data; clean-room style sharing | Light: eligibility and messaging flows | Azure ML on the bank's own transaction data |
| **Data needed** | Public (available now) + 8–10 bank inputs from Section 5 | Bank cohort data, consent, data-sharing agreements | Treasury/agent partnership, consent, benefit-program data | Bank transaction data, merchant category coding |
| **Validation** | Put the model in front of 2–3 bank finance leads; do they trust and change the inputs? | One 6-month pilot with a holdout group | Small opt-in graduation offer with one partner bank | Back-test on historical transactions |
| **Risks** | Garbage-in assumptions; seen as a sales tool | Banks won't share data; slow | Treasury program rules; consent; fraud | Privacy perception; UDAAP risk if offers are poorly targeted |
| **Hackathon feasible?** | **Yes**: public data plus scenario inputs | Partly: design and mock dashboard only | Weak: needs program access | Weak: needs private data |

### Ranking (1 = weak, 5 = strong; Inference)

| Criterion | O1 | O2 | O3 | O4 |
| --- | --- | --- | --- | --- |
| Alignment with discovery interview | 5 | 4 | 3 | 3 |
| Strength of supporting evidence | 4 | 4 | 4 | 4 |
| Potential measurable business impact | 4 | 5 | 4 | 4 |
| Value to underserved communities | 3 | 4 | 5 | 4 |
| Technical feasibility | 5 | 3 | 3 | 3 |
| Data availability | 4 | 2 | 2 | 2 |
| Ability to demonstrate an MVP | 5 | 3 | 2 | 3 |
| **Total (of 35)** | **30** | **25** | **23** | **23** |

O3 and O4 carry the most direct customer value but depend on data the team cannot reach this week. They make strong *use cases* inside O1: the builder can model a graduation or recapture program as a scenario.

## 7. Recommended Opportunity: Partner-Bank Business Case Builder (O1)

**Build a transparent, bank-specific investment model that answers one executive question: “If we launch a low-cost account in these tracts, what does it cost us, when does it pay back, and what happens to customers?”** It is chosen because it attacks the exact friction Mastercard named, runs on public data today, and turns every unknown into an explicit input the bank supplies, which is what makes it credible rather than promotional.

### Proof of concept (buildable in a hackathon)

1. **Pick one real footprint.** Choose one mid-size bank from BankFind (e.g., a $1–10B bank in one MSA). Pull its branches from `/locations` and deposits from `/sod` (2025).
2. **Load public layers into Microsoft Fabric.** ACS 2020–2024 tract tables (`B19001`, `C17002`, `B11012`, `B28002`, `C16002`, `B08201`) with margins of error; FDIC 2023 state and income-bracket rates; BOND Hub state-level usage.
3. **Produce a modeled range, not a point.** Estimate tract-level unbanked households by applying FDIC income-bracket rates to ACS bracket counts, scaled to the FDIC state total, and carry the MOE through to a low–high band. Label it “modeled estimate.”
4. **Overlay presence vs need.** Distance from each tract to the bank's nearest full-service branch and to competitors; flag tracts with high modeled need and no nearby branch.
5. **Build the payback model in Power BI.** What-if sliders for the Section 5 inputs (CAC, servicing cost, closure, cross-sell, funding value, interchange). Defaults come from BOND Hub where public and are flagged “Illustrative” where not. Output: 5-year NPV per account, payback year, break-even CAC, and total program cost for a pilot of N accounts.
6. **Generate a cited one-page brief with Microsoft Foundry.** A model drafts the investment memo *only* from numbers the model computed, with a source link on every figure. It refuses to state a number that isn't in the data. This is the one place AI earns its place: turning a model into a banker-readable narrative in minutes.
7. **Attach a pilot design.** Auto-generate a 6-month test-and-control plan with the metrics from Section 5, so the brief ends with a small, stoppable ask rather than a large commitment.

### Demo success criteria

- A judge can change three inputs and see payback move, with the reason visible.
- Every number on screen opens to its source or is labeled Illustrative.
- The tract map shows a range, never a single “unbanked rate” for a tract.

### Guardrails (non-negotiable)

- Tract-level, aggregate use only. No individual-level scoring, and no protected attributes (race, ethnicity, disability, national origin) used in any eligibility or pricing decision.
- Demographic correlates are shown as context for outreach and accessibility, never as targeting rules for credit. Review against fair-lending and UDAAP standards before any real deployment.
- No bank data leaves the bank; the real version runs in the bank's or Mastercard's tenant.

### Why not lead with AI

The core value is a trustworthy model and clear assumptions. Foundry adds speed in writing the memo and answering “what if” questions in plain language; if it were removed, the product would still work. That is the right dependency direction for a credit committee audience.

## 8. Open Questions

**The single most important unknown is what evidence standard a partner bank's investment committee actually uses; everything in Section 7 should be tuned to that answer.**

### For Mastercard representatives

- [ ] Which partner-bank segment is the priority: community banks, regionals, or large issuers? The economics differ sharply (Section 5).
- [ ] When a bank said no, what was the stated reason: cost, risk, CAC, compliance, or lack of proof?
- [ ] What does Mastercard already give banks today (Inclusive Growth Score, heat maps, incentives)? What do banks ignore?
- [ ] Can Mastercard offer co-funding, interchange or marketing incentives, or a shared acquisition channel? These change CAC directly.
- [ ] Is there appetite to link Direct Express or prepaid programs to partner-bank graduation offers?
- [ ] What aggregated, anonymized network data could Mastercard contribute to the model without privacy risk?

### For partner banks

- [ ] Hurdle rate, payback limit and pilot budget for a new retail product.
- [ ] Fully loaded CAC, activation rate and 12-month retention for current checking accounts.
- [ ] Cost to serve a digital-only vs branch-served account.
- [ ] Is a Bank On-certified account already offered? If yes, what are its opening, usage and closure numbers?
- [ ] Debit interchange status (Reg II covered or exempt) and funds-transfer price for deposits.
- [ ] CIP/ID policy (ITIN, consular, municipal ID) and use of screening databases at account opening.

### For underserved customers (interviews or community partners)

- [ ] For people who do *not* want an account, what would change their mind, if anything? (Distrust is the least understood barrier.)
- [ ] Which nonbank service costs them the most and which would they replace first?
- [ ] Did the paper-check change push them to prepaid, a bank, or a waiver? How did it go?
- [ ] Preferred channel for opening and getting help: branch, phone, app, or a trusted community organization?

### Data gaps to track

- FDIC 2025 survey results (fielded June 2025, not yet published), especially the new opinions-about-banks questions.
- Whether the 2025 CRA rescission proposal was finalized.
- Current Reg II debit interchange cap.

## 9. Source Register

**Primary government and Federal Reserve sources carry the analysis; industry and vendor figures appear only as clearly labeled ranges.**

| Source | Publisher | Published | Data period | Reliability | Notes |
| --- | --- | --- | --- | --- | --- |
| [ACS 5-Year Data API](https://www.census.gov/data/developers/data-sets/acs-5year.html) | U.S. Census Bureau | Jan 29, 2026 (page rev. May 20, 2026) | 2020–2024 | High | Key now required; tract MOEs can be large |
| [BankFind Suite API](https://api.fdic.gov/banks/docs/) | FDIC | Live; locations index Oct 9, 2026; SOD index Sept 18, 2026 | Current; SOD as of June 30, 2025 | High | Queried live; presence only, not access quality |
| [2023 FDIC Household Survey, Executive Summary](https://fdic.gov/household-survey/2023-fdic-national-survey-unbanked-and-underbanked-households-executive-summary) | FDIC | Nov 2024 | June 2023 | High | \~30,000 HHs; national, state, large MSA only |
| [FDIC Household Survey interactive site](https://household-survey.fdic.gov/) | FDIC | — | 2009–2023 | High | **Not rendered by our tools**; use for custom state/MSA tables |
| [2021 FDIC survey findings](https://www.fdic.gov/household-survey) | FDIC | 2022 (page updated July 2023) | June 2021 | High | Source of benefit-payment “bankable moment” figures |
| [2025 FDIC survey OMB filing](https://omb.report/icr/202505-3064-002/doc/158020901.pdf) | FDIC / OMB | 2025 | June 2025 fielding | High | Confirms new questions; results not yet out |
| [Economic Well-Being of U.S. Households in 2025 (SHED)](https://www.federalreserve.gov/publications/files/2025-report-economic-well-being-us-households-202605.pdf) | Federal Reserve Board | May 2026 | Oct 2025 | High | Adult-level, not household-level |
| [Bank On National Data Hub: Findings from 2024](https://www.stlouisfed.org/community-development/bank-on-national-data-hub/bank-on-report-2024) | St. Louis Fed / CFE Fund | Nov 13, 2025 | 2024 | Medium-high | Voluntary reporting by 45 FIs; weighted aggregates |
| [Tracking Banking Access Using the BOND Hub](https://www.stlouisfed.org/on-the-economy/2026/feb/tracking-banking-access-using-bank-on-national-data-hub) | St. Louis Fed | Feb 24, 2026 | 2018–2024 | Medium-high | Closure trend; paper-check context |
| [FDIC Model Safe Accounts Pilot](https://www.fdic.gov/consumer-research/model-safe-accounts-pilot) | FDIC | Apr 2012 | 2011 | High but dated | 9 banks; small sample |
| [A Look at the Affordable Banking Movement](https://www.stlouisfed.org/open-vault/2019/january/affordable-banking-movement) | St. Louis Fed | Jan 2019 | 2017 | Medium | Source of \~$200/yr savings estimate |
| [CRA rescission proposal](https://www.federalreserve.gov/newsevents/pressreleases/bcreg20250716a.htm) | FRB, FDIC, OCC | July 16, 2025 | — | High | Final status not verified |
| [Congress Repeals CFPB's Overdraft Rule](https://www.everycrsreport.com/reports/IN12513.html) | Congressional Research Service | Sept 10, 2025 | — | High | Signed May 9, 2025 |
| [Direct Express agent change / paper-check end](https://www.paymentsjournal.com/as-paper-checks-sunset-fifth-third-bank-scales-up-prepaid-program/amp/) | PaymentsJournal | Sept 30, 2025 | 2025 | Medium | Trade press; 3.4M figure also in [Treasury release](https://fiscal.treasury.gov/about-us/news/manage-direct-express-program-for-federal-benefits) (Nov 2024) |
| [Inclusive Growth Score](https://www.mastercard.com/news/perspectives/2023/inclusive-growth-score-for-everyone-to-win-you-have-to-keep-score) | Mastercard | 2023 | Tract-level | Medium (company source) | Shows existing Mastercard capability |
| [Mastercard 2025 Impact Report coverage](https://ffnews.com/news/mastercard-surpasses-1-billion-digital-inclusion-goal-and-slashes-emissions-in-2025-impact-report) | FF News | July 17, 2026 | 2015–2025 | Low-medium | Secondary report of company claim |
| [Microsoft Foundry rename](https://examinotion.com/blog/azure-ai-foundry-renamed-microsoft-foundry) | Third-party summary of Microsoft Learn | 2026 | — | Medium | Confirm on Microsoft Learn before citing in pitch |
| [Reducing CAC in banking](https://www.backbase.com/blog/reducing-customer-acquisition-cost-banking) / [CU member acquisition cost](https://swaystack.com/blog/how-financial-institutions-are-optimizing-customer-acquisition-costs-and-driving-roi) | Vendors | 2025 | — | **Low** | Used only as a range; replace with bank data |
| [How customer primacy drives value](https://bankingjournal.aba.com/2025/07/how-customer-primacy-drives-value-in-2025) | ABA Banking Journal | July 17, 2025 | — | Medium | Primacy definitions |

**Added October 12, 2026**

| Source | Publisher | Published | Data period | Reliability | Notes |
| --- | --- | --- | --- | --- | --- |
| [HMDA Data Browser API](https://ffiec.cfpb.gov/data-browser/) | FFIEC / CFPB | Annual | 2021–2025 | High | County totals verified live for 2021 and 2025 |
| [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/) | CFPB | Continuous | Jan 2021 – Oct 12, 2026 | Medium (self-selected) | API returned errors on Oct 12; pulled file reconciles internally |
| [FDIC Household Survey appendix tables](https://fdic.gov/household-survey/2023-fdic-national-survey-unbanked-and-underbanked-households-appendix-tables) | FDIC | Nov 2024 | 2019–2023 | High | Tables A.2–A.4 read; G.2/G.3 underbanked tables not retrieved |
