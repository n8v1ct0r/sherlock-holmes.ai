# Technology Stack

**Analysis Date:** 2026-03-15

## Languages

**Primary:**
- Python 3.12+ - All application logic, agents, and CLI

**Secondary:**
- HTML/CSS/JavaScript - Minimal single-page viewer UI served by FastAPI (inline in `sherlock/api.py`)

## Runtime

**Environment:**
- Python 3.12+
- Async runtime via `asyncio`

**Package Manager:**
- `uv` (Rust-based package manager)
- Lockfile: `uv.lock` (present)

## Frameworks

**Core:**
- FastAPI 0.115.0+ - REST API server for investigation endpoints and report viewer
- Typer 0.15.0+ - CLI framework for command-line interface
- Pydantic 2.10.0+ - Data validation and serialization
- Pydantic Settings 2.7.0+ - Environment-based configuration management

**LLM & AI:**
- Anthropic API (anthropic>=0.42.0) - Primary LLM integration for Claude models
  - Default model: `claude-sonnet-4-20250514`
  - Deep analysis model: `claude-opus-4-6`

**Web & Scraping:**
- httpx 0.28.0+ - Async HTTP client for web requests
- BeautifulSoup4 4.12.0+ - HTML parsing and text extraction
- crawl4ai 0.4.0+ - Advanced web crawling (installed but appears to be fallback/future use)

**Document Processing:**
- pymupdf 1.25.0+ (fitz) - PDF text extraction
- pdfplumber 0.11.0+ - PDF parsing and analysis
- python-docx 1.1.0+ - DOCX file parsing

**CLI & Display:**
- Rich 13.9.0+ - Styled terminal output, progress bars, panels
- Typer (with [all] extras) - CLI framework with click integration

**Server & ASGI:**
- Uvicorn 0.34.0+ (with [standard] extras) - ASGI server
- Jinja2 3.1.0+ - Template rendering (for future use)

**Telegram Integration:**
- python-telegram-bot 21.9+ - Bot framework for Telegram notifications and message handling

**Async Utilities:**
- aiosqlite 0.20.0+ - Async SQLite database access (currently unused but configured)

## Key Dependencies

**Critical:**
- anthropic 0.42.0+ - Core LLM functionality; all agent reasoning depends on this
- fastapi + uvicorn - API server for web interface and programmatic access
- typer - CLI entrypoint; no investigation can be triggered without this
- pydantic - Data validation; all models depend on Pydantic serialization

**Infrastructure:**
- httpx - Web scraping and search engine integration
- beautifulsoup4 - HTML parsing for evidence extraction
- python-telegram-bot - User notifications and Telegram bot interface
- pymupdf, pdfplumber, python-docx - Document analysis capability

**Development:**
- pytest 8.3.0+ - Test runner
- pytest-asyncio 0.24.0+ - Async test support
- mypy 1.13.0+ - Static type checking
- ruff 0.8.0+ - Linting and formatting (combined with isort)
- pre-commit 4.0.0+ - Git hook management

## Configuration

**Environment:**
- `.env` file (expected) - Required environment variables
- `.env.example` present at project root (template for configuration)
- Configuration via `pydantic-settings` with `SHERLOCK_` prefix

**Build:**
- `pyproject.toml` - Project metadata, dependencies, build configuration
- `hatchling` - Build backend
- Wheel packages target: `sherlock/` directory

## Environment Variables

**Required:**
- `ANTHROPIC_API_KEY` - Claude API key (sk-ant-...)

**Optional:**
- `SHERLOCK_MODEL` - Override default model (default: claude-sonnet-4-20250514)
- `SHERLOCK_DEEP_MODEL` - Model for deep analysis passes (default: claude-opus-4-6)
- `SHERLOCK_CACHE_DIR` - Request cache directory (default: .sherlock_cache)
- `SHERLOCK_OUTPUT_DIR` - Report output directory (default: sherlock/outputs)
- `SHERLOCK_MAX_WEB_RESULTS` - Max web search results per query (default: 10)
- `SHERLOCK_MAX_SCRAPE_DEPTH` - Max scraping depth (default: 2)
- `SHERLOCK_REQUEST_TIMEOUT` - HTTP request timeout in seconds (default: 30)
- `SHERLOCK_MAX_CONCURRENT_REQUESTS` - Max parallel web requests (default: 5)
- `SHERLOCK_REPORT_FORMAT` - Output format: markdown|json|html (default: markdown)
- `SHERLOCK_TELEGRAM_BOT_TOKEN` - Telegram bot token (optional; required for bot mode)
- `SHERLOCK_TELEGRAM_CHAT_ID` - Telegram chat ID for notifications (optional)

## Platform Requirements

**Development:**
- Python 3.12+
- macOS/Linux/Windows with Python and uv package manager
- Network access to Anthropic API, web search services, and Telegram API

**Production:**
- Python 3.12+ runtime
- Anthropic API key with appropriate quotas
- Optional: Telegram bot token and chat ID for notifications
- SQLite database support (aiosqlite available but not yet utilized)
- Network access: Anthropic API, public web (via httpx), Telegram API (optional)
- File system: Write access to `.sherlock_cache/` and configured `output_dir`

## Execution Models

**CLI Mode** (via `sherlock investigate`):
- Entry point: `sherlock/cli.py`
- Synchronous wrapper around async operations
- Uses Typer for argument parsing and Rich for progress display

**API Mode** (via `sherlock serve`):
- FastAPI server with OpenAPI documentation
- Endpoints: `/investigate` (POST), `/reports` (GET), `/reports/{filename}` (GET)
- Single-page viewer UI served at root endpoint

**Telegram Bot Mode** (via `sherlock telegram`):
- Polling-based bot application
- Listens for messages; kicks off investigation on command
- Sends results back to configured chat

## Caching Strategy

**Web Request Cache:**
- File-based cache using SHA256-hashed cache keys
- Storage: `.sherlock_cache/{key}.json`
- Prevents redundant web requests during development/iteration
- Cache read/write happens in `sherlock/tools/web.py`

---

*Stack analysis: 2026-03-15*
