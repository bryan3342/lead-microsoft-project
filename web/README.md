# Inclusion ROI Engine web page

A single static page that shows the pitch view of the data: opportunity map, LTV build-up, campaign mix,
projected pilot and trust signals, with a scenario toggle. It computes nothing. Every number comes from
`data.json`, which the `Load Public Data` notebook writes in the Fabric lakehouse.

```bash
python3 web/fetch_data.py                       # pull the latest snapshot from the lakehouse
python3 -m http.server 8765 --directory web     # then open http://localhost:8765
```

- **Change the metro:** set `SAMPLE` in `fabric/deploy/config.env`, run `fabric/deploy/deploy.py up`, then fetch again.
- **Change an assumption:** edit a file in `data/assumptions/`, deploy, fetch.
- **Without Fabric:** run the notebook's code cells locally; it writes the same file to `sample-output/site_data.json`.

What is observed and what is projected:

| On the page | Basis |
|---|---|
| Households, branches, mortgage denial rate, branch closings, complaints, limited-English share | Observed public data |
| Unbanked and underbanked households | Estimate: FDIC survey rates applied to ACS household counts |
| "Why people stay unbanked" percentages | FDIC survey, national |
| LTV, footprint value, campaign value | Projection from `ltv_assumptions.csv` |
| Pilot bank and branches | Chosen from the data: the local bank whose branches sit in the highest-opportunity tracts |
| Pilot accounts, activation, deposits, return, payback | Projection from `pilot_assumptions.csv`. No pilot has run. |
| Top need per county | The county's strongest signal relative to the metro, mapped through `campaign_playbook.csv` |
