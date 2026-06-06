#!/usr/bin/env python3
"""Debug script to analyze HDFC listing page and find card links."""
import asyncio
import re
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    config = BrowserConfig(headless=True, browser_type="chromium", verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=60000,
        wait_until="networkidle",
        delay_before_return_html=3.0,
    )
    
    async with AsyncWebCrawler(config=config) as crawler:
        result = await crawler.arun(
            url="https://www.hdfcbank.com/personal/pay/cards/credit-cards",
            config=run_config,
        )
        
        if not result or not result.success:
            print("FAILED TO CRAWL")
            return
        
        # Save markdown
        with open("data/raw/hdfc_listing_debug.md", "w") as f:
            f.write(result.markdown[:30000])
        print(f"Markdown length: {len(result.markdown)} chars")
        print(f"HTML length: {len(result.html)} chars")
        
        # Extract ALL hrefs from HTML
        hrefs = re.findall(r'href="([^"]*)"', result.html)
        
        # Group by path pattern
        print("\n=== ALL UNIQUE PATHS CONTAINING 'card' ===")
        card_links = set()
        for href in hrefs:
            if "card" in href.lower():
                card_links.add(href)
        
        for link in sorted(card_links):
            print(f"  {link}")
        
        print(f"\nTotal card-related links: {len(card_links)}")
        
        # Look for specific card product page patterns
        print("\n=== POTENTIAL CARD PRODUCT PAGES ===")
        # HDFC individual cards usually have paths like /personal/pay/cards/credit-cards/<card-name>
        product_links = set()
        for href in hrefs:
            href_lower = href.lower()
            # Check for paths that look like individual card pages
            if re.search(r'/credit-cards?/[a-z][\w-]+(?:-card|-cards?)?$', href_lower):
                if not any(x in href_lower for x in ['/services/', '/blogs/', '/compare', '/offers', '/apply', '/faq']):
                    product_links.add(href)
        
        for link in sorted(product_links):
            print(f"  {link}")
        print(f"\nPotential product pages: {len(product_links)}")

asyncio.run(main())
