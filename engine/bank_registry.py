"""
Bank URL registry for all 20 Indian banks.
Contains listing page URLs and metadata for the scraper.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class BankInfo:
    """Metadata and URLs for a single bank."""
    bank_id: str
    bank_name: str
    short_code: str
    credit_card_listing_url: str
    card_type: str = "credit"  # credit, debit, or both
    link_selector: str = ""  # CSS selector hint for card links on listing page
    notes: str = ""
    extra_listing_urls: list[str] = field(default_factory=list)


# ── All 20 Banks ──────────────────────────────────────────────────────────
BANKS: list[BankInfo] = [
    BankInfo(
        bank_id="hdfc",
        bank_name="HDFC Bank",
        short_code="HDFC",
        credit_card_listing_url="https://www.hdfcbank.com/personal/pay/cards/credit-cards",
        link_selector="a[href*='credit-cards']",
        notes="hdfcbank.com has anti-bot. Use hdfc.bank.in for detail pages.",
        # hdfc.bank.in is the newer domain, less bot protection
        extra_listing_urls=["https://www.hdfc.bank.in/personal/pay/cards/credit-cards"],
    ),
    BankInfo(
        bank_id="sbi",
        bank_name="State Bank of India (SBI Card)",
        short_code="SBI",
        credit_card_listing_url="https://www.sbicard.com/en/personal/credit-cards.page",
        link_selector="a[href*='credit-card']",
        notes="Dedicated sbicard.com domain. Well-structured pages.",
    ),
    BankInfo(
        bank_id="icici",
        bank_name="ICICI Bank",
        short_code="ICICI",
        credit_card_listing_url="https://www.icicibank.com/personal-banking/cards/credit-card",
        link_selector="a[href*='credit-card']",
        notes="Modern site with JS rendering.",
    ),
    BankInfo(
        bank_id="axis",
        bank_name="Axis Bank",
        short_code="AXIS",
        credit_card_listing_url="https://www.axisbank.com/retail/cards/credit-card",
        link_selector="a[href*='credit-card']",
        notes="Restructured URLs in 2025. Some PDF-based MITC docs.",
    ),
    BankInfo(
        bank_id="kotak",
        bank_name="Kotak Mahindra Bank",
        short_code="KOTAK",
        credit_card_listing_url="https://www.kotak.com/en/personal-banking/cards/credit-cards.html",
        link_selector="a[href*='credit-card']",
        notes="Standard HTML with some dynamic content.",
    ),
    BankInfo(
        bank_id="indusind",
        bank_name="IndusInd Bank",
        short_code="INDUSIND",
        credit_card_listing_url="https://www.indusind.com/in/en/personal/cards/credit-card.html",
        link_selector="a[href*='credit-card']",
        notes="Decent HTML structure. Multiple card categories.",
    ),
    BankInfo(
        bank_id="rbl",
        bank_name="RBL Bank",
        short_code="RBL",
        credit_card_listing_url="https://www.rblbank.com/credit-cards",
        link_selector="a[href*='credit-card']",
        notes="Clean modern website.",
    ),
    BankInfo(
        bank_id="idfc",
        bank_name="IDFC FIRST Bank",
        short_code="IDFC",
        credit_card_listing_url="https://www.idfcfirstbank.com/credit-card",
        link_selector="a[href*='credit-card']",
        notes="Well-structured modern site. Known for good card features.",
    ),
    BankInfo(
        bank_id="federal",
        bank_name="Federal Bank",
        short_code="FEDERAL",
        credit_card_listing_url="https://www.federalbank.co.in/credit-card",
        link_selector="a[href*='credit-card']",
        notes="Simpler website. Fewer cards.",
    ),
    BankInfo(
        bank_id="yes",
        bank_name="YES Bank",
        short_code="YES",
        credit_card_listing_url="https://www.yesbank.in/personal-banking/yes-individual/cards/credit-card",
        link_selector="a[href*='credit-card']",
        notes="Moderate number of cards.",
    ),
    BankInfo(
        bank_id="au",
        bank_name="AU Small Finance Bank",
        short_code="AU",
        credit_card_listing_url="https://www.aubank.in/credit-cards",
        link_selector="a[href*='credit-card']",
        notes="Growing card portfolio. Clean site.",
    ),
    BankInfo(
        bank_id="sc",
        bank_name="Standard Chartered Bank",
        short_code="SC",
        credit_card_listing_url="https://www.sc.com/in/credit-cards/",
        link_selector="a[href*='credit-card']",
        notes="International bank. Good page structure.",
    ),
    BankInfo(
        bank_id="hsbc",
        bank_name="HSBC India",
        short_code="HSBC",
        credit_card_listing_url="https://www.hsbc.co.in/credit-cards/",
        link_selector="a[href*='credit-card']",
        notes="Fewer cards but premium focused.",
    ),
    BankInfo(
        bank_id="amex",
        bank_name="American Express",
        short_code="AMEX",
        credit_card_listing_url="https://www.americanexpress.com/in/credit-cards/",
        link_selector="a[href*='credit-card']",
        notes="Premium cards. Well-structured site.",
    ),
    BankInfo(
        bank_id="bob",
        bank_name="Bank of Baroda",
        short_code="BOB",
        credit_card_listing_url="https://www.bankofbaroda.in/personal-banking/credit-cards",
        extra_listing_urls=[
            "https://www.bobfinancial.com/credit-cards",
        ],
        link_selector="a[href*='credit-card']",
        notes="BOB Financial handles cards. May need both domains.",
    ),
    BankInfo(
        bank_id="canara",
        bank_name="Canara Bank",
        short_code="CANARA",
        credit_card_listing_url="https://www.canarabank.com/english/scripts/creditcards.aspx",
        link_selector="a[href*='credit']",
        notes="Old-style .aspx pages. Limited online info. May have PDF-only details.",
    ),
    BankInfo(
        bank_id="union",
        bank_name="Union Bank of India",
        short_code="UNION",
        credit_card_listing_url="https://www.unionbankofindia.co.in/english/credit-card.aspx",
        link_selector="a[href*='credit']",
        notes="PSU bank. Basic website. Limited card details online.",
    ),
    BankInfo(
        bank_id="pnb",
        bank_name="Punjab National Bank",
        short_code="PNB",
        credit_card_listing_url="https://www.pnbcard.in/credit-card",
        link_selector="a[href*='credit-card']",
        notes="Separate pnbcard.in domain for card business.",
    ),
    BankInfo(
        bank_id="indian",
        bank_name="Indian Bank",
        short_code="INDIANBANK",
        credit_card_listing_url="https://www.indianbank.in/departments/credit-cards/",
        link_selector="a[href*='credit']",
        notes="PSU bank. Limited card portfolio.",
    ),
    BankInfo(
        bank_id="boi",
        bank_name="Bank of India",
        short_code="BOI",
        credit_card_listing_url="https://bankofindia.co.in/credit-card",
        link_selector="a[href*='credit']",
        notes="PSU bank. Basic online presence for cards.",
    ),
]


def get_bank(bank_id: str) -> BankInfo | None:
    """Get a bank by its ID."""
    for bank in BANKS:
        if bank.bank_id == bank_id:
            return bank
    return None


def get_all_bank_ids() -> list[str]:
    """Get all bank IDs."""
    return [b.bank_id for b in BANKS]


def get_bank_by_name(name: str) -> BankInfo | None:
    """Fuzzy match a bank by name substring."""
    name_lower = name.lower()
    for bank in BANKS:
        if name_lower in bank.bank_name.lower() or name_lower == bank.bank_id:
            return bank
    return None
