"""
Configuration and settings for the credit card data collection engine.
"""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = DATA_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "cards.json"

# Ensure directories exist
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Ollama ─────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "deepseek-v3.1:671b-cloud"
OLLAMA_FALLBACK_MODEL = "qwen2.5-coder:7b"
OLLAMA_TIMEOUT = 120  # seconds per extraction call

# ── Scraping ───────────────────────────────────────────────────────────────
REQUEST_DELAY_MIN = 2.0  # seconds between requests to same domain
REQUEST_DELAY_MAX = 4.0
MAX_RETRIES = 3
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

# ── LLM Extraction ────────────────────────────────────────────────────────
MAX_CHUNK_TOKENS = 4000  # approximate token limit per LLM call
MAX_EXTRACTION_RETRIES = 3

# ── Logging ────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
