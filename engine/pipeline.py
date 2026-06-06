"""
End-to-end pipeline orchestrator.

Coordinates scraping, extraction, normalization, and output generation.
"""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone

from engine.config import RAW_DIR, OUTPUT_DIR, OUTPUT_FILE
from engine.bank_registry import BANKS, BankInfo, get_bank, get_all_bank_ids
from engine.scraper import scrape_bank
from engine.extractor import extract_card_data, extract_from_cached_file, check_ollama_health
from engine.normalizer import normalize_all_cards, deduplicate_cards
from engine.utils import logger, console

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel


async def run_scrape_phase(banks: list[BankInfo], resume: bool = True) -> dict[str, list[dict]]:
    """
    Phase 1 & 2: Scrape listing pages and card detail pages for given banks.
    Returns: {bank_id: [cached_card_data_dicts]}
    """
    results = {}

    for i, bank in enumerate(banks, 1):
        console.rule(f"[bold blue]Scraping {bank.bank_name} ({i}/{len(banks)})")
        try:
            card_data_list = await scrape_bank(bank, resume=resume)
            results[bank.bank_id] = card_data_list
            logger.info(f"  📊 {bank.bank_name}: {len(card_data_list)} pages scraped")
        except Exception as e:
            logger.error(f"  ❌ Error scraping {bank.bank_name}: {e}")
            results[bank.bank_id] = []

    return results


async def run_extract_phase(banks: list[BankInfo]) -> dict[str, list[dict]]:
    """
    Phase 3: Run LLM extraction on all cached raw data.
    Returns: {bank_id: [extracted_card_dicts]}
    """
    # Check Ollama first
    if not await check_ollama_health():
        logger.error("Ollama is not available. Cannot run extraction.")
        raise RuntimeError("Ollama not available")

    results = {}

    for i, bank in enumerate(banks, 1):
        console.rule(f"[bold green]Extracting {bank.bank_name} ({i}/{len(banks)})")
        bank_dir = RAW_DIR / bank.bank_id

        if not bank_dir.exists():
            logger.warning(f"  No raw data found for {bank.bank_name}. Run scrape phase first.")
            results[bank.bank_id] = []
            continue

        # Find all cached files
        cache_files = sorted(bank_dir.glob("*.json"))
        cache_files = [f for f in cache_files if f.name != "_discovered_urls.json"]

        if not cache_files:
            logger.warning(f"  No cached files for {bank.bank_name}")
            results[bank.bank_id] = []
            continue

        bank_cards = []
        for j, cache_file in enumerate(cache_files, 1):
            logger.info(f"  [{j}/{len(cache_files)}] Extracting from {cache_file.name}")
            try:
                extracted = await extract_from_cached_file(str(cache_file))
                if extracted:
                    bank_cards.extend(extracted)
                    logger.info(f"    → Got {len(extracted)} card(s)")
                else:
                    logger.warning(f"    → No cards extracted")
            except Exception as e:
                logger.error(f"    → Extraction error: {e}")

        results[bank.bank_id] = bank_cards
        logger.info(f"  📊 {bank.bank_name}: {len(bank_cards)} cards extracted")

    return results


def run_normalize_phase(extracted: dict[str, list[dict]]) -> list[dict]:
    """
    Phase 4: Normalize and deduplicate all extracted cards.
    Returns: list of all normalized cards
    """
    all_cards = []

    for bank_id, cards in extracted.items():
        if not cards:
            continue
        normalized = normalize_all_cards(cards, bank_id)
        all_cards.extend(normalized)
        logger.info(f"  {bank_id}: {len(normalized)} cards normalized")

    # Global deduplication
    all_cards = deduplicate_cards(all_cards)
    logger.info(f"\n📊 Total unique cards after normalization: {len(all_cards)}")

    return all_cards


def save_output(cards: list[dict], output_file: Path = OUTPUT_FILE):
    """Save final card data to JSON file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_cards": len(cards),
            "banks_covered": len(set(c.get("bank_id", "") for c in cards)),
            "schema_version": "1.0",
        },
        "cards": cards,
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✅ Saved {len(cards)} cards to {output_file}")


def print_summary(cards: list[dict]):
    """Print a nice summary table of results."""
    # Group by bank
    bank_counts = {}
    for card in cards:
        bank_id = card.get("bank_id", "unknown")
        bank_name = card.get("bank_name", bank_id)
        key = (bank_id, bank_name)
        bank_counts[key] = bank_counts.get(key, 0) + 1

    table = Table(title="📊 Card Collection Summary", show_lines=True)
    table.add_column("Bank", style="cyan", min_width=25)
    table.add_column("Cards", style="green", justify="center")
    table.add_column("Status", justify="center")

    total = 0
    for (bank_id, bank_name), count in sorted(bank_counts.items()):
        status = "✅" if count >= 3 else "⚠️" if count >= 1 else "❌"
        table.add_row(bank_name, str(count), status)
        total += count

    table.add_row("[bold]TOTAL[/bold]", f"[bold]{total}[/bold]", "", style="bold")
    console.print(table)

    # Coverage stats
    completeness = []
    for card in cards:
        non_null = sum(1 for v in card.values() if v is not None)
        total_fields = len(card)
        completeness.append(non_null / total_fields * 100 if total_fields > 0 else 0)

    if completeness:
        avg = sum(completeness) / len(completeness)
        console.print(f"\n📈 Average field completeness: [bold]{avg:.1f}%[/bold]")


def validate_output(output_file: Path = OUTPUT_FILE) -> bool:
    """Validate the output JSON file against schema."""
    if not output_file.exists():
        logger.error(f"Output file not found: {output_file}")
        return False

    with open(output_file) as f:
        data = json.load(f)

    cards = data.get("cards", [])
    if not cards:
        logger.error("No cards in output file")
        return False

    # Validate required fields
    issues = []
    for i, card in enumerate(cards):
        if not card.get("card_name"):
            issues.append(f"Card {i}: missing card_name")
        if not card.get("bank_id"):
            issues.append(f"Card {i}: missing bank_id")

    if issues:
        logger.warning(f"Validation found {len(issues)} issues:")
        for issue in issues[:10]:
            logger.warning(f"  - {issue}")
        return False

    logger.info(f"✅ Validation passed: {len(cards)} cards OK")
    return True


# ── Main Pipeline Functions ───────────────────────────────────────────────

async def run_full_pipeline(
    bank_ids: list[str] | None = None,
    resume: bool = True,
    scrape_only: bool = False,
    extract_only: bool = False,
):
    """
    Run the complete pipeline: scrape → extract → normalize → save.
    """
    # Determine which banks to process
    if bank_ids:
        banks = [get_bank(bid) for bid in bank_ids]
        banks = [b for b in banks if b is not None]
        if not banks:
            logger.error(f"No valid banks found for IDs: {bank_ids}")
            return
    else:
        banks = BANKS

    console.print(Panel(
        f"[bold]Credit Card Data Engine[/bold]\n"
        f"Banks: {len(banks)} | Mode: {'scrape-only' if scrape_only else 'extract-only' if extract_only else 'full'} | Resume: {resume}",
        title="🏦 Starting Pipeline",
        border_style="blue",
    ))

    # Phase 1+2: Scraping
    if not extract_only:
        console.print("\n[bold blue]═══ PHASE 1+2: SCRAPING ═══[/bold blue]\n")
        await run_scrape_phase(banks, resume=resume)

    if scrape_only:
        console.print("\n[bold green]Scraping complete. Raw data saved to data/raw/[/bold green]")
        return

    # Phase 3: LLM Extraction
    console.print("\n[bold green]═══ PHASE 3: LLM EXTRACTION ═══[/bold green]\n")
    extracted = await run_extract_phase(banks)

    # Phase 4: Normalization
    console.print("\n[bold yellow]═══ PHASE 4: NORMALIZATION ═══[/bold yellow]\n")
    all_cards = run_normalize_phase(extracted)

    if not all_cards:
        logger.error("No cards extracted! Check logs for errors.")
        return

    # Save output
    save_output(all_cards)
    print_summary(all_cards)

    # Validate
    validate_output()
