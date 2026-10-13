"""Command-line interface for Foundry playbook generator."""
import argparse
import sys
from pathlib import Path
from foundry.agent import PlaybookAgent


def main():
    parser = argparse.ArgumentParser(
        description="Generate campaign playbooks for underserved communities"
    )
    parser.add_argument(
        "--metro",
        default="houston",
        help="Metro area: houston, dallas, or dc (default: houston)"
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Output directory for playbook files (default: output)"
    )
    parser.add_argument(
        "--format",
        default="both",
        choices=["json", "csv", "both"],
        help="Output format (default: both)"
    )

    args = parser.parse_args()

    try:
        agent = PlaybookAgent(sample=args.metro.lower())
        playbook = agent.generate_playbook(args.metro.title())

        output_path = Path(args.output)
        output_path.mkdir(exist_ok=True, parents=True)

        if args.format in ["json", "both"]:
            json_file = output_path / f"{args.metro.lower()}_playbook.json"
            agent.renderer.to_json(playbook, json_file)
            print(f"✓ JSON: {json_file}")

        if args.format in ["csv", "both"]:
            csv_file = output_path / f"{args.metro.lower()}_playbook.csv"
            agent.renderer.to_csv(playbook, csv_file)
            print(f"✓ CSV: {csv_file}")

        print(f"\nPlaybook Summary:")
        print(f"  Metro: {playbook.metro_name}")
        print(f"  Census tracts: {playbook.sample_size}")
        print(f"  Recommendations: {len(playbook.recommendations)}")
        print(f"  Generated: {playbook.generated_at}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
