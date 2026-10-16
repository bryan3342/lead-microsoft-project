#!/usr/bin/env python3
"""Generate Layer 2 county-level recommendations using the Foundry playbook generator.

This script:
1. Runs the Foundry playbook generator to get tract-level recommendations
2. Aggregates to county level (groups by county, picks strongest signal per county)
3. Updates web/data.json with real Foundry-generated recommendations
4. Preserves existing LTV values (from Fabric notebook) since those require the LTV model

Usage:
  python scripts/generate_layer2.py [--metro houston] [--output web/data.json]
"""
import json
import argparse
from pathlib import Path
from collections import defaultdict

# Add foundry to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from foundry.agent import PlaybookAgent
from foundry.data_loader import DataLoader


def aggregate_to_counties(playbook, data_loader):
    """Aggregate tract-level recommendations to county level.

    For each county, picks the most common top_need and uses that recommendation.
    Returns a list of county-level recommendation objects matching the shape of
    web/data.json's counties array.
    """
    # Load county names for each tract
    acs = data_loader.load_acs_tracts()
    sample_counties = data_loader._read("sample_counties")
    county_lookup = dict(zip(sample_counties["county_fips"], sample_counties["county_name"]))
    acs["county_name"] = acs["county_fips"].map(county_lookup)
    tract_to_county = dict(zip(acs["tract_geoid"], acs["county_name"]))

    # Group recommendations by county
    by_county = defaultdict(list)
    for rec in playbook.recommendations:
        county = tract_to_county.get(rec.tract_geoid)
        if county:
            by_county[county].append(rec)

    # For each county, pick the most common top_need
    counties = []
    for county_name in sorted(by_county.keys()):
        recs = by_county[county_name]

        # Find the most common top_need
        needs = defaultdict(list)
        for rec in recs:
            needs[rec.top_need].append(rec)

        most_common_need = max(needs.keys(), key=lambda k: len(needs[k]))
        rec = needs[most_common_need][0]  # Use first recommendation for this need

        county_row = {
            "area": county_name,
            "signal": f"Foundry-derived: {most_common_need.lower()}",
            "times_metro": 1.0,  # Placeholder; would need metro-level normalization
            "top_need": rec.top_need,
            "entry_product": rec.entry_product,
            "campaign": rec.campaign,
            "channel": rec.channel,
            # Note: "value" (LTV estimates) preserved from original data.json
        }
        counties.append(county_row)

    return counties


def main():
    parser = argparse.ArgumentParser(description="Generate Layer 2 recommendations using Foundry")
    parser.add_argument("--metro", default="houston", help="Metro area (default: houston)")
    parser.add_argument("--output", default="web/data.json", help="Output data.json path")
    parser.add_argument("--input", default="web/data.json", help="Input data.json to update (to preserve LTV values)")

    args = parser.parse_args()

    # Generate playbook using Foundry
    print(f"Generating playbook for {args.metro}...")
    agent = PlaybookAgent(sample=args.metro.lower())
    playbook = agent.generate_playbook(args.metro.title())
    print(f"Generated {len(playbook.recommendations)} tract-level recommendations")

    # Aggregate to county level
    print("Aggregating to county level...")
    loader = DataLoader()
    new_counties = aggregate_to_counties(playbook, loader)
    print(f"Created {len(new_counties)} county-level recommendations")

    # Load existing data.json to preserve LTV values
    print(f"Loading existing {args.input}...")
    with open(args.input) as f:
        data = json.load(f)

    # Merge LTV values from original counties array with new Foundry recommendations
    old_counties_by_area = {c["area"]: c for c in data.get("counties", [])}
    for county in new_counties:
        if county["area"] in old_counties_by_area:
            # Preserve the LTV value from the original data
            county["value"] = old_counties_by_area[county["area"]].get("value", {})

    # Update data.json
    data["counties"] = new_counties
    data["_generated_by_foundry"] = True
    data["_foundry_metro"] = args.metro

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n✓ Updated {args.output}")
    print(f"  Counties: {len(new_counties)}")
    print(f"  Now shows real Foundry-generated recommendations instead of example output")


if __name__ == "__main__":
    main()
