"""
Data normalizer and cleaner for extracted card data.

Standardizes fees, income formats, boolean values, categories,
generates IDs, and deduplicates cards.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone

from engine.utils import logger, generate_card_id, slugify


# ── Fee Normalization ─────────────────────────────────────────────────────

def normalize_fee(value: str | None) -> str | None:
    """
    Normalize fee values to a consistent format.
    Examples:
        "₹500 + GST" → "500+GST"
        "Rs. 1,499" → "1499"
        "Nil" → "0"
        "Free" → "0"
        "Lifetime Free" → "0"
    """
    if value is None:
        return None

    val = str(value).strip()
    val_lower = val.lower()

    # Free / Nil / Waived / No fee
    if any(kw in val_lower for kw in ['nil', 'free', 'waived', 'no fee', 'no charge', 'zero', 'n/a', 'na', 'none']):
        return "0"

    # Remove currency symbols and normalize
    val = val.replace('₹', '').replace('Rs.', '').replace('Rs', '').replace('INR', '')
    val = val.replace(',', '').strip()

    # Keep "+GST" annotation if present
    has_gst = '+gst' in val.lower() or '+ gst' in val.lower()
    val = re.sub(r'\+?\s*gst', '', val, flags=re.IGNORECASE).strip()

    # Extract numeric value
    match = re.search(r'(\d+(?:\.\d+)?)', val)
    if match:
        num = match.group(1)
        # Remove trailing .0
        if num.endswith('.0'):
            num = num[:-2]
        return f"{num}+GST" if has_gst else num

    return value  # Return original if can't parse


def normalize_income(value: str | None) -> str | None:
    """
    Normalize income to annual amount in INR.
    Examples:
        "3 LPA" → "300000"
        "25,000 p.m." → "300000"
        "₹6 Lakhs per annum" → "600000"
        "25000/month" → "300000"
    """
    if value is None:
        return None

    val = str(value).strip()
    val_lower = val.lower()

    if any(kw in val_lower for kw in ['nil', 'n/a', 'na', 'none', 'not specified']):
        return None

    # Remove currency symbols
    val = val.replace('₹', '').replace('Rs.', '').replace('Rs', '').replace('INR', '').replace(',', '').strip()

    # Extract number
    match = re.search(r'(\d+(?:\.\d+)?)', val)
    if not match:
        return value

    num = float(match.group(1))

    # Determine if monthly or annual
    is_monthly = any(kw in val_lower for kw in ['p.m', 'per month', '/month', 'monthly', 'p.m.', '/mo'])
    is_lakh = any(kw in val_lower for kw in ['lakh', 'lac', 'lpa', 'l p.a', 'l.p.a'])
    is_crore = any(kw in val_lower for kw in ['crore', 'cr'])

    if is_crore:
        num *= 10000000
    elif is_lakh:
        num *= 100000
    elif is_monthly:
        num *= 12
    elif num < 1000:
        # Small number likely in lakhs
        num *= 100000

    return str(int(num))


def normalize_boolean(value: str | None) -> str | None:
    """
    Normalize boolean-like values.
    "Yes" / "Available" / "✓" → "yes"
    "No" / "Not Available" / "✗" → "no"
    """
    if value is None:
        return None

    val = str(value).strip().lower()

    yes_indicators = ['yes', 'true', 'available', '✓', '✔', 'supported', 'included', 'applicable']
    no_indicators = ['no', 'false', 'not available', '✗', '✘', 'not supported', 'not included', 'na', 'n/a']

    if any(kw in val for kw in yes_indicators):
        return "yes"
    if any(kw == val for kw in no_indicators):
        return "no"

    return value  # Keep original for descriptive values


def normalize_card_type(value: str | None) -> str | None:
    """Normalize card type to 'credit' or 'debit'."""
    if value is None:
        return "credit"  # Default to credit
    val = value.lower().strip()
    if 'debit' in val:
        return "debit"
    return "credit"


def normalize_network(value: str | None) -> str | None:
    """Normalize card network names."""
    if value is None:
        return None
    val = value.lower().strip()
    mapping = {
        'visa': 'Visa',
        'mastercard': 'Mastercard',
        'master card': 'Mastercard',
        'master': 'Mastercard',
        'rupay': 'RuPay',
        'ru pay': 'RuPay',
        'amex': 'Amex',
        'american express': 'Amex',
        'diners': 'Diners Club',
        'diners club': 'Diners Club',
    }
    for key, normalized in mapping.items():
        if key in val:
            return normalized
    return value


def normalize_category(value: str | None) -> str | None:
    """Normalize card category to standard values."""
    if value is None:
        return None
    val = value.lower().strip()
    mapping = {
        'cashback': 'cashback',
        'cash back': 'cashback',
        'travel': 'travel',
        'fuel': 'fuel',
        'reward': 'rewards',
        'rewards': 'rewards',
        'lifestyle': 'lifestyle',
        'premium': 'premium',
        'super premium': 'premium',
        'entry': 'entry-level',
        'entry-level': 'entry-level',
        'basic': 'entry-level',
        'student': 'student',
        'luxury': 'luxury',
        'business': 'business',
        'corporate': 'business',
        'shopping': 'shopping',
        'co-brand': 'co-branded',
        'co brand': 'co-branded',
        'cobranded': 'co-branded',
    }
    for key, normalized in mapping.items():
        if key in val:
            return normalized
    return val


def normalize_variant(value: str | None) -> str | None:
    """Normalize card variant/tier."""
    if value is None:
        return None
    val = value.lower().strip()
    mapping = {
        'classic': 'classic',
        'gold': 'gold',
        'platinum': 'platinum',
        'titanium': 'titanium',
        'signature': 'signature',
        'infinite': 'infinite',
        'world': 'world',
        'select': 'select',
        'elite': 'elite',
        'regalia': 'regalia',
    }
    for key, normalized in mapping.items():
        if key in val:
            return normalized
    return val


# ── Full Card Normalization ───────────────────────────────────────────────

def normalize_card(card: dict, bank_id: str) -> dict:
    """Apply all normalizations to a single card."""
    # Generate IDs
    card_name = card.get("card_name", "unknown")
    card["card_id"] = generate_card_id(bank_id, card_name)
    card["bank_id"] = bank_id
    card["last_verified_at"] = datetime.now(timezone.utc).isoformat()

    # Normalize specific fields
    card["card_type"] = normalize_card_type(card.get("card_type"))
    card["card_network"] = normalize_network(card.get("card_network"))
    card["card_category"] = normalize_category(card.get("card_category"))
    card["variant"] = normalize_variant(card.get("variant"))

    # Normalize fees
    fee_fields = [
        "joining_fee", "annual_fee", "late_payment_fee",
        "cash_withdrawal_fee", "add_on_card_fee",
        "reward_redemption_fee",
    ]
    for field in fee_fields:
        card[field] = normalize_fee(card.get(field))

    # Normalize income
    card["minimum_income"] = normalize_income(card.get("minimum_income"))
    card["annual_fee_waiver_spend"] = normalize_fee(card.get("annual_fee_waiver_spend"))

    # Normalize boolean-like fields
    bool_fields = [
        "rupay_upi_supported", "salary_account_required",
    ]
    for field in bool_fields:
        card[field] = normalize_boolean(card.get(field))

    # Clean status
    if card.get("status"):
        status = card["status"].lower().strip()
        card["status"] = "active" if "active" in status or "available" in status else "discontinued"
    else:
        card["status"] = "active"

    return card


# ── Deduplication ─────────────────────────────────────────────────────────

def deduplicate_cards(cards: list[dict]) -> list[dict]:
    """
    Remove duplicate cards based on bank_id + card_name.
    When duplicates found, keep the one with more non-null fields.
    """
    seen = {}  # key: (bank_id, card_name_slug) → card

    for card in cards:
        bank_id = card.get("bank_id", "")
        card_name = card.get("card_name", "")
        key = (bank_id, slugify(card_name))

        if key in seen:
            # Keep the one with more data
            existing = seen[key]
            existing_fields = sum(1 for v in existing.values() if v is not None)
            new_fields = sum(1 for v in card.values() if v is not None)

            if new_fields > existing_fields:
                logger.debug(f"  Replacing duplicate: {card_name} ({new_fields} > {existing_fields} fields)")
                seen[key] = card
        else:
            seen[key] = card

    deduped = list(seen.values())
    removed = len(cards) - len(deduped)
    if removed > 0:
        logger.info(f"  Removed {removed} duplicate cards")

    return deduped


def normalize_all_cards(cards: list[dict], bank_id: str) -> list[dict]:
    """Normalize and deduplicate a list of cards."""
    normalized = []
    for card in cards:
        try:
            normalized.append(normalize_card(card, bank_id))
        except Exception as e:
            logger.warning(f"  Normalization error for {card.get('card_name', '?')}: {e}")
            normalized.append(card)  # Keep unnormalized rather than lose data

    return deduplicate_cards(normalized)
