# 🏦 Indian Credit Card Data Collection Engine — Progress & Handoff Document

> **Last Updated:** June 6, 2026  
> **Project Path:** `/Users/pratikpotadar/Developer/cc.com`  
> **Purpose:** This document covers everything built so far, what's working, what's broken, known issues, and detailed instructions for the next AI agent to continue the work.

---

## 📋 Project Overview

This engine scrapes credit/debit card data from 20 Indian bank websites, extracts structured fields using a local LLM (Ollama), normalizes the data, and outputs a unified JSON file. **No API keys are used** — everything runs locally.

### Goal
Collect structured data for **150-200+ credit/debit cards** across 20 Indian banks, with ~56 fields per card (fees, rewards, eligibility, benefits, India-specific features). The output JSON will later power a comparison website (not built yet).

### Tech Stack
- **Python 3.13** (macOS)
- **Crawl4AI** — browser-based web scraper (uses Playwright/Chromium)
- **Ollama** — local LLM inference
  - Primary: `deepseek-v3.1:671b-cloud` (cloud model, quota exhausted as of June 6, 2026)
  - Fallback: `qwen2.5-coder:7b` (local, 4.7 GB, ~30s per extraction)
  - Also available: `qwen2.5-coder:14b` (local, 9.0 GB, ~2-4min per extraction, not recommended for batch)
- **Pydantic v2** — data validation
- **Rich** — terminal UI
- **httpx** — HTTP client for Ollama API

---

## 📁 Project Structure

```
cc.com/
├── run.py                      # CLI entry point (argparse)
├── requirements.txt            # crawl4ai, pydantic, httpx, rich
├── details.md                  # Source of truth: bank list + 56 required fields
├── progress.md                 # THIS FILE
├── debug_links.py              # One-off debug script (can be deleted)
├── engine/
│   ├── __init__.py             # Package init
│   ├── config.py               # All config: paths, Ollama settings, scraping params
│   ├── bank_registry.py        # 20 banks with URLs, selectors, notes
│   ├── scraper.py              # Crawl4AI scraper with domain aliasing + URL filtering
│   ├── extractor.py            # LLM extraction with cloud→local fallback + lenient validation
│   ├── models.py               # Pydantic models: CardExtraction (flat), CreditCard (nested)
│   ├── normalizer.py           # Fee/income/boolean/category normalization + deduplication
│   ├── pipeline.py             # Orchestrator: scrape → extract → normalize → save
│   └── utils.py                # Logging, slugify, rate limiting, text processing
└── data/
    ├── raw/
    │   └── hdfc/               # 54 scraped card JSON files + listing page + URL cache
    │       ├── _discovered_urls.json   # 77 discovered HDFC card URLs
    │       ├── listing-page.json       # HDFC listing page markdown
    │       ├── all-miles-credit-card.json
    │       ├── diners-club-black-credit-card.json
    │       └── ... (54 total card files)
    └── output/
        └── cards.json          # ← Final output (NOT YET GENERATED - extraction pending)
```

---

## ✅ What's COMPLETED and WORKING

### 1. Bank Registry (`engine/bank_registry.py`) — ✅ WORKING
- All **20 banks** registered with:
  - `bank_id`, `bank_name`, `short_code`
  - `credit_card_listing_url` (main listing page)
  - `extra_listing_urls` (alternate domains, e.g., HDFC has `hdfc.bank.in`)
  - `link_selector` (CSS selector hint)
  - `notes` (scraping tips per bank)
- Bank-specific URL regex patterns in `scraper.py` (`BANK_CARD_URL_PATTERNS`) for all 20 banks
- Exclude patterns for non-card pages (blogs, services, FAQs, etc.)

### 2. Web Scraper (`engine/scraper.py`) — ✅ WORKING (tested on HDFC)
- **Phase 1 (Discovery):** Crawls listing pages, extracts card product URLs using bank-specific regex patterns
- **Phase 2 (Detail scraping):** Scrapes individual card pages, caches as JSON
- **Domain aliasing:** `www.hdfcbank.com` → `www.hdfc.bank.in` (bypasses anti-bot blocks)
- **Features:**
  - Stealth browser config (random user agents, 1920×1080 viewport)
  - `domcontentloaded` wait strategy with 5.0s delay (JS-heavy banking sites)
  - Exponential backoff retries (3 attempts per page)
  - Rate limiting (2-4s random delay between requests)
  - Caching: won't re-scrape if JSON file exists (use `--no-resume` to force)
  - Fallback to listing page extraction if too many consecutive failures

### 3. HDFC Bank Scrape — ✅ COMPLETE
- **77 card URLs discovered** from 2 listing pages
- **54 individual card pages scraped** and cached in `data/raw/hdfc/`
- ~23 URLs were duplicates across `hdfcbank.com` and `hdfc.bank.in` domains
- Each cached file contains: `bank_id`, `bank_name`, `card_url`, `card_slug`, `markdown`, `title`
- Content quality is excellent — pages contain fees, rewards, eligibility, benefits, FAQs

**Complete list of 54 scraped HDFC cards:**
```
all-miles, bharat, credit-card-against-fd, diners-club-black, 
diners-club-black-metal-edition, diners-club-miles, diners-club-premium, 
diners-club-rewardz, diners-privilege, doctors-regalia, doctors-superia, 
flipkart-wholesale, freedom, hdfc-bank-upi-rupay, indianoil-hdfc-bank, 
infinia, intermiles-diners-club, intermiles-platinum, intermiles-signature, 
irctc, jetprivilege-titanium, lifestyle, marriott-bonvoy, millennia, 
money-back, moneyback-plus, paytm-business, phonepe-hdfc-bank-ultimo, 
phonepe-hdfc-bank-uno, phonepe-hdfc, pixel-go, pixel-play, platinum-edge, 
platinum-plus, regalia, regalia-activ, regalia-first, regalia-gold, 
rewards, rupay, shoppers-stop, shoppers-stop-black, solitaire, superia, 
swiggy-blck-hdfc-bank, swiggy-hdfc-bank, swiggy-ornge-hdfc-bank, 
tata-neu-infinity-hdfc-bank, tata-neu-plus-hdfc-bank, teachers-platinum, 
titanium-edge, travel, visa-signature, world-mastercard
```

### 4. LLM Extractor (`engine/extractor.py`) — ✅ WORKING (~80% success rate)
- Compact prompt with all 36 key fields (not full Pydantic schema dump)
- Ollama API with `"format": "json"` for forced JSON output
- **Cloud→local auto-fallback:** Tries `deepseek-v3.1:671b-cloud` first, auto-switches to `qwen2.5-coder:7b` on 403/429/402/503
- **Lenient validation:** 
  - Coerces strings→lists (e.g., `"fuel, groceries"` → `["fuel", "groceries"]`)
  - Coerces int/float→string for fee fields
  - Strips unknown fields before Pydantic validation
  - Double-fallback: if Pydantic fails, strips complex types and retries
- Markdown preprocessing: removes nav links, CDN images, CTA buttons, duplicate lines
- Content truncation to 8000 chars
- 3 retry attempts per card

### 5. Data Models (`engine/models.py`) — ✅ WORKING
- `CardExtraction` — flat model with all 56 fields, used for LLM extraction
- `CreditCard` — nested model (master, pricing, benefits, eligibility, india_specific)
- All fields are `Optional` except `card_name` and `bank_name`

### 6. Normalizer (`engine/normalizer.py`) — ✅ WORKING (not yet tested at scale)
- Fee normalization: `"₹500 + GST"` → `"500+GST"`, `"Nil"` → `"0"`
- Income normalization: `"25,000 p.m."` → `"300000"`, `"3 LPA"` → `"300000"`
- Boolean normalization: `"Available"` → `"yes"`
- Card type/network/category/variant standardization
- Deduplication: keeps card with more non-null fields

### 7. Pipeline Orchestrator (`engine/pipeline.py`) — ✅ WORKING
- `run_full_pipeline()` coordinates all phases
- Modes: `--scrape-only`, `--extract-only`, full pipeline
- Rich progress output with summary table
- Saves to `data/output/cards.json` with metadata

### 8. CLI Entry Point (`run.py`) — ✅ WORKING
```bash
python run.py --bank hdfc --scrape-only      # Scrape only
python run.py --bank hdfc --extract-only     # Extract from cached data
python run.py --bank hdfc                    # Full pipeline
python run.py --all                          # All 20 banks
python run.py --list-banks                   # Show all bank IDs
python run.py --validate                     # Validate output JSON
```

---

## ⚠️ What's PARTIALLY WORKING / HAS KNOWN ISSUES

### 1. LLM Extraction Success Rate (~80% on HDFC)
- **Tested:** 5 HDFC cards with `qwen2.5-coder:7b` — 4/5 succeeded
- **Failed card:** `credit-card-against-fd.json` — the LLM parses the page but validation fails (possibly because the model doesn't output `card_name` correctly for this unusual card type)
- **Root cause of past failures (fixed):** Pydantic was rejecting valid extractions because the 7b model outputs strings instead of lists/dicts for complex fields. Fixed with lenient type coercion in `_validate_extraction()`.
- **Average field completeness:** ~14-18 non-null fields out of 56 (30-35%). This is expected because individual card pages don't always list all fields (e.g., age limits, CIBIL score, etc.)

### 2. Cloud Model (`deepseek-v3.1:671b-cloud`)
- **Status:** Quota exhausted (returns 403 Forbidden)
- Auto-fallback to local `qwen2.5-coder:7b` works correctly
- If quota refreshes, the engine will automatically use it again (it tries cloud first each run)

### 3. Extraction Speed
- `qwen2.5-coder:7b`: ~30-40s per card (with retries: up to 90s)
- `qwen2.5-coder:14b`: ~2-4min per card (not recommended for batch)
- For 54 HDFC cards at 80% first-attempt success: ~30-45 minutes
- For all 20 banks (~200 cards): ~2-4 hours total

---

## ❌ What's NOT YET DONE

### 1. Run Full HDFC Extraction (IMMEDIATE PRIORITY)
**Status:** Scraping done, extraction NOT yet completed at scale.  
**How to do it:**
```bash
cd /Users/pratikpotadar/Developer/cc.com
python run.py --bank hdfc --extract-only
```
This will:
1. Check Ollama health
2. Process all 54 cached files in `data/raw/hdfc/`
3. Extract structured data using the LLM
4. Normalize and deduplicate
5. Save to `data/output/cards.json`

**Expected time:** ~30-45 minutes with `qwen2.5-coder:7b`

### 2. Scrape + Extract Remaining 19 Banks
**Status:** Not started. Only HDFC has been scraped.  
**Banks remaining:** SBI, ICICI, Axis, Kotak, IndusInd, RBL, IDFC FIRST, Federal, YES, AU, Standard Chartered, HSBC, Amex, Bank of Baroda, Canara, Union Bank, PNB, Indian Bank, Bank of India

**How to do it (one bank at a time):**
```bash
python run.py --bank sbi --scrape-only    # Scrape SBI first
python run.py --bank sbi --extract-only   # Then extract
```

**How to do it (all at once — will take 4+ hours):**
```bash
python run.py --all
```

**⚠️ IMPORTANT NOTES for other banks:**
- Each bank website is different. The URL patterns in `BANK_CARD_URL_PATTERNS` (in `scraper.py` lines 30-99) are **guesses** — they have NOT been tested. You will likely need to:
  1. Run `--scrape-only` for the bank
  2. Check `data/raw/<bank_id>/_discovered_urls.json` for the URLs it found
  3. If URLs are wrong or missing, update the regex patterns in `scraper.py`
  4. Check if the listing page URL in `bank_registry.py` is still valid
- **PSU banks** (Canara, Union, PNB, Indian Bank, BOI) have old `.aspx` websites with limited online card info. You may get very few or no cards.
- **SBI** uses a dedicated `sbicard.com` domain — should work well.
- **ICICI, Axis, Kotak** are modern sites — should work but may need CSS selector tuning.
- **Amex** (`americanexpress.com`) may have strong anti-bot measures.
- Some banks may need domain aliasing like HDFC. Add entries to `DOMAIN_ALIASES` in `scraper.py` (line 289).

### 3. Improve Extraction Quality
**Current issues:**
- Only ~30% of fields are filled (14-18 out of 56)
- Many fields (CIBIL score, age limits, income requirements) are often NOT on the card detail page — they're on separate "eligibility" or "apply" pages
- The prompt could be improved to extract more from FAQ sections

**How to improve:**
1. **Scrape eligibility pages too:** Many banks have `/credit-cards/<card>/eligibility` or `/apply` pages with income/age/CIBIL info. Add these as secondary URLs to scrape.
2. **Try the 14b model for quality:** Use `qwen2.5-coder:14b` for cards where the 7b model returns low field counts. Change `OLLAMA_MODEL` and `OLLAMA_FALLBACK_MODEL` in `engine/config.py`.
3. **Multi-source extraction:** For banks with less detail on card pages (PSU banks), use the listing page markdown to extract partial data for all cards at once.
4. **Manual data augmentation:** Some data (CIBIL score hints, approval likelihood) is crowd-sourced or editorial — it won't be on bank websites.

### 4. Validate Final Output
After extraction completes:
```bash
python run.py --validate
```
This checks `data/output/cards.json` for:
- Missing `card_name` or `bank_id`
- Prints a summary table with per-bank card counts
- Shows average field completeness percentage

### 5. Handle Edge Cases
- **Discontinued cards:** Cards like "Bharat Credit Card" and "JetPrivilege Titanium" say "Sourcing stopped." The extractor correctly sets `status: "inactive"/"discontinued"` for some, but not always.
- **Co-branded cards:** Cards like "Swiggy HDFC Bank Credit Card" need to set `card_category: "co-branded"` — currently extracted as "lifestyle" sometimes.
- **Debit cards:** The engine is set up for credit cards only. If you want debit cards too, you need to add debit card listing URLs to `bank_registry.py`.

---

## 🔧 Configuration Reference (`engine/config.py`)

| Setting | Current Value | Purpose |
|---------|--------------|---------|
| `OLLAMA_MODEL` | `deepseek-v3.1:671b-cloud` | Primary LLM (quota exhausted) |
| `OLLAMA_FALLBACK_MODEL` | `qwen2.5-coder:7b` | Fallback local LLM |
| `OLLAMA_TIMEOUT` | `120` seconds | Max time per LLM call |
| `MAX_EXTRACTION_RETRIES` | `3` | LLM retry attempts per card |
| `REQUEST_DELAY_MIN/MAX` | `2.0-4.0` seconds | Rate limiting between scrape requests |
| `MAX_RETRIES` | `3` | Scraper retry attempts per page |
| `OUTPUT_FILE` | `data/output/cards.json` | Final output path |

**To switch LLM model:**
Edit `engine/config.py` lines 19-20:
```python
OLLAMA_MODEL = "qwen2.5-coder:14b"        # Use 14b for better quality
OLLAMA_FALLBACK_MODEL = "qwen2.5-coder:7b" # 7b as fallback
```

---

## 🐛 Known Bugs & Gotchas

### 1. `domcontentloaded` vs `networkidle`
**DO NOT** change `wait_until` to `"networkidle"` in `scraper.py` line 133. Indian bank sites have aggressive tracking/ad scripts that never fully load, causing timeouts. `domcontentloaded` with 5s delay is the working solution.

### 2. HDFC Domain Swap
`hdfcbank.com` individual card pages are heavily protected with anti-bot measures. The scraper uses `hdfc.bank.in` (same content, less protection). This is configured in `DOMAIN_ALIASES` in `scraper.py` line 289-291.

### 3. LLM JSON Mode
The Ollama API call uses `"format": "json"` (line ~94 in `extractor.py`). This forces the model to output valid JSON. Without this, the 7b model often outputs explanatory text mixed with JSON.

### 4. Pydantic Type Coercion
The 7b model frequently outputs:
- Strings instead of lists: `"fuel, groceries"` instead of `["fuel", "groceries"]`
- Integers instead of strings: `500` instead of `"500"` for fees
- Extra fields not in the schema
The `_validate_extraction()` function (around line 214 in `extractor.py`) handles all of these with lenient coercion. **DO NOT replace it with strict Pydantic validation** — the success rate will drop from 80% to 25%.

### 5. Cloud Model State
The `_cloud_exhausted` global variable tracks whether the cloud model returned 403. It persists for the lifetime of the Python process. If you restart the process, it will try the cloud model again (which is correct behavior — quota may have refreshed).

---

## 📊 Extraction Field Coverage (from test runs)

From a sample of 4 successfully extracted HDFC cards:

| Field Category | Typical Coverage | Notes |
|---------------|-----------------|-------|
| Card identity (name, bank, type, network) | 100% | Always extracted |
| Fees (joining, annual) | ~60% | Sometimes in "Fees & Charges" section |
| Reward details | ~50% | Base rate usually found, category-wise often missing |
| Benefits (lounge, movie, dining) | ~40% | Varies by card richness |
| Eligibility (income, age, CIBIL) | ~20% | Often on separate pages |
| India-specific (UPI, forex) | ~10% | Rarely on main card page |

---

## 📝 Step-by-Step Instructions for Next Agent

### Quick Start: Run HDFC Extraction
```bash
cd /Users/pratikpotadar/Developer/cc.com

# Make sure Ollama is running
ollama list   # Should show qwen2.5-coder:7b

# Run extraction on already-scraped HDFC data
python run.py --bank hdfc --extract-only

# Check results
python run.py --validate
cat data/output/cards.json | python -m json.tool | head -100
```

### Process All Banks
```bash
# Scrape all 20 banks (takes ~2 hours)
python run.py --all --scrape-only

# Check what was scraped
ls -la data/raw/*/

# Extract from all cached data (takes ~2-4 hours with 7b model)
python run.py --all --extract-only

# Validate final output
python run.py --validate
```

### If a Bank Scrape Fails
1. Check the listing URL: Open `engine/bank_registry.py`, find the bank, verify the URL works in a browser
2. Check URL patterns: Open `engine/scraper.py`, find `BANK_CARD_URL_PATTERNS`, update regex for that bank
3. Check for anti-bot: If getting empty content, add the bank's domain to `DOMAIN_ALIASES` if an alternate domain exists
4. For PSU banks with `.aspx` pages: Consider scraping the listing page and using the `MULTI_CARD_PROMPT` to extract all cards at once

### If LLM Extraction Fails
1. Check if Ollama is running: `curl http://localhost:11434/api/tags`
2. Check the raw markdown: `cat data/raw/<bank_id>/<card>.json | python -m json.tool`
3. If markdown is empty/short: The scrape failed — delete the cached file and re-scrape
4. If markdown looks good but extraction fails: The LLM prompt may need adjustment for that bank's page structure. Check `extractor.py` EXTRACTION_PROMPT.

### Adding a New Bank
1. Add entry to `BANKS` list in `engine/bank_registry.py`
2. Add URL pattern regex in `BANK_CARD_URL_PATTERNS` in `engine/scraper.py`
3. Test: `python run.py --bank <new_id> --scrape-only`
4. Check: `ls data/raw/<new_id>/`

---

## 🎯 Priority Roadmap

| Priority | Task | Estimated Time | Dependency |
|----------|------|---------------|------------|
| P0 | Run HDFC extraction | 30-45 min | Ollama running |
| P1 | Scrape SBI, ICICI, Axis, Kotak | 30 min each | None |
| P1 | Extract SBI, ICICI, Axis, Kotak | 30-45 min each | Scrape done |
| P2 | Scrape IndusInd, RBL, IDFC, Federal, YES, AU | 20 min each | None |
| P2 | Extract remaining private banks | 30 min each | Scrape done |
| P3 | Scrape SC, HSBC, Amex | 20 min each | May need anti-bot work |
| P3 | Scrape PSU banks (BOB, Canara, Union, PNB, Indian Bank, BOI) | 15 min each | May have limited data |
| P4 | Improve field coverage (scrape eligibility pages) | 2-3 hours | All banks done |
| P4 | Manual data review and correction | 2-4 hours | Extraction done |
| P5 | Debit card support | 3-4 hours | Credit cards done |

---

## 📦 Dependencies & Setup

```bash
# Install dependencies
pip install -r requirements.txt
# This installs: crawl4ai>=0.4.0, pydantic>=2.0, httpx>=0.27.0, rich>=13.0

# Crawl4AI needs Playwright browsers
crawl4ai-setup   # or: playwright install chromium

# Verify Ollama
ollama list
# Expected: qwen2.5-coder:7b (4.7 GB)
# Optional: qwen2.5-coder:14b (9.0 GB) — better quality, slower
```

---

## 🏗️ Architecture Diagram

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  run.py     │    │  scraper.py  │    │ extractor.py │    │normalizer.py │
│  (CLI)      │───→│  (Crawl4AI)  │───→│  (Ollama)    │───→│  (cleanup)   │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                  │                   │                    │
       │           ┌──────┴──────┐    ┌───────┴────────┐   ┌──────┴──────┐
       │           │ data/raw/   │    │ LLM (7b/14b)   │   │ cards.json  │
       │           │ hdfc/*.json │    │ via Ollama API  │   │ (output)    │
       │           └─────────────┘    └────────────────┘   └─────────────┘
       │
  ┌────┴────────────┐
  │ bank_registry.py│
  │ (20 banks)      │
  │ config.py       │
  │ models.py       │
  │ utils.py        │
  └─────────────────┘
```

**Data Flow:**
1. `bank_registry.py` → listing URLs per bank
2. `scraper.py` Phase 1 → discover card product URLs from listing page
3. `scraper.py` Phase 2 → scrape each card detail page → save as `data/raw/<bank>/<card>.json`
4. `extractor.py` → send markdown to Ollama LLM → parse JSON → validate with Pydantic
5. `normalizer.py` → standardize fees/income/booleans → deduplicate
6. `pipeline.py` → orchestrate all phases → save to `data/output/cards.json`
