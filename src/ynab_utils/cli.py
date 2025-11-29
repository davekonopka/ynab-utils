"""CLI interface for ynab-utils."""

import argparse
import sys

from ynab_utils import __version__
from ynab_utils.dupes import detect_duplicates


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="ynab-utils",
        description="A CLI utility for YNAB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
    )

    # detect-dupes subcommand
    dupes_parser = subparsers.add_parser(
        "detect-dupes",
        help="Detect possible duplicate transactions in YNAB export",
    )
    dupes_parser.add_argument(
        "--file",
        required=True,
        help="Path to YNAB CSV export file",
    )
    dupes_parser.add_argument(
        "--days",
        type=int,
        default=2,
        help="Number of days window for date proximity matching (default: 2)",
    )
    dupes_parser.add_argument(
        "--confidence",
        type=int,
        default=5,
        choices=[1, 2, 3, 4, 5],
        help="Minimum confidence level to report (1=lowest, 5=highest, default: 5)",
    )
    dupes_parser.add_argument(
        "--start-date",
        type=str,
        help="Filter transactions from this date onwards (format: YYYY-MM-DD)",
    )
    dupes_parser.add_argument(
        "--output",
        type=str,
        default="text",
        choices=["text", "json"],
        help="Output format (default: text)",
    )

    return parser


def main() -> int:
    """Main entry point for the CLI application."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "detect-dupes":
        return detect_duplicates(args.file, args.days, args.confidence, args.start_date, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
