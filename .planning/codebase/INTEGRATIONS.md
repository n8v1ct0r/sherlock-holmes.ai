# External Integrations

**Analysis Date:** 2026-03-15

## APIs & External Services

**LLM Provider:**
- Anthropic Claude API - Core reasoning engine for all investigation agents
  - SDK/Client: `anthropic>=0.42.0`
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Models used:
    - `claude-sonnet-4-20250514` - Default for standard tasks
    - `claude-opus-4-6` - Deep analysis passes
  - Integration files: `sherlock/agents/conductor.py`, `sherlock/agents/researcher.py`, `sherlock/agents/reporter.py`

**Web Search:**
- DuckDuckGo HTML search (free fallback, no API key required)
  - Accessed via httpx with HTML scraping
  - Alternative: SerpAPI, Brave Search API (commented as production upgrade)
  - Integration file: `sherlock/tools/web.py` (function `search_web()`)
  - Endpoint: `https://html.duckduckgo.com/html/`
  - User-Agent: `Sherlock-Holmes-AI/0.1 (research agent)`

## Data Storage

**Databases:**
- SQLite (optional, configured but not actively used)
  - Client: `aiosqlite>=0.20.0`
  - Database path: `.sherlock_cache/investigations.db` (configurable via `SHERLOCK_CACHE_DIR`)
  - Purpose: Future investigation history storage
  - Status: Infrastructure in place, awaiting schema implementation

**File Storage:**
- Local filesystem only
  - Report output directory: `sherlock/outputs/` (configurable via `SHERLOCK_OUTPUT_DIR`)
  - Cache directory: `.sherlock_cache/` (configurable via `SHERLOCK_CACHE_DIR`)
  - Markdown reports: Named pattern `{YYYYMMDD_HHMMSS}_{slug}.md`
  - Cache format: JSON files with SHA256 hash keys

## Authentication & Identity

**Auth Provider:**
- Custom (API key-based)
  - Anthropic: Bearer token in header (handled by `anthropic` SDK)
  - Telegram: Bot token for bot initialization

## Monitoring & Observability

**Error Tracking:**
- None currently implemented
- Logging: Python `logging` module for warnings/errors
  - Telegram notifications include error callbacks: `notify_task_failed()`

**Logs:**
- Console output via Rich (CLI mode)
- Telegram messages (notifications mode)
- No persistent log file integration

## CI/CD & Deployment

**Hosting:**
- Not deployed; development/local execution only
- Can be deployed to any cloud platform supporting Python 3.12

**CI Pipeline:**
- None detected
- Dev tools configured: pytest, mypy, ruff

## Webhooks & Callbacks

**Incoming:**
- None implemented

**Outgoing:**
- Telegram notifications (optional)
  - Functions in `sherlock/tools/telegram.py`:
    - `notify_investigation_started()` - Sends task count
    - `notify_task_completed()` - Sends finding count
    - `notify_task_failed()` - Error notification
    - `notify_investigation_complete()` - Final report notification
    - `send_report_file()` - Direct file delivery
  - Triggered conditionally when `--notify` flag or bot mode is active

## Environment Configuration

**Required env vars:**
- `ANTHROPIC_API_KEY` - Anthropic Claude API key (no default)

**Secrets location:**
- `.env` file in project root (read by pydantic-settings)
- Template: `.env.example`
- Telegram credentials optional: `SHERLOCK_TELEGRAM_BOT_TOKEN`, `SHERLOCK_TELEGRAM_CHAT_ID`

## Request Caching

**Web Request Cache:**
- Mechanism: File-based, SHA256-hashed keys
- Storage: `.sherlock_cache/{hash}.json`
- Cached endpoints:
  - DuckDuckGo search queries
  - URL scrape results (5000 char limit per cached entry)
- Cache busting: Manual deletion of cache directory
- Implementation: `sherlock/tools/web.py` (_cache_key, _read_cache, _write_cache functions)

## Document Format Support

**Input Documents:**
- PDF files: via `pymupdf` (fitz) - `sherlock/tools/documents.py:parse_pdf()`
  - Output: Evidence chunks (max 3000 chars per page)
  - Metadata: File path, page number
- DOCX files: via `python-docx` - `sherlock/tools/documents.py:parse_docx()`
  - Output: Single Evidence object (max 10000 chars)
  - Metadata: File path only

**Report Output:**
- Primary: Markdown (human-readable)
- Format configurable: `SHERLOCK_REPORT_FORMAT` (markdown|json|html)
- Currently only markdown generation implemented
- Saved to: `sherlock/outputs/{timestamp}_{slug}.md`

## Web Scraping

**HTTP Client:**
- httpx with async support (AsyncClient)
- Timeout: Configurable via `SHERLOCK_REQUEST_TIMEOUT` (default 30s)
- User-Agent: `Sherlock-Holmes-AI/0.1 (research agent)`
- Headers: Standard research agent identification
- Follow redirects: Enabled for URL scraping

**HTML Parsing:**
- BeautifulSoup4 with html.parser
- Elements stripped: `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`
- Text extraction: separator="\n", max 5000 chars per URL
- CSS selectors used for DuckDuckGo: `.result`, `.result__a`, `.result__snippet`

## Telegram Integration

**Bot Framework:**
- `python-telegram-bot>=21.9`

**Inbound:**
- Bot application listens for messages
- Triggers investigation on message receipt
- Runs `sherlock telegram` command to start polling

**Outbound:**
- Sends notifications with Markdown parse mode
- Supports text messages and document (file) delivery
- Chat ID configuration: `SHERLOCK_TELEGRAM_CHAT_ID`
- Bot token: `SHERLOCK_TELEGRAM_BOT_TOKEN`

**Callback Functions:**
- `send_notification()` - Generic text message
- `send_report_file()` - Sends markdown report as document
- `notify_investigation_started()` - Initial task breakdown
- `notify_task_completed()` - Per-task completion
- `notify_task_failed()` - Error notification
- `notify_investigation_complete()` - Final summary with report file

## Rate Limiting & Concurrency

**Web Requests:**
- Max concurrent requests: `SHERLOCK_MAX_CONCURRENT_REQUESTS` (default 5)
- Per search: `max_web_results` capped at configured limit (default 10)
- Per-query scraping: Up to 3 search queries executed per task
- Timeout: `SHERLOCK_REQUEST_TIMEOUT` (default 30 seconds)

**LLM Calls:**
- No rate limiting implemented
- All agent calls are sequential per investigation
- Max tokens per response: `SHERLOCK_MAX_TOKENS` (default 4096)

## Data Flow Integration Points

1. **Query Input** → CLI/API receives investigation query
2. **Conductor** → Anthropic Claude plans sub-tasks (JSON response parsing)
3. **Researcher** → Multiple sub-tasks generate search queries → DuckDuckGo + URL scraping → Claude analyzes evidence
4. **Evidence Chain** → Each finding gets Evidence model with sources, confidence, metadata
5. **Reporter** → Claude synthesizes report from findings (structured Markdown output)
6. **Storage** → Report saved to `sherlock/outputs/`
7. **Telegram** (optional) → Notification sent with results file
8. **Cache** → All web requests cached for future runs

---

*Integration audit: 2026-03-15*
