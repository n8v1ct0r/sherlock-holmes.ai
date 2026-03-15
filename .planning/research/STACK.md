# Technology Stack

**Project:** Sherlock Holmes AI
**Researched:** 2026-03-15
**Research basis:** Code audit of existing pyproject.toml + uv.lock (resolved versions), existing source files, training knowledge through August 2025. External network tools were unavailable during this session.

---

## Recommended Stack

### LLM / AI Layer

| Technology | Version (resolved) | Purpose | Why |
|------------|-------------------|---------|-----|
| `anthropic` | 0.84.0 | Claude API client | Only permitted LLM provider per project constraints. AsyncAnthropic supports async natively. |
| `claude-sonnet-4-20250514` | (model ID) | Default agent reasoning | Best cost/capability balance for iterative search+analysis loops |
| `claude-opus-4-6` | (model ID) | Deep analysis pass | Reserved for reporter synthesis where quality matters more than speed |

**On tool_use (function calling):** The existing codebase uses raw JSON parsing from LLM responses. The rebuild spec requires `tool_use` structured output instead. This is the correct approach — tool_use guarantees schema-valid JSON from the model without brittle string parsing or markdown code fence stripping. Use `client.messages.create(tools=[...])` with `tool_choice={"type": "any"}` to force tool invocation.

**Confidence: HIGH** — Anthropic's Python SDK is the only option given the LLM constraint. tool_use is well-documented and the correct pattern for structured output.

---

### Web Search

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `duckduckgo-search` | ^7.x | Primary search (no API key) | The `DDGS().text()` async API is the correct approach — NOT scraping html.duckduckgo.com. The existing code scrapes DDG HTML directly which is fragile and violates ToS. |
| Brave Search API (httpx) | — | Production-grade search fallback | Optional, key-gated. Better reliability, no rate-limit surprises, structured JSON response. |

**Critical finding: the existing web.py is wrong.** It scrapes `html.duckduckgo.com/html/` directly with httpx+BeautifulSoup. This is unreliable (CSS selectors break on HTML changes), rate-limited aggressively, and fragile. The `duckduckgo-search` PyPI library (`pip install duckduckgo-search`) wraps the same source but with retry logic, proper session handling, and a stable Python API (`DDGS().text(query, max_results=10)`). It is NOT currently in the lock file — it needs to be added.

**Why not Google/Bing/SerpAPI by default:** Requires paid API keys. Brave Search has a free tier (2,000 req/month) making it a reasonable optional upgrade path.

**Confidence: MEDIUM** — duckduckgo-search is widely used in the LLM agent ecosystem (LangChain, AutoGPT all default to it), but DDG rate limiting is an ongoing community complaint. Brave Search as the fallback is the right call.

---

### Web Scraping

| Technology | Version (resolved) | Purpose | Why |
|------------|-------------------|---------|-----|
| `crawl4ai` | 0.8.0 | Async JS-aware web scraping | Playwright-backed, designed specifically for LLM content extraction. Outputs clean markdown from scraped pages. |
| `httpx` | 0.28.1 | Simple HTTP requests, Brave Search API calls | For API calls and simple static pages where Crawl4AI is overkill |
| `beautifulsoup4` | 4.14.3 | HTML parsing when using httpx directly | Fallback for simple pages |

**On Crawl4AI 0.8.x:** The resolved version (0.8.0) is a significant jump from the 0.4.0 minimum. Crawl4AI changed its API substantially between 0.4.x and 0.5.x — the `AsyncWebCrawler` context manager API changed. At 0.8.x the canonical pattern is:

```python
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(timeout=15000)
    )
    if result.success:
        text = result.markdown  # LLM-ready markdown
```

**Do not use the old `crawl4ai.AsyncWebCrawler(verbose=True)` pattern from pre-0.5 docs** — it has been removed.

**Why Crawl4AI over alternatives:**
- `playwright` directly: Too low-level, requires manual content extraction logic
- `scrapy`: Synchronous-first, overkill for per-URL scraping in an async agent
- `newspaper3k`: Abandoned (last PyPI release 2022), does not handle JS-rendered pages
- `trafilatura`: Good for static sites, no JS rendering, niche extraction quality
- Raw `httpx+bs4`: Already in the codebase as fallback — fine for static pages, fails on SPAs

**Confidence: MEDIUM** — Crawl4AI is the de facto choice for LLM-focused scraping in 2025. The 0.8.x API is confirmed by the lock file but API details are from training knowledge (August 2025 cutoff). Verify `CrawlerRunConfig` parameter names against installed version before coding.

---

### Document Parsing

| Technology | Version (resolved) | Purpose | Why |
|------------|-------------------|---------|-----|
| `pymupdf` | 1.27.2 | PDF text extraction | Fast, accurate, handles complex PDFs |
| `pymupdf4llm` | NOT INSTALLED | LLM-optimized markdown output from PDFs | **Must be added** — produces structured markdown with headers, tables, footnotes preserved. Pure `fitz.page.get_text()` loses layout semantics. |
| `python-docx` | 1.2.0 | DOCX paragraph extraction | Stable, correct for v1 scope |
| `pdfplumber` | 0.11.9 | Table extraction from PDFs | Complementary to pymupdf — use specifically when the PDF contains tables that need structure |

**On pymupdf4llm:** It is not in the lock file and not in pyproject.toml — the existing code uses raw `fitz` (pymupdf). The PROJECT.md spec requires `pymupdf4llm`. It must be added: `uv add pymupdf4llm`. It is a thin wrapper that calls `pymupdf4llm.to_markdown(doc)` and returns markdown. It is maintained by the PyMuPDF team and tied to the same `pymupdf` package already installed.

**Why not pdfplumber as primary:** pdfplumber is character-position-based and excellent for extracting tables but does not produce LLM-friendly markdown. Use it as a secondary parser when a PDF is known to contain tables.

**Why not pypdf/PyPDF2:** Slower extraction, no markdown output, not LLM-optimized. pymupdf is faster and more accurate.

**Confidence: HIGH** for pymupdf + python-docx. MEDIUM for pymupdf4llm (needs version verification after adding).

---

### CLI & Output

| Technology | Version (resolved) | Purpose | Why |
|------------|-------------------|---------|-----|
| `typer[all]` | 0.24.1 | CLI framework | The `[all]` extra pulls in `rich` integration automatically. Best DX for async Python CLIs. |
| `rich` | (pulled by typer[all]) | Panels, spinners, progress bars | Required for the investigation progress UX. Use `rich.live.Live` for real-time sub-task progress. |

**Confidence: HIGH** — Typer + Rich is the standard choice for Python CLIs in 2025. Stable API.

---

### API & Report Viewer

| Technology | Version (resolved) | Purpose | Why |
|------------|-------------------|---------|-----|
| `fastapi` | 0.135.1 | REST API + static file serving | Serves the React viewer and report list endpoint |
| `uvicorn[standard]` | 0.41.0 | ASGI server | The `[standard]` extra includes uvloop (faster event loop) and websockets support |
| `jinja2` | 3.1.6 | Server-side HTML templating | For the Markdown-to-HTML rendering endpoint. FastAPI integrates via `Jinja2Templates`. |

**On the report viewer:** The spec says a "single-page React app served by FastAPI." For v1, use `fastapi.staticfiles.StaticFiles` to mount a pre-built React dist. Do not add a Node.js build step to the Python project — build the React app separately and commit the dist. A simpler alternative that avoids frontend build tooling entirely: serve Markdown as HTML using Jinja2 templates with a client-side marked.js CDN. This is likely sufficient for the "dark-mode, clickable sources" requirement.

**Confidence: HIGH** — FastAPI + Uvicorn is the clear standard. Jinja2 is the built-in templating choice.

---

### Telegram Bot

| Technology | Version (resolved) | Purpose | Why |
|------------|-------------------|---------|-----|
| `python-telegram-bot` | 22.6 | Telegram Bot API wrapper | Async-native (uses httpx under the hood from v20+), PTB's Application builder handles polling loop cleanly |

**Version gotcha:** The pyproject.toml pins `>=21.9` but the resolved version is 22.6. The API surface is compatible, but if you use `Bot(token=...)` directly for notifications (as the existing code does), ensure you call `async with Bot(token=...) as bot:` in 22.x — `Bot` is now a context manager that manages its session. Calling `Bot(token=...)` without a context manager will trigger a deprecation warning in 22.x and may break in 23.x.

**The existing telegram.py is incorrect** — it creates `Bot(token=...)` instances ad-hoc without using the context manager. This leaks HTTP sessions. Fix pattern:

```python
async with Bot(token=settings.telegram_bot_token) as bot:
    await bot.send_message(chat_id=..., text=...)
```

Or better: use the `Application` instance's bot for all outbound messages to share the session.

**Confidence: HIGH** — python-telegram-bot is the standard. Version note is from training data (HIGH confidence on 22.x context manager requirement based on PTB changelog knowledge through August 2025).

---

### Data Models & Config

| Technology | Version (resolved) | Purpose | Why |
|------------|-------------------|---------|-----|
| `pydantic` | 2.12.5 | Data validation, all agent I/O models | v2 required. No raw dicts crossing function boundaries. |
| `pydantic-settings` | 2.13.1 | Env var config with SHERLOCK_ prefix | `BaseSettings` with `env_prefix="SHERLOCK_"` is the correct pattern. |

**Pydantic v2 gotcha:** The existing models use `Field(default_factory=dict)` for `metadata: dict[str, str]`. This is valid but in v2 you should use `model_config = ConfigDict(...)` at the class level rather than the v1 `class Config`. The existing code doesn't have a `class Config` — it's already v2-clean.

**Confidence: HIGH** — Pydantic v2 + pydantic-settings is the standard stack for 2025 Python projects.

---

### Async & Testing

| Technology | Version (resolved) | Purpose | Why |
|------------|-------------------|---------|-----|
| `pytest` | >=8.3.0 | Test runner | Standard |
| `pytest-asyncio` | 1.3.0 | Async test support | `asyncio_mode = "auto"` in pyproject.toml means all async test functions run without explicit decorator |
| `mypy` | 1.19.1 | Static type checking | `strict = true` in pyproject.toml — all code must pass mypy strict |
| `ruff` | 0.15.5 | Linting + formatting | Replaces black + isort + flake8. Use `ruff check --fix` + `ruff format` |

**pytest-asyncio 1.3.0 note:** Version 1.x (post-0.24.x) changed how fixtures work with async. The `asyncio_mode = "auto"` config in pyproject.toml is correct and means you do NOT need `@pytest.mark.asyncio` on every async test. However, async fixtures must be declared with `@pytest_asyncio.fixture` (not just `@pytest.fixture`) in strict mode.

**Confidence: HIGH** — All dev tooling is standard and well-established.

---

## Missing Dependencies (Must Add)

| Library | Command | Why Needed |
|---------|---------|-----------|
| `duckduckgo-search` | `uv add duckduckgo-search` | Replace fragile HTML scraping of DDG with the proper Python library |
| `pymupdf4llm` | `uv add pymupdf4llm` | Spec requires it; produces LLM-optimized markdown from PDFs vs raw text extraction |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Web scraping | crawl4ai | playwright directly | Too low-level, no built-in LLM content extraction |
| Web scraping | crawl4ai | scrapy | Synchronous-first, not designed for single-URL async use |
| Web scraping | crawl4ai | newspaper3k | Abandoned (2022), no JS rendering |
| Search | duckduckgo-search | SerpAPI | Paid, requires API key, unnecessary for v1 |
| Search | duckduckgo-search | Google Custom Search | Paid API, setup friction |
| PDF | pymupdf4llm | pypdf/PyPDF2 | Slower, no markdown output, not LLM-optimized |
| PDF | pymupdf4llm | pdfplumber (primary) | No markdown output, character-position model is wrong abstraction for LLM ingestion |
| Telegram | python-telegram-bot | aiogram | Less community examples for investigator-bot patterns, aiogram is better for high-volume bots |
| LLM output | tool_use | JSON in system prompt | Fragile — requires string parsing, markdown fence stripping, error-prone. tool_use guarantees schema. |
| CLI | typer | click | Typer wraps click with type hints; no reason to use click directly |
| CLI | typer | argparse | No Rich integration, more boilerplate |

---

## Installation

```bash
# Install all dependencies (already in pyproject.toml)
uv sync

# Add missing dependencies not yet in pyproject.toml
uv add duckduckgo-search
uv add pymupdf4llm

# Install dev dependencies
uv sync --extra dev

# After first install, Crawl4AI requires Playwright browsers
uv run crawl4ai-setup
# OR
uv run playwright install chromium
```

**Crawl4AI setup is a required post-install step.** It downloads Playwright browser binaries. The existing pyproject.toml does not document this — it must be added to the README and any CI setup.

---

## Resolved Version Reference

From `uv.lock` (authoritative, as of 2026-03-15):

| Package | Resolved Version |
|---------|-----------------|
| anthropic | 0.84.0 |
| crawl4ai | 0.8.0 |
| fastapi | 0.135.1 |
| httpx | 0.28.1 |
| jinja2 | 3.1.6 |
| mypy | 1.19.1 |
| pdfplumber | 0.11.9 |
| pydantic | 2.12.5 |
| pydantic-settings | 2.13.1 |
| pymupdf | 1.27.2 |
| pytest-asyncio | 1.3.0 |
| python-docx | 1.2.0 |
| python-telegram-bot | 22.6 |
| ruff | 0.15.5 |
| typer | 0.24.1 |
| uvicorn | 0.41.0 |
| aiosqlite | 0.22.1 (installed but out-of-scope for v1) |
| beautifulsoup4 | 4.14.3 |
| aiohttp | 3.13.3 |
| aiofiles | 25.1.0 |

---

## Sources

- `uv.lock` — Authoritative resolved versions (read directly from repo)
- `pyproject.toml` — Declared dependency minimums (read directly from repo)
- `sherlock/tools/web.py` — Confirmed DDG HTML scraping issue
- `sherlock/tools/documents.py` — Confirmed pymupdf4llm not used
- `sherlock/tools/telegram.py` — Confirmed Bot context manager issue
- `sherlock/agents/conductor.py` — Confirmed raw JSON parsing (not tool_use)
- Anthropic Python SDK changelog (training knowledge, HIGH confidence through August 2025)
- python-telegram-bot changelog v22.x (training knowledge, HIGH confidence through August 2025)
- Crawl4AI documentation (training knowledge, MEDIUM confidence — verify 0.8.x API surface)
