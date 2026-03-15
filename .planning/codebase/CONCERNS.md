# Codebase Concerns

**Analysis Date:** 2026-03-15

## JSON Parsing Fragility

**LLM output parsing lacks error handling:**
- Issue: Three agent files (`conductor.py`, `researcher.py`, reporter implicitly) strip markdown fences and call `json.loads()` without try-catch. If the LLM returns malformed JSON or fails to wrap output in markdown fences, the entire investigation crashes.
- Files: `sherlock/agents/conductor.py` (lines 52-57), `sherlock/agents/researcher.py` (lines 55-59, 100-104)
- Impact: Any LLM hallucination or formatting deviation terminates the investigation with an unhandled `JSONDecodeError`
- Fix approach: Wrap JSON parsing in try-except blocks. Provide fallback behavior (retry with reprompt, or return empty findings). Add JSON schema validation via `pydantic` or `jsonschema` to catch malformed responses early.

**Evidence attachment is inefficient:**
- Issue: In `researcher.py` line 112, all gathered evidence is attached to every finding, creating duplication and memory bloat. For a research task with 30 search results and 5 findings, that's 150 evidence records instead of 30.
- Files: `sherlock/agents/researcher.py` (line 112)
- Impact: Memory usage scales poorly; reports become unnecessarily large; evidence de-duplication logic is missing
- Fix approach: Build a bidirectional mapping of findings to evidence IDs. Store evidence once, reference by ID in findings. Implement evidence relevance filtering.

## Silent Error Suppression

**Broad exception handlers mask real issues:**
- Issue: Multiple locations catch all exceptions and fail silently (`pass` or continue). Makes debugging production failures extremely difficult.
- Files:
  - `sherlock/tools/web.py` (lines 49-50, 81-82, 105-106, 114-115) - catch-all in search, scrape, and cache operations
  - `sherlock/agents/researcher.py` (lines 76-77) - continue on exception during evidence gathering
- Impact: Network failures, API rate limits, malformed HTML, and real bugs disappear with no trace. Investigation completes with partial data and no warning.
- Fix approach: Log specific exception types and messages. Raise for critical failures (missing API key, disk full). Differentiate transient failures (timeout, 429) from permanent ones (404, bad credentials).

## Missing Input Validation

**No query validation before investigation starts:**
- Issue: `plan_investigation()` and `/investigate` endpoint accept any string without sanitization or length limits. No protection against injection-like attacks or resource exhaustion.
- Files: `sherlock/agents/conductor.py` (line 41), `sherlock/api.py` (line 23), `sherlock/cli.py` (line 22)
- Impact: Users could pass extremely long queries or malicious content to LLM. No rate limiting prevents rapid-fire investigations.
- Fix approach: Add query length limits (e.g., 2000 chars), character validation, and per-user rate limiting (especially for API).

## Agent Task Assignment Too Simple

**Default fallback masks incomplete implementation:**
- Issue: In `conductor.py` lines 92-96, if a task agent is not "researcher", code defaults to researcher anyway. This silently accepts malformed plans from the LLM.
- Files: `sherlock/agents/conductor.py` (lines 88-96)
- Impact: Future agent types (analyst, reporter) can't be properly delegated. Bugs in conductor planning get hidden.
- Fix approach: Raise `ValueError` for unknown agent types. Implement `analyst` and `reporter` as proper async task handlers.

## Test Coverage Critical Gaps

**Only basic model tests exist:**
- Issue: Single test file (`test_models.py`) with 5 basic Pydantic model tests. Zero tests for:
  - Agent orchestration and error recovery
  - Web scraping failure modes
  - JSON parsing edge cases
  - Telegram notification delivery
  - API endpoint behavior
  - Cache correctness
  - Document parsing (PDF/DOCX)
- Files: `tests/test_models.py` (57 lines only)
- Risk: Integration bugs, regression failures, and production outages go undetected. Changes to core logic have no safety net.
- Priority: **High** - Agent logic and tool reliability need comprehensive async integration tests

## Async Footgun: Fire-and-Forget Tasks

**Background task has no error tracking:**
- Issue: In `telegram.py` line 163, `asyncio.create_task(_safe_investigate())` runs investigations in background. If the task fails, Telegram gets an error notification but the investigation data is lost—no persistence to database.
- Files: `sherlock/tools/telegram.py` (line 163)
- Impact: Users can't retrieve failed investigations. No audit trail. Repeated failures go undetected.
- Fix approach: Implement job queue with persistence (SQLite already exists but not used). Track investigation status in DB. Implement retry logic with backoff.

## Cache System Vulnerabilities

**File-based cache has no security model:**
- Issue: Cache files stored in `.sherlock_cache/` as plaintext JSON. Sensitive URLs, API responses, and content are readable on disk. No encryption, no access control.
- Files: `sherlock/tools/web.py` (lines 88-116)
- Impact: Competitor intelligence, private URLs, confidential PDFs could be exposed if system is compromised
- Fix approach: Implement optional encryption for cached content. Add TTL-based expiration. Sanitize sensitive data before caching.

**Cache key collision risk:**
- Issue: Cache key is SHA256(query text) truncated to 16 chars (line 92). Hash collision probability grows with scale.
- Files: `sherlock/tools/web.py` (line 92)
- Impact: Unrelated queries could retrieve wrong cached data, corrupting findings
- Fix approach: Use full hash length or add version prefix. Implement cache invalidation strategy.

## Model Validator Not Leveraging Pydantic

**String status fields instead of enums:**
- Issue: `Investigation.status`, `SubTask.status` are `str` (defaulting to "pending", accepting "running", "completed", "failed"). No enum protection—code accepts invalid values.
- Files: `sherlock/models.py` (lines 70, 83)
- Impact: Type safety lost; invalid states can be created; bug-prone state machine
- Fix approach: Create `InvestigationStatus` and `TaskStatus` enums. Update all status assignments to use enums.

## Search Engine API Not Implemented

**DuckDuckGo HTML scraping is not a production API:**
- Issue: `search_web()` scrapes DuckDuckGo's HTML page directly (lines 15-53). This violates ToS, breaks if DuckDuckGo changes HTML, and returns low-quality results.
- Files: `sherlock/tools/web.py` (lines 15-53)
- Impact: Web research is unreliable and unsustainable. Easy to detect and block.
- Fix approach: Integrate SerpAPI, Brave Search API, or Bing Search API. Add API key configuration. Handle rate limiting properly.

## Document Parsing Missing Error Handling

**PDF/DOCX parsing truncates without warning:**
- Issue: `parse_pdf()` caps content per page at 3000 chars (line 28), `parse_docx()` at 10000 total (line 52). If document is larger, evidence is silently truncated with no indication.
- Files: `sherlock/tools/documents.py` (lines 28, 52)
- Impact: Large documents lose information, findings may be incomplete without user awareness
- Fix approach: Implement chunking with overlap. Track truncation and warn in metadata. Return multiple Evidence entries per document.

## Hardcoded Model Selection

**No fallback if primary model fails:**
- Issue: Config specifies `claude-sonnet-4-20250514` as default, with `claude-opus-4-6` for deep analysis, but no fallback if API quota exhausted or model deprecated.
- Files: `sherlock/config.py` (lines 19-20)
- Impact: Model updates or API changes break investigations
- Fix approach: Add model fallback list. Detect model availability errors and retry with alternative.

## Performance Scaling Concerns

**No concurrency limits on evidence gathering:**
- Issue: `max_concurrent_requests` is set (config line 32) but not enforced in research task. Researcher loops through queries sequentially (researcher.py line 64) but web requests are not rate-limited.
- Files: `sherlock/config.py` (line 32), `sherlock/agents/researcher.py` (line 64)
- Impact: Script can trigger DDoS-like behavior on target sites. No backpressure on LLM token usage.
- Fix approach: Implement semaphore for concurrent web requests. Add delay between requests. Monitor token usage per investigation.

## Telegram Bot Authorization Too Broad

**Chat ID check uses string comparison:**
- Issue: Line 152 in `telegram.py` compares `chat_id` as string: `if chat_id != settings.telegram_chat_id`. If settings value is misconfigured, bot could be accessible to wrong users.
- Files: `sherlock/tools/telegram.py` (line 152)
- Impact: Unauthorized users could trigger investigations on the bot
- Fix approach: Use numeric chat ID internally. Implement allowlist for authorized users/chats. Add audit logging.

## Dependency Version Flexibility

**Loose dependency constraints:**
- Issue: `pyproject.toml` specifies minimum versions (e.g., `anthropic>=0.42.0`) but no upper bounds. Major version upgrades could introduce breaking changes.
- Files: `pyproject.toml` (lines 18-35)
- Impact: Install on new systems could pull incompatible library versions. Reproducibility issues.
- Fix approach: Pin major versions (e.g., `anthropic>=0.42.0,<1.0`). Regularly test with latest versions. Use `uv lock` for reproducible installs.

## Missing Database Implementation

**SQLite database configured but never used:**
- Issue: `db_path` configured in settings (config.py line 26), but investigation history is never persisted. Investigations are ephemeral—lost after process exit.
- Files: `sherlock/config.py` (line 26)
- Impact: No audit trail, no investigation history, can't resume failed tasks
- Fix approach: Implement DB schema and CRUD operations. Persist investigations after planning and completion. Add query/list endpoints.

## Reporting Format Not Fully Implemented

**Only Markdown reports work:**
- Issue: `report_format` setting (config.py line 36) claims to support "markdown, json, html" but only Markdown is implemented. JSON and HTML are unimplemented stubs.
- Files: `sherlock/config.py` (line 36), `sherlock/agents/reporter.py`
- Impact: Users selecting JSON or HTML get Markdown anyway, silently
- Fix approach: Implement JSON schema export (Evidence + Finding objects). Implement HTML template rendering. Update reporter to dispatch by format.

## Rate Limiting Missing

**No protection against abuse:**
- Issue: Both CLI and API allow unrestricted investigation launches. No rate limiting, no concurrent request limits, no token budget enforcement.
- Files: `sherlock/api.py` (line 23), `sherlock/cli.py` (line 22)
- Impact: Single user could exhaust Anthropic API quota with rapid requests. No protection against DDoS.
- Fix approach: Add request rate limiting (e.g., 5 investigations/hour per user). Implement token budget tracking. Add request queuing.

## Security: API Key Exposure Risk

**API key logged in error messages:**
- Issue: Anthropic client created with `api_key=settings.anthropic_api_key`. If exception occurs during API call, Anthropic SDK might log the key in traceback.
- Files: `sherlock/agents/conductor.py` (line 43), `sherlock/agents/researcher.py` (line 40), `sherlock/agents/reporter.py` (line 47)
- Impact: Secret keys could be exposed in logs or error reports
- Fix approach: Never pass raw keys to clients. Use environment-only configuration. Implement custom exception handling that strips sensitive data.

---

*Concerns audit: 2026-03-15*
