"""Shared helpers: paths, sample definition, HTTP with retries, and provenance records."""

import argparse
import datetime as dt
import hashlib
import json
import os
import time
from pathlib import Path

import requests

# Each sample is one metro (CBSA). Pick with `--sample <name>` or the DAPA_SAMPLE env var; default dc.
SAMPLES = {
    "dc": {
        "cbsa": "47900",
        "name": "Washington-Arlington-Alexandria, DC-VA-MD-WV",
        "states": {"11": "DC", "24": "MD", "51": "VA", "54": "WV"},
    },
    "houston": {
        "cbsa": "26420",
        "name": "Houston-Pasadena-The Woodlands, TX",
        "states": {"48": "TX"},
    },
    "dallas": {
        "cbsa": "19100",
        "name": "Dallas-Fort Worth-Arlington, TX",
        "states": {"48": "TX"},
    },
}

_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--sample", choices=SAMPLES, default=os.environ.get("DAPA_SAMPLE", "dc"))
SAMPLE = _parser.parse_known_args()[0].sample
SAMPLE_CBSA = SAMPLES[SAMPLE]["cbsa"]
SAMPLE_STATES = SAMPLES[SAMPLE]["states"]
SAMPLE_NAME = SAMPLES[SAMPLE]["name"]
START_YEAR = 2021  # post-COVID window

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / SAMPLE
SHARED_RAW = ROOT / "data" / "raw" / "shared"  # national files reused by every sample
PROCESSED = ROOT / "data" / "processed" / SAMPLE
REFERENCE = ROOT / "data" / "reference"

TODAY = dt.date.today().isoformat()

_session = requests.Session()
_session.headers["User-Agent"] = "dapa-data-collection/0.1 (research prototype)"


def get(url, params=None, stream=False, timeout=120, retries=5):
    """GET with exponential backoff on 429/5xx and network errors."""
    for attempt in range(retries):
        try:
            resp = _session.get(url, params=params, stream=stream, timeout=timeout)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            retryable = not isinstance(exc, requests.HTTPError) or exc.response.status_code in (429, 500, 502, 503, 504)
            if not retryable or attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def raw_dir(source, shared=False):
    """Folder for today's raw downloads; shared=True for national files every sample reuses."""
    path = (SHARED_RAW if shared else RAW) / source / TODAY
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_provenance(data_path, url, params=None, rows=None, extra=None):
    """Write <file>.provenance.json next to a raw file so every value traces back to its source."""
    data_path = Path(data_path)
    digest = hashlib.sha256(data_path.read_bytes()).hexdigest() if data_path.is_file() else None
    record = {
        "file": data_path.name,
        "url": url,
        "params": params or {},
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "rows": rows,
        "sha256": digest,
        **(extra or {}),
    }
    data_path.with_name(data_path.name + ".provenance.json").write_text(json.dumps(record, indent=2))


def write_processed(df, name):
    """Write a processed table as Parquet (for Fabric) and CSV (for inspection)."""
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED / f"{name}.parquet", index=False)
    df.to_csv(PROCESSED / f"{name}.csv", index=False)
    print(f"  wrote data/processed/{SAMPLE}/{name} ({len(df):,} rows)")


def sample_counties():
    """5-digit county FIPS codes in the sample metro, from the processed delineation table."""
    path = PROCESSED / "sample_counties.csv"
    if not path.exists():
        raise SystemExit("Run scripts/fetch_geography.py first (builds sample_counties).")
    import pandas as pd

    return pd.read_csv(path, dtype=str)["county_fips"].tolist()


def census_key():
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("CENSUS_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"')
    return key
