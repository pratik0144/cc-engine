#!/usr/bin/env python3
"""
Credit Card Data Collection Engine — CLI Entry Point

Usage:
    python run.py --all                    # Full pipeline for all 20 banks
    python run.py --bank hdfc --bank sbi   # Specific banks only
    python run.py --scrape-only            # Only scrape, no LLM extraction
    python run.py --extract-only           # Only extract from cached data
    python run.py --all --resume           # Resume from where it left off
    python run.py --validate               # Validate existing output file
    python run.py --list-banks             # List all available banks
"""
from __future__ import annotations
import argparse
import asyncio
import sys

from rich.console import Console
from rich.table import Table


console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="🏦 Indian Credit Card Data Collection Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --all                    Full pipeline for all banks
  python run.py --bank hdfc --bank sbi   Process specific banks
  python run.py --scrape-only --all      Only scrape (no LLM)
  python run.py --extract-only --all     Only extract from cache
  python run.py --validate               Validate output JSON
  python run.py --list-banks             Show available banks
        """,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Process all 20 banks")
    group.add_argument("--bank", action="append", dest="banks", metavar="BANK_ID",
                       help="Process specific bank(s) by ID (repeatable)")
    group.add_argument("--validate", action="store_true", help="Validate existing output")
    group.add_argument("--list-banks", action="store_true", help="List all banks and IDs")

    parser.add_argument("--scrape-only", action="store_true",
                        help="Only scrape pages, skip LLM extraction")
    parser.add_argument("--extract-only", action="store_true",
                        help="Only run LLM extraction on cached data")
    parser.add_argument("--no-resume", action="store_true",
                        help="Don't use cached data, re-scrape everything")

    return parser.parse_args()


def list_banks():
    """Print a table of all available banks."""
    from engine.bank_registry import BANKS

    table = Table(title="🏦 Available Banks", show_lines=True)
    table.add_column("ID", style="cyan", min_width=10)
    table.add_column("Bank Name", style="green", min_width=30)
    table.add_column("Listing URL", style="dim", max_width=60)

    for bank in BANKS:
        table.add_row(bank.bank_id, bank.bank_name, bank.credit_card_listing_url)

    console.print(table)
    console.print(f"\n[dim]Use --bank <ID> to process specific banks[/dim]")


def run_validation():
    """Run validation on existing output."""
    from engine.pipeline import validate_output, print_summary, OUTPUT_FILE
    import json

    if not OUTPUT_FILE.exists():
        console.print("[red]No output file found. Run the pipeline first.[/red]")
        return

    with open(OUTPUT_FILE) as f:
        data = json.load(f)

    cards = data.get("cards", [])
    console.print(f"\n[bold]Validating {len(cards)} cards...[/bold]\n")

    validate_output()
    print_summary(cards)


async def main():
    args = parse_args()

    if args.list_banks:
        list_banks()
        return

    if args.validate:
        run_validation()
        return

    if not args.all and not args.banks:
        console.print("[yellow]No banks specified. Use --all or --bank <ID>[/yellow]")
        console.print("[dim]Run with --help for usage information[/dim]")
        return

    from engine.pipeline import run_full_pipeline

    bank_ids = None if args.all else args.banks
    resume = not args.no_resume

    await run_full_pipeline(
        bank_ids=bank_ids,
        resume=resume,
        scrape_only=args.scrape_only,
        extract_only=args.extract_only,
    )


if __name__ == "__main__":
    asyncio.run(main())
