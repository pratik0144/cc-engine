"""
Web scraper using Crawl4AI to crawl Indian bank credit card pages.

Two-phase approach:
  Phase 1: Discover card URLs from listing pages using bank-specific patterns
  Phase 2: Scrape individual card detail pages
"""
from __future__ import annotations
import asyncio
import json
import random
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from engine.config import RAW_DIR, USER_AGENTS, MAX_RETRIES
from engine.bank_registry import BankInfo
from engine.utils import (
    logger,
    slugify,
    rate_limit_delay,
    clean_text,
)


# ── Per-bank URL patterns for card product pages ──────────────────────────
# Each pattern matches individual card detail page URLs (not listings/blogs/services)
BANK_CARD_URL_PATTERNS: dict[str, list[re.Pattern]] = {
    "hdfc": [
        # /credit-cards/<card-name>-credit-card  (but NOT /services/, /blogs/, etc.)
        re.compile(r'/credit-cards/[\w-]+-credit-card$', re.I),
        re.compile(r'/credit-cards/credit-card-against-fd$', re.I),
    ],
    "sbi": [
        re.compile(r'/credit-cards?/[\w-]+-card', re.I),
        re.compile(r'/en/personal/credit-cards/[\w-]+\.page$', re.I),
    ],
    "icici": [
        re.compile(r'/credit-card/[\w-]+-credit-card', re.I),
        re.compile(r'/personal-banking/cards/credit-card/[\w-]+-card', re.I),
    ],
    "axis": [
        re.compile(r'/credit-card/[\w-]+-credit-card', re.I),
        re.compile(r'/retail/cards/credit-card/[\w-]+', re.I),
    ],
    "kotak": [
        re.compile(r'/credit-cards/[\w-]+-credit-card', re.I),
        re.compile(r'/personal-banking/cards/credit-cards/[\w-]+', re.I),
    ],
    "indusind": [
        re.compile(r'/credit-card/[\w-]+', re.I),
        re.compile(r'/cards/credit-card/[\w-]+', re.I),
    ],
    "rbl": [
        re.compile(r'/credit-cards/[\w-]+', re.I),
    ],
    "idfc": [
        re.compile(r'/credit-card/[\w-]+', re.I),
    ],
    "federal": [
        re.compile(r'/credit-card/[\w-]+', re.I),
    ],
    "yes": [
        re.compile(r'/credit-card/[\w-]+', re.I),
        re.compile(r'/cards/credit-card/[\w-]+', re.I),
    ],
    "au": [
        re.compile(r'/credit-cards?/[\w-]+', re.I),
    ],
    "sc": [
        re.compile(r'/credit-cards/[\w-]+', re.I),
    ],
    "hsbc": [
        re.compile(r'/credit-cards/[\w-]+', re.I),
    ],
    "amex": [
        re.compile(r'/credit-cards/[\w-]+', re.I),
    ],
    "bob": [
        re.compile(r'/credit-cards?/[\w-]+', re.I),
    ],
    "canara": [
        re.compile(r'/credit\w*', re.I),
    ],
    "union": [
        re.compile(r'/credit.card', re.I),
    ],
    "pnb": [
        re.compile(r'/credit-card/[\w-]+', re.I),
    ],
    "indian": [
        re.compile(r'/credit-card', re.I),
    ],
    "boi": [
        re.compile(r'/credit-card', re.I),
    ],
}

# Paths to always exclude (services, blogs, tools, etc.)
EXCLUDE_PATH_PATTERNS = [
    r'/services/', r'/blogs?/', r'/blog/', r'/faq', r'/contact',
    r'/apply', r'/login', r'/register', r'/terms', r'/privacy',
    r'/sitemap', r'/careers', r'/about', r'/netbanking', r'/compare',
    r'/offers', r'/emi-calc', r'/calculator', r'/track', r'/status',
    r'/bill-payment', r'/activation', r'/upgrade', r'/pin',
    r'/limit-enhancement', r'/claim-rewards', r'/fee-waiver',
    r'/forgot', r'/block', r'/customer', r'/reward-point',
    r'/premium-and-super', r'/how-to', r'/what-is', r'/what-are',
    r'/tips', r'scene7\.com', r'/xpressway/', r'/insta-services/',
]
EXCLUDE_RE = re.compile('|'.join(EXCLUDE_PATH_PATTERNS), re.I)


def _browser_config() -> BrowserConfig:
    """Create browser config for stealth crawling."""
    return BrowserConfig(
        headless=True,
        browser_type="chromium",
        user_agent=random.choice(USER_AGENTS),
        viewport_width=1920,
        viewport_height=1080,
        verbose=False,
    )


def _crawl_config() -> CrawlerRunConfig:
    """Create crawler run config."""
    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=90000,
        wait_until="domcontentloaded",
        delay_before_return_html=5.0,
        word_count_threshold=10,
        excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
        exclude_external_links=False,
        process_iframes=False,
    )


async def crawl_page(crawler: AsyncWebCrawler, url: str, retries: int = MAX_RETRIES) -> dict | None:
    """
    Crawl a single page and return result dict with markdown and metadata.
    Retries on failure with exponential backoff.
    """
    for attempt in range(retries):
        try:
            config = _crawl_config()
            result = await crawler.arun(url=url, config=config)

            if result and result.success:
                return {
                    "url": url,
                    "markdown": result.markdown or "",
                    "html": result.html or "",
                    "title": getattr(result, 'title', '') or '',
                    "success": True,
                }
            else:
                error_msg = getattr(result, 'error_message', 'Unknown error') if result else 'No result'
                logger.warning(f"  Attempt {attempt + 1}/{retries} failed for {url}: {error_msg}")

        except Exception as e:
            logger.warning(f"  Attempt {attempt + 1}/{retries} error for {url}: {e}")

        if attempt < retries - 1:
            wait = (2 ** attempt) + random.uniform(1, 3)
            logger.debug(f"  Retrying in {wait:.1f}s...")
            await asyncio.sleep(wait)

    logger.error(f"  All {retries} attempts failed for {url}")
    return None


def _is_card_product_url(href: str, bank_id: str) -> bool:
    """
    Check if a URL path is a card product page for the given bank.
    Uses bank-specific patterns and excludes service/blog pages.
    """
    # Exclude service/blog/tool pages
    if EXCLUDE_RE.search(href):
        return False

    # Exclude image/media/document links
    if re.search(r'\.(pdf|jpg|jpeg|png|gif|svg|webp|mp4|zip)$', href, re.I):
        return False

    # Exclude javascript/anchor links
    if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
        return False

    # Check bank-specific patterns
    patterns = BANK_CARD_URL_PATTERNS.get(bank_id, [])
    for pattern in patterns:
        if pattern.search(href):
            return True

    return False


def _extract_card_urls_from_html(html: str, base_url: str, bank_id: str) -> list[str]:
    """
    Extract card product URLs from HTML using bank-specific patterns.
    """
    parsed = urlparse(base_url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"

    # Find all href values
    all_hrefs = re.findall(r'href="([^"]*)"', html)

    card_urls = []
    seen = set()
    for href in all_hrefs:
        # Make absolute
        if href.startswith('/'):
            full_url = base_domain + href
        elif href.startswith('http'):
            full_url = href
        else:
            continue

        # Normalize
        clean_url = full_url.split('?')[0].split('#')[0].rstrip('/')
        if clean_url in seen:
            continue
        seen.add(clean_url)

        # Check with bank-specific pattern
        path = urlparse(clean_url).path
        if _is_card_product_url(path, bank_id):
            card_urls.append(clean_url)

    return card_urls


async def discover_card_urls(crawler: AsyncWebCrawler, bank: BankInfo) -> list[str]:
    """
    Phase 1: Discover all individual card page URLs from the listing page.
    Uses bank-specific URL patterns for accurate filtering.
    """
    logger.info(f"🔍 Discovering cards for {bank.bank_name}...")

    all_card_urls = []

    # Crawl main listing page + any extra listing URLs
    listing_urls = [bank.credit_card_listing_url] + bank.extra_listing_urls

    for listing_url in listing_urls:
        logger.info(f"  Crawling listing: {listing_url}")
        result = await crawl_page(crawler, listing_url)

        if not result:
            logger.warning(f"  Failed to crawl listing page: {listing_url}")
            continue

        # Extract links from HTML with bank-specific patterns
        card_urls = _extract_card_urls_from_html(result["html"], listing_url, bank.bank_id)
        logger.info(f"  Found {len(card_urls)} card product links from {listing_url}")

        # Also save listing page markdown for fallback multi-card extraction
        listing_cache = RAW_DIR / bank.bank_id / "listing-page.json"
        listing_cache.parent.mkdir(parents=True, exist_ok=True)
        listing_data = {
            "bank_id": bank.bank_id,
            "bank_name": bank.bank_name,
            "card_url": listing_url,
            "card_slug": "listing-page",
            "markdown": result["markdown"],
            "title": result["title"],
            "is_listing_page": True,
        }
        with open(listing_cache, 'w') as f:
            json.dump(listing_data, f, indent=2, ensure_ascii=False)

        all_card_urls.extend(card_urls)
        await rate_limit_delay()

    # Deduplicate
    all_card_urls = list(set(all_card_urls))
    logger.info(f"  Total unique card URLs for {bank.bank_name}: {len(all_card_urls)}")

    return all_card_urls


# ── Domain aliasing for anti-bot avoidance ────────────────────────────────
# Some banks serve the same content on multiple domains.
# If one domain blocks us, we can try an alternate.
DOMAIN_ALIASES = {
    "www.hdfcbank.com": "www.hdfc.bank.in",
    # Add more as we discover blocked domains
}


def _swap_domain(url: str) -> str | None:
    """Swap a URL's domain to an alternate if available."""
    parsed = urlparse(url)
    alt_domain = DOMAIN_ALIASES.get(parsed.netloc)
    if alt_domain:
        return url.replace(parsed.netloc, alt_domain, 1)
    return None


async def scrape_card_page(
    crawler: AsyncWebCrawler,
    bank: BankInfo,
    card_url: str,
) -> dict | None:
    """
    Phase 2: Scrape a single card detail page and cache the raw content.
    Tries alternate domain if primary fails.
    """
    # Generate slug from URL
    card_slug = slugify(card_url.split('/')[-1] or card_url.split('/')[-2])
    if not card_slug:
        card_slug = slugify(urlparse(card_url).path.replace('/', '-'))

    bank_dir = RAW_DIR / bank.bank_id
    bank_dir.mkdir(parents=True, exist_ok=True)
    cache_file = bank_dir / f"{card_slug}.json"

    # Check cache
    if cache_file.exists():
        logger.debug(f"  Cache hit: {cache_file.name}")
        try:
            with open(cache_file) as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass  # Re-scrape if cache is corrupted

    # Try primary URL first
    urls_to_try = [card_url]
    alt_url = _swap_domain(card_url)
    if alt_url:
        # Try alternate domain first (it's usually less blocked)
        urls_to_try = [alt_url, card_url]

    result = None
    for try_url in urls_to_try:
        logger.info(f"  📄 Scraping: {try_url}")
        result = await crawl_page(crawler, try_url, retries=2)
        if result:
            break
        logger.warning(f"  Failed on {try_url}, trying next...")

    if not result:
        return None

    # Save to cache
    cache_data = {
        "bank_id": bank.bank_id,
        "bank_name": bank.bank_name,
        "card_url": card_url,
        "card_slug": card_slug,
        "markdown": result["markdown"],
        "title": result["title"],
    }

    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2, ensure_ascii=False)

    logger.debug(f"  Cached: {cache_file.name} ({len(result['markdown'])} chars)")
    return cache_data


async def scrape_bank(bank: BankInfo, resume: bool = True) -> list[dict]:
    """
    Full scrape pipeline for a single bank:
    1. Discover card URLs from listing page
    2. Scrape each card detail page
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"🏦 Processing: {bank.bank_name}")
    logger.info(f"{'='*60}")

    bank_dir = RAW_DIR / bank.bank_id
    bank_dir.mkdir(parents=True, exist_ok=True)
    urls_cache = bank_dir / "_discovered_urls.json"

    async with AsyncWebCrawler(config=_browser_config()) as crawler:
        # Phase 1: Discover URLs
        if resume and urls_cache.exists():
            with open(urls_cache) as f:
                card_urls = json.load(f)
            logger.info(f"  Loaded {len(card_urls)} cached URLs")
        else:
            card_urls = await discover_card_urls(crawler, bank)
            with open(urls_cache, 'w') as f:
                json.dump(card_urls, f, indent=2)

        if not card_urls:
            logger.warning(f"  No individual card URLs found for {bank.bank_name}")
            logger.info(f"  Will use listing page for multi-card extraction")
            listing_file = bank_dir / "listing-page.json"
            if listing_file.exists():
                with open(listing_file) as f:
                    return [json.load(f)]
            return []

        # Phase 2: Scrape each card page
        results = []
        failed = 0
        for i, url in enumerate(card_urls, 1):
            logger.info(f"  [{i}/{len(card_urls)}] {url}")
            card_data = await scrape_card_page(crawler, bank, url)
            if card_data:
                results.append(card_data)
            else:
                failed += 1
                # If too many consecutive failures, likely blocked
                if failed >= 5 and len(results) == 0:
                    logger.warning(f"  ⚠️ {failed} consecutive failures. Site may be blocking us.")
                    logger.info(f"  Falling back to listing page extraction.")
                    listing_file = bank_dir / "listing-page.json"
                    if listing_file.exists():
                        with open(listing_file) as f:
                            results.append(json.load(f))
                    break
            await rate_limit_delay()

        logger.info(f"  ✅ {bank.bank_name}: {len(results)}/{len(card_urls)} pages scraped")
        return results

