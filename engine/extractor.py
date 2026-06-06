"""
LLM-based structured data extractor using Ollama.

Takes raw markdown from scraped pages and extracts structured card data
using qwen2.5-coder via Ollama's API with JSON mode.
"""
from __future__ import annotations
import json
import re
import httpx

from engine.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_FALLBACK_MODEL, OLLAMA_TIMEOUT, MAX_EXTRACTION_RETRIES
from engine.models import CardExtraction
from engine.utils import logger, truncate_text, clean_text

# Track active model — start with cloud, fallback to local
_active_model = OLLAMA_MODEL
_cloud_exhausted = False


def _get_active_model() -> str:
    """Get the currently active model, considering fallback state."""
    global _cloud_exhausted
    if _cloud_exhausted:
        return OLLAMA_FALLBACK_MODEL
    return _active_model


def _switch_to_fallback():
    """Switch to fallback local model when cloud quota is exhausted."""
    global _cloud_exhausted
    if not _cloud_exhausted:
        _cloud_exhausted = True
        logger.warning(f"  ⚠️ Cloud model quota exhausted. Switching to local: {OLLAMA_FALLBACK_MODEL}")


# ── Compact Extraction Prompt ─────────────────────────────────────────────
# Using a compact prompt to fit within context window and get better results

EXTRACTION_PROMPT = """Extract credit card details from this webpage content into JSON.

Bank: {bank_name}
URL: {card_url}

CONTENT:
{content}

Return a JSON object with these fields (use null if not found):
{{
  "card_name": "official card name",
  "bank_name": "{bank_name}",
  "card_type": "credit or debit",
  "card_network": "Visa/Mastercard/RuPay/Amex/Diners Club or null",
  "variant": "classic/gold/platinum/signature/infinite or null",
  "card_category": "cashback/travel/fuel/rewards/lifestyle/premium/entry-level/co-branded or null",
  "status": "active",
  "joining_fee": "fee amount or Nil",
  "annual_fee": "fee amount or Nil",
  "annual_fee_waiver_condition": "condition text or null",
  "annual_fee_waiver_spend": "spend amount or null",
  "late_payment_fee": "fee or null",
  "cash_withdrawal_fee": "fee or null",
  "forex_markup": "percentage or null",
  "add_on_card_fee": "fee or null",
  "reward_type": "points/cashback/miles or null",
  "reward_rate_general": "base earn rate or null",
  "reward_rate_category_wise": {{"category": "rate"}} or null,
  "bonus_categories": ["list of bonus categories"] or null,
  "welcome_bonus": "bonus details or null",
  "milestone_bonuses": ["milestone details"] or null,
  "fuel_surcharge_waiver": "details or null",
  "lounge_access": "details or null",
  "movie_offer": "details or null",
  "dining_offer": "details or null",
  "travel_benefits": "details or null",
  "insurance_benefits": "details or null",
  "emi_conversions": "details or null",
  "contactless_support": "yes/no or null",
  "minimum_income": "amount or null",
  "age_min": "min age or null",
  "age_max": "max age or null",
  "cibil_range_hint": "score range or null",
  "rupay_upi_supported": "yes/no or null",
  "upi_reward_rate": "rate or null",
  "domestic_lounge_visits": "count or null",
  "international_lounge_visits": "count or null",
  "forex_markup_percentage": "percentage or null",
  "reward_expiry_months": "months or null",
  "salary_account_benefit": "details or null"
}}

Return ONLY the JSON object."""


MULTI_CARD_PROMPT = """Extract ALL credit cards from this webpage into a JSON array.

Bank: {bank_name}
URL: {card_url}

CONTENT:
{content}

For each card found, create a JSON object with: card_name, bank_name, card_type, card_network, variant, card_category, joining_fee, annual_fee, annual_fee_waiver_condition, reward_type, reward_rate_general, welcome_bonus, fuel_surcharge_waiver, lounge_access, minimum_income.
Use null for missing fields. Return a JSON ARRAY of card objects. Return ONLY JSON."""


async def call_ollama(prompt: str, temperature: float = 0.1) -> str:
    """Call Ollama's API with auto-fallback from cloud to local model."""
    global _cloud_exhausted

    model = _get_active_model()
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "num_predict": 4096,
            "top_p": 0.9,
        },
    }

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        try:
            response = await client.post(url, json=payload)

            # Check for quota/rate limit errors (403 = cloud quota exhausted)
            if response.status_code in (429, 402, 403, 503):
                logger.warning(f"  Cloud model returned {response.status_code}")
                _switch_to_fallback()
                # Retry with fallback model
                payload["model"] = OLLAMA_FALLBACK_MODEL
                response = await client.post(url, json=payload)

            response.raise_for_status()
            result = response.json()
            resp_text = result.get("response", "")

            # Check if cloud model returned an error message instead of JSON
            if model != OLLAMA_FALLBACK_MODEL and resp_text:
                lower = resp_text.lower()
                if any(err in lower for err in ["quota", "rate limit", "exceeded", "unavailable", "error"]):
                    if not resp_text.strip().startswith("{"):
                        logger.warning(f"  Cloud model error response: {resp_text[:100]}")
                        _switch_to_fallback()
                        payload["model"] = OLLAMA_FALLBACK_MODEL
                        response = await client.post(url, json=payload)
                        response.raise_for_status()
                        result = response.json()
                        resp_text = result.get("response", "")

            return resp_text

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 402, 403, 503) and not _cloud_exhausted:
                _switch_to_fallback()
                payload["model"] = OLLAMA_FALLBACK_MODEL
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
            raise


def _parse_json_response(response_text: str) -> dict | list | None:
    """Parse JSON from LLM response, handling common formatting issues."""
    text = response_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object or array in the text
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start_idx = text.find(start_char)
        if start_idx == -1:
            continue

        depth = 0
        for i in range(start_idx, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
            if depth == 0:
                json_str = text[start_idx:i + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    break

    # Try fixing trailing commas
    fixed = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    logger.warning(f"  Failed to parse JSON from LLM response ({len(text)} chars)")
    logger.debug(f"  Response preview: {text[:200]}...")
    return None


def _validate_extraction(data: dict, bank_name: str) -> dict | None:
    """Validate extracted data — lenient mode, coerce types instead of rejecting."""
    try:
        if not data.get("card_name"):
            logger.debug(f"  Validation: no card_name in response")
            return None

        if not data.get("bank_name"):
            data["bank_name"] = bank_name

        # Handle nested "cards" key
        if "cards" in data and isinstance(data["cards"], list):
            return None  # Will be handled as multi-card

        # Coerce types for fields the LLM often gets wrong
        # list fields: if string, split by comma
        list_fields = ["bonus_categories", "milestone_bonuses", "documents_required"]
        for field in list_fields:
            val = data.get(field)
            if isinstance(val, str):
                data[field] = [item.strip() for item in val.split(",") if item.strip()]
            elif val is not None and not isinstance(val, list):
                data[field] = None

        # dict fields: if string or list, set to None
        dict_fields = ["reward_rate_category_wise"]
        for field in dict_fields:
            val = data.get(field)
            if val is not None and not isinstance(val, dict):
                # Try to keep it if it's a string description
                if isinstance(val, str):
                    data[field] = None  # Can't convert arbitrary string to dict
                else:
                    data[field] = None

        # Coerce numeric-ish fields that may come as int/float
        str_fields = [
            "joining_fee", "annual_fee", "late_payment_fee", "cash_withdrawal_fee",
            "forex_markup", "add_on_card_fee", "minimum_income", "age_min", "age_max",
            "domestic_lounge_visits", "international_lounge_visits",
            "forex_markup_percentage", "reward_expiry_months",
        ]
        for field in str_fields:
            val = data.get(field)
            if isinstance(val, (int, float)):
                data[field] = str(val)

        # Remove any extra fields not in our model
        known_fields = set(CardExtraction.model_fields.keys())
        extra_keys = set(data.keys()) - known_fields
        for key in extra_keys:
            del data[key]

        # Try Pydantic validation with coerced data
        try:
            card = CardExtraction(**data)
            return card.model_dump()
        except Exception as e:
            # If Pydantic still fails, do manual extraction with just the basic fields
            logger.debug(f"  Pydantic validation failed: {e}")
            # Fallback: keep only string fields, drop complex ones
            safe_data = {}
            for key, val in data.items():
                if key in known_fields:
                    if isinstance(val, (str, type(None))):
                        safe_data[key] = val
                    elif isinstance(val, (list, dict)):
                        safe_data[key] = None  # Drop complex types that fail
                    else:
                        safe_data[key] = str(val) if val is not None else None

            if safe_data.get("card_name"):
                try:
                    card = CardExtraction(**safe_data)
                    return card.model_dump()
                except Exception as e2:
                    logger.debug(f"  Fallback validation also failed: {e2}")

            return None
    except Exception as e:
        logger.debug(f"  Validation error: {e}")
        return None


def _preprocess_markdown(markdown: str) -> str:
    """
    Clean markdown to focus on card-relevant content.
    Removes navigation, footers, repetitive content.
    """
    lines = markdown.split('\n')
    filtered = []
    skip_patterns = [
        r'^\s*\*\s*\[.*\]\(.*\)\s*$',  # Navigation links like * [Link](url)
        r'^\s*!\[.*\]\(.*scene7.*\)',    # CDN image references
        r'^\s*!\[.*\]\(.*preview-img.*\)',  # Preview images
        r'^\s*(Apply Now|Know More|View More|Check Eligibility)',  # CTA buttons
        r'^\s*©\s*\d{4}',               # Copyright lines
        r'^\s*Follow us on',            # Social media
    ]
    skip_re = re.compile('|'.join(skip_patterns), re.I)

    seen_lines = set()
    for line in lines:
        stripped = line.strip()
        # Skip empty, very short, or duplicate lines
        if len(stripped) < 3:
            filtered.append('')
            continue
        if stripped in seen_lines:
            continue
        if skip_re.search(stripped):
            continue
        seen_lines.add(stripped)
        filtered.append(line)

    return '\n'.join(filtered)


async def extract_card_data(
    markdown: str,
    bank_name: str,
    card_url: str,
    title: str = "",
    is_listing_page: bool = False,
) -> list[dict]:
    """
    Extract structured card data from markdown using Ollama LLM.
    """
    if not markdown or len(markdown.strip()) < 100:
        logger.warning(f"  Content too short for extraction ({len(markdown)} chars)")
        return []

    # Preprocess and truncate
    cleaned = _preprocess_markdown(markdown)
    content = truncate_text(clean_text(cleaned), max_chars=8000)

    extracted_cards = []

    for attempt in range(MAX_EXTRACTION_RETRIES):
        try:
            if is_listing_page:
                prompt = MULTI_CARD_PROMPT.format(
                    bank_name=bank_name,
                    card_url=card_url,
                    content=content,
                )
            else:
                prompt = EXTRACTION_PROMPT.format(
                    bank_name=bank_name,
                    card_url=card_url,
                    content=content,
                )

            logger.info(f"  🤖 LLM call attempt {attempt + 1}/{MAX_EXTRACTION_RETRIES}...")
            response = await call_ollama(prompt)

            if not response:
                logger.warning(f"  Empty LLM response on attempt {attempt + 1}")
                continue

            parsed = _parse_json_response(response)

            if parsed is None:
                logger.warning(f"  JSON parse failed on attempt {attempt + 1}")
                continue

            # Handle nested "cards" key
            if isinstance(parsed, dict) and "cards" in parsed and isinstance(parsed["cards"], list):
                parsed = parsed["cards"]

            # Handle both single card and array of cards
            cards_list = parsed if isinstance(parsed, list) else [parsed]

            for card_data in cards_list:
                if not isinstance(card_data, dict):
                    continue
                validated = _validate_extraction(card_data, bank_name)
                if validated:
                    validated["source_url"] = card_url
                    extracted_cards.append(validated)

            if extracted_cards:
                logger.info(f"  ✅ Extracted {len(extracted_cards)} card(s) from {card_url}")
                return extracted_cards
            else:
                logger.warning(f"  No valid cards from LLM response on attempt {attempt + 1}")

        except httpx.TimeoutException:
            logger.warning(f"  LLM timeout on attempt {attempt + 1}")
        except httpx.ConnectError:
            logger.error(f"  Cannot connect to Ollama at {OLLAMA_BASE_URL}. Is it running?")
            raise
        except Exception as e:
            logger.warning(f"  Extraction error on attempt {attempt + 1}: {e}")

    logger.warning(f"  ❌ Failed to extract data after {MAX_EXTRACTION_RETRIES} attempts")
    return []


async def extract_from_cached_file(cache_file_path: str) -> list[dict]:
    """Extract card data from a cached raw JSON file."""
    with open(cache_file_path) as f:
        cached = json.load(f)

    return await extract_card_data(
        markdown=cached.get("markdown", ""),
        bank_name=cached.get("bank_name", ""),
        card_url=cached.get("card_url", ""),
        title=cached.get("title", ""),
        is_listing_page=cached.get("is_listing_page", False),
    )


async def check_ollama_health() -> bool:
    """Check if Ollama is running and required models are available."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            data = response.json()

            models = [m.get("name", "") for m in data.get("models", [])]
            active = _get_active_model()

            primary_ok = any(OLLAMA_MODEL in m for m in models)
            fallback_ok = any(OLLAMA_FALLBACK_MODEL in m for m in models)

            if primary_ok:
                logger.info(f"  ✅ Ollama: primary={OLLAMA_MODEL} (cloud), fallback={OLLAMA_FALLBACK_MODEL}")
            elif fallback_ok:
                logger.info(f"  ✅ Ollama: using fallback={OLLAMA_FALLBACK_MODEL} (local)")
                _switch_to_fallback()
            else:
                logger.error(f"  ❌ No suitable model found. Available: {models}")
                return False

            logger.info(f"  Active model: {_get_active_model()}")
            return True
    except Exception as e:
        logger.error(f"  ❌ Ollama health check failed: {e}")
        return False

