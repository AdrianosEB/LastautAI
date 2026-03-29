"""CLI entrypoint for dry-run workflow generation."""

import argparse
import json
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

from src.pipeline import generate_workflow, AmbiguityRejection, PipelineError


def main():
    parser = argparse.ArgumentParser(
        description="Generate a workflow definition from a natural language description",
    )
    parser.add_argument("input_file", help="Path to a text file with the workflow description")
    parser.add_argument("--format", choices=["json", "yaml"], default="json", help="Output format (default: json)")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode (reject ambiguous input)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    try:
        with open(args.input_file) as f:
            description = f.read().strip()
    except FileNotFoundError:
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    if not description:
        print("Error: Input file is empty", file=sys.stderr)
        sys.exit(1)

    try:
        result = generate_workflow(
            description=description,
            output_format=args.format,
            strict_mode=args.strict,
        )
    except AmbiguityRejection as e:
        print("Error: Input is ambiguous", file=sys.stderr)
        for amb in e.ambiguities:
            print(f"  - {amb['text']}: {', '.join(amb['options'])}", file=sys.stderr)
        sys.exit(2)
    except PipelineError as e:
        print(f"Error in {e.stage}: {e.message}", file=sys.stderr)
        sys.exit(1)

    if isinstance(result, dict):
        print(json.dumps(result, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main()
