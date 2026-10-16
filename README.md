# Inclusion ROI Engine

## Description

A financial-inclusion research and demo project combining public banking and community data, a static pitch dashboard, and Microsoft Fabric / Power BI item definitions. It includes processed samples for Washington, DC, Houston, and Dallas.

## Dependencies

- A browser and Python 3 for serving the static demo.
- Python 3.10+ for the Fabric preview and test tools.
- `requests`, `pandas`, `pyarrow`, and `openpyxl` for data collection.
- `pytest>=8` for Fabric checks.
- Azure CLI sign-in and Fabric permissions for the optional cloud deployment workflow. These are not needed to view the checked-in web snapshot.

## Technologies

Python, CSV and Parquet, HTML and JavaScript, Microsoft Fabric lakehouse/notebook definitions, Power BI reports and semantic models, Azure CLI, and Cloudflare static-asset configuration.

## Setup

```bash
git clone https://github.com/bryan3342/lead-microsoft-project.git
cd lead-microsoft-project
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt -r fabric/requirements-dev.txt
```

On Windows, use `.venv\Scripts\activate`. The static page can use the existing `web/data.json` without downloading datasets or deploying infrastructure.

For data refreshes, see [data documentation](data/README.md). `scripts/common.py` supports `--sample dc`, `--sample houston`, and `--sample dallas`; geography must be fetched before scripts that require county mappings. ACS collection uses `CENSUS_API_KEY`.

For cloud deployment, follow the [Fabric runbook](fabric/deploy/RUNBOOK.md), including its configuration and resource requirements.

## Features

- Data collectors for FDIC, Census ACS, HMDA, CFPB, and geographic crosswalks.
- A static opportunity map, lifetime-value breakdown, campaign mix, and projected pilot view.
- Fabric notebooks, lakehouse metadata, report definitions, and semantic models.
- Local layout previews and consistency checks for Fabric assets.
- Separate assumption tables for lifetime value, campaigns, and pilot scenarios.

Observed data, estimates, and projections are distinct. Unbanked household counts are estimates; lifetime value and pilot outcomes use assumptions. No completed pilot is established by this repository. The research-agent and Copilot components described in planning documents are not implemented applications here.

## Commands to run

```bash
python3 -m http.server 8765 --directory web
python3 fabric/tools/preview.py
python3 fabric/tools/web_preview.py --open
python3 -m pytest fabric/tests
```

Open `http://localhost:8765` for the static demo. After configuring and running the Fabric workflow, `python3 web/fetch_data.py` refreshes the web snapshot from the lakehouse. It requires Azure authentication and `fabric/deploy/config.env`.

## Contributors

- [Bryan Mejia (@bryan3342)](https://github.com/bryan3342)
- [Angel Difo (@KerlynD)](https://github.com/KerlynD)
- Daniel Fernandez
- [Giancarlo Forero (@gianca2020)](https://github.com/gianca2020)

Credit follows human authors in Git history. Public datasets retain their respective source attribution in the [data documentation](data/README.md).
