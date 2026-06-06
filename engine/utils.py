"""
Utility helpers: logging, slugs, retry, and text processing.
"""
from __future__ import annotations
import re
import hashlib
import logging
import asyncio
import random
from functools import wraps
from rich.logging import RichHandler
from rich.console import Console

from engine.config import LOG_LEVEL, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX

console = Console()


def setup_logger(name: str = "cc_engine") -> logging.Logger:
    """Create a rich-formatted logger."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )
    return logging.getLogger(name)


logger = setup_logger()


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def generate_card_id(bank_id: str, card_name: str) -> str:
    """Generate a deterministic card ID from bank + card name."""
    raw = f"{bank_id}:{card_name.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def generate_bank_id(bank_name: str) -> str:
    """Generate a deterministic bank ID."""
    return slugify(bank_name)


async def rate_limit_delay():
    """Random delay between requests to avoid rate limiting."""
    delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
    logger.debug(f"Rate limiting: waiting {delay:.1f}s")
    await asyncio.sleep(delay)


def clean_text(text: str) -> str:
    """Clean extracted text: remove extra whitespace, normalize unicode."""
    if not text:
        return ""
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    # Normalize common unicode chars
    text = text.replace('\u20b9', '₹')
    text = text.replace('\u2013', '-')
    text = text.replace('\u2014', '-')
    text = text.replace('\u2018', "'")
    text = text.replace('\u2019', "'")
    text = text.replace('\u201c', '"')
    text = text.replace('\u201d', '"')
    return text


def truncate_text(text: str, max_chars: int = 12000) -> str:
    """Truncate text to roughly max_chars while preserving word boundaries."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]
    return truncated + "\n\n[... content truncated ...]"


def extract_urls_from_text(text: str, base_domain: str = "") -> list[str]:
    """Extract HTTP(S) URLs from text, optionally filtering by domain."""
    url_pattern = r'https?://[^\s\)\]\"\'<>]+'
    urls = re.findall(url_pattern, text)
    # Clean trailing punctuation
    cleaned = []
    for url in urls:
        url = url.rstrip('.,;:!?)')
        if base_domain and base_domain not in url:
            continue
        cleaned.append(url)
    return list(set(cleaned))


def is_card_detail_url(url: str) -> bool:
    """Heuristic to check if a URL is likely a card detail page (not listing)."""
    # Exclude obvious non-card pages
    exclude_patterns = [
        '/apply', '/login', '/register', '/faq', '/contact',
        '/terms', '/privacy', '/sitemap', '/careers', '/about',
        '/customer-service', '/locate-us', '/branch', '/atm',
        '/personal-loan', '/home-loan', '/savings', '/current-account',
        '/fixed-deposit', '/mutual-fund', '/insurance', '/demat',
        '#', 'javascript:', 'mailto:', 'tel:',
        '.pdf', '.jpg', '.png', '.gif',
        '/pay-bill', '/offers', '/emi-', '/reward',
    ]
    url_lower = url.lower()
    for pattern in exclude_patterns:
        if pattern in url_lower:
            return False

    # Must contain card-related path
    include_patterns = ['credit-card', 'creditcard', 'credit_card', 'cards/', '/card/']
    has_card_ref = any(p in url_lower for p in include_patterns)

    # Should be deeper than just the listing page (has more path segments)
    path_segments = url.split('/')
    is_deep_enough = len(path_segments) > 5

    return has_card_ref and is_deep_enough
