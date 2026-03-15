# Domain Pitfalls

**Domain:** Autonomous AI research agent (Claude tool_use + Crawl4AI + DuckDuckGo + Telegram)
**Researched:** 2026-03-15
**Confidence:** MEDIUM — based on training knowledge (cutoff Aug 2025) of Crawl4AI, python-telegram-bot, duckduckgo-search, and Anthropic tool_use. No live web verification was available in this session; flag for validation before Phase 1 implementation.

---

## Critical Pitfalls

Mistakes that cause rewrites or force major architectural changes.

---

### Pitfall 1: Hallucinated Source URLs in LLM Output

**What goes wrong:** The conductor or reporter agent is asked to produce a citation list. The LLM generates plausible-looking URLs that were never actually fetched — URLs that 404, or reference real domains but with invented paths. The final report looks well-sourced but is fabricated.

**Why it happens:** LLMs are trained to be helpful and produce well-formed output. When structured output asks for a `source_url` field, the model fills it even when it has no grounded URL. This is especially likely when the reporter sees raw text extracted by the researcher but not the original URL metadata. The URL gets "reconstructed" by the model from memory.

**Consequences:** The entire trust model of Sherlock collapses. Reports cite invented sources. Users who follow citations find 404s or unrelated content. The core value proposition ("every claim cites a real source") is broken silently.

**Prevention:**
- Every `Finding` and `Source` Pydantic model must carry the URL it was retrieved from, set at scrape time — never inferred later.
- The reporter agent must only output citations from the `sources` list passed to it. It must not generate new URLs.
- Add a post-generation validation step: for every URL in the report, verify it exists in the `sources` list from the research run. Reject the report if a URL appears that wasn't in the list.
- Use tool_use (function calling) where the researcher tool returns `{url, content, title}` tuples. The reporter receives only what was grounded.

**Detection:** Run a citation audit after every generated report: extract all URLs from the Markdown, diff against `investigation.sources`. Any URL not in the sources list is hallucinated.

**Phase:** Address in Phase 1 (core pipeline). Embed the validation check before the report is written to disk.

---

### Pitfall 2: Structured Output Parsing Failure Under Variation

**What goes wrong:** The Claude tool_use call returns a valid JSON object, but the schema is subtly wrong — a field is missing, a string is returned where an int is expected, or a nested object is flattened. Pydantic validation raises `ValidationError` at runtime. If unhandled, the entire investigation crashes with no partial results saved.

**Why it happens:** Tool_use (function calling) significantly reduces schema drift compared to markdown parsing, but it doesn't eliminate it. Claude may omit optional fields, or interpret ambiguous instructions in the tool schema in unexpected ways. The problem compounds when prompts are long (evidence is large) and the model compresses/abbreviates its output.

**Consequences:** A 2-minute investigation crashes with a Pydantic error. No partial findings are persisted. The user sees a stack trace in Telegram or CLI. Trust erodes.

**Prevention:**
- Use `model_validate` with `strict=False` where fields are optional. Don't require the model to return every field.
- Design tool schemas with all fields optional where possible; validate presence of required fields manually after parsing.
- Wrap every `model_validate` in a try/except `ValidationError`. On failure: log the raw JSON response, return a `PartialFinding` or skip that sub-task, continue the investigation.
- Use `model_json_schema()` to generate the tool input schema from Pydantic models directly — keeps tool definition and model in sync.
- Keep tool schemas simple: flat over nested, fewer fields over more.

**Detection:** Log every raw LLM response before parsing. Any ValidationError in logs indicates schema drift. Set up a counter; if >10% of calls fail validation, the schema needs revision.

**Phase:** Address in Phase 1. Implement before adding complex agent logic — the error handling scaffolding must be in place from the start.

---

### Pitfall 3: Crawl4AI Playwright Browser Not Installed

**What goes wrong:** `crawl4ai` is installed via pip/uv, but `playwright install` was never run. On first use, Crawl4AI raises a `BrowserType.launch: Executable doesn't exist` error (or similar) that looks like a scraping failure, not a setup failure. The error message doesn't clearly indicate that Playwright browsers need a separate install step.

**Why it happens:** Playwright's browser binaries are not bundled with the Python package. They must be installed separately with `playwright install chromium`. This is a non-obvious post-install step that's easy to miss when setting up a fresh environment.

**Consequences:** Crawl4AI silently or loudly fails on every URL. All scraping returns empty or errors. The investigation produces reports with zero evidence.

**Prevention:**
- Add `playwright install chromium` to the project setup instructions and to a `Makefile` or `uv run` script.
- In `pyproject.toml`, add a post-install script or document as a required step.
- On startup, detect if Playwright browsers are installed: call `playwright.chromium.executable_path()` and check if the file exists. Fail fast with a clear error: "Run `playwright install chromium` first."

**Detection:** A `BrowserType.launch: Executable doesn't exist` or `playwright._impl._errors.Error` in scraping logs.

**Phase:** Address in Phase 1 (environment setup) and document in README before any other work.

---

### Pitfall 4: DuckDuckGo Rate Limiting and Silent Empty Results

**What goes wrong:** The `duckduckgo-search` library is not an official API — it scrapes DDG's HTML or uses their unofficial API endpoints. Under load, DDG returns rate-limit errors (`RatelimitException`), 202 responses, or empty result sets with no error raised. The researcher proceeds with zero search results, finds nothing to scrape, and the reporter generates a report citing no sources.

**Why it happens:** DDG aggressively rate-limits bots. The `duckduckgo-search` library exposes this via a `RatelimitException` in some versions, but in others it returns an empty list silently. The issue is especially pronounced when multiple sub-tasks fire search queries in rapid succession.

**Consequences:** The investigation completes without error but produces vacuous reports. The system appears to work but generates useless output. Harder to catch than a crash.

**Prevention:**
- Always check `len(results) == 0` after a DDG search and treat it as a soft failure, not success.
- Add jitter between search calls: `await asyncio.sleep(random.uniform(1.5, 3.5))` between each DDG query.
- Implement retry with backoff for `RatelimitException`: 3 retries with exponential backoff (2s, 4s, 8s).
- Make Brave Search the production default and DDG the development fallback, not the other way around.
- In the `Finding` model, track `search_results_count`. If 0, flag the sub-task as `SearchFailed` rather than completing it normally.

**Detection:** Log result count for every search call. Alert (Telegram or CLI warning) if a sub-task produced zero search results.

**Phase:** Address in Phase 1 (researcher agent). Robust empty-result handling is required before the pipeline is useful.

---

## Moderate Pitfalls

---

### Pitfall 5: Crawl4AI Memory Leak with Long-Running Browser Sessions

**What goes wrong:** Crawl4AI uses Playwright browsers under the hood. If the `AsyncWebCrawler` is not properly closed (via `async with` or explicit `.close()`), browser processes accumulate. In a long-running Telegram bot process, this leaks memory over hours until the process OOMs or becomes unresponsive.

**Why it happens:** Playwright launches a full Chromium process. Without explicit cleanup, each crawl spawns a new context that is never freed.

**Prevention:**
- Always use `async with AsyncWebCrawler(...) as crawler:` — never instantiate outside a context manager.
- Consider creating a single shared crawler instance for the process lifetime (initialized at startup, closed on shutdown) rather than one per investigation.
- Add a SIGTERM/SIGINT handler in the Telegram bot that calls `await crawler.close()` before exit.

**Detection:** Monitor the process's memory usage over time (`/proc/PID/status` on Linux). Increasing RSS over multiple investigations indicates a leak.

**Phase:** Address in Phase 2 (Telegram bot integration). The bot runs as a long-lived process where this matters most.

---

### Pitfall 6: Telegram Bot Webhook vs Polling Confusion

**What goes wrong:** The bot is started with `application.run_polling()` but a stale webhook URL is still registered with Telegram. Telegram sends all messages to the webhook (which 404s), and the polling loop receives nothing. The bot appears to start successfully but never receives any messages.

**Why it happens:** Telegram maintains webhook state server-side. If a webhook was ever set (e.g., during testing) and not explicitly deleted, it takes priority over polling. `run_polling()` does not automatically clear webhooks.

**Prevention:**
- At bot startup, always call `await application.bot.delete_webhook(drop_pending_updates=True)` before starting the polling loop.
- Alternatively, make this explicit in the startup script: `sherlock telegram --clear-webhook`.

**Detection:** Bot starts with no errors but `on_message` handler never fires. Check with: `https://api.telegram.org/bot<TOKEN>/getWebhookInfo` — if `url` is non-empty, there's an active webhook.

**Phase:** Address in Phase 2 (Telegram bot). Add the `delete_webhook` call unconditionally before `run_polling`.

---

### Pitfall 7: Async Blocking in Sync Contexts (FastAPI + asyncio)

**What goes wrong:** A synchronous file read, a `requests` call, or `time.sleep()` is called inside an `async def` route handler or agent method. This blocks the entire event loop, making the FastAPI server or Telegram bot unresponsive for the duration of the blocking call.

**Why it happens:** Python doesn't prevent calling sync code from async functions. It fails silently — no exception, just degraded performance. Common triggers: `open()` for reading report files, `time.sleep()` in retry logic, or forgetting to `await` an async call.

**Prevention:**
- Use `aiofiles` for all file I/O in async contexts.
- Replace `time.sleep()` with `await asyncio.sleep()` everywhere.
- Use `asyncio.get_event_loop().run_in_executor()` for any unavoidably synchronous CPU-bound code (e.g., pymupdf page parsing).
- Run `pylint` or `flake8-async` to catch blocking calls in async functions.

**Detection:** The FastAPI `/reports` endpoint hangs for seconds during investigation. Telegram bot stops responding while an investigation runs. Use `asyncio.get_event_loop().set_debug(True)` to log coroutines that block for >100ms.

**Phase:** Address throughout. Establish the pattern in Phase 1 and enforce consistently.

---

### Pitfall 8: LLM Context Window Overflow from Scraped Content

**What goes wrong:** The researcher agent scrapes 10 pages, each with 50KB of text. The conductor passes all raw content to the analyst or reporter in a single prompt. The total token count exceeds the model's context window (200K for claude-sonnet-4), causing an API error or — worse — the model silently drops content from the middle of the prompt (lost-in-the-middle problem).

**Why it happens:** Web pages contain far more text than needed. A single scrape of a news article or Wikipedia page can be 10K-50K tokens. 5-10 such pages in one prompt easily hits limits.

**Prevention:**
- Truncate scraped content per-page before passing to the LLM: extract first 3000 characters of main content + title + URL. Let Crawl4AI's `word_count_threshold` and `excluded_tags` handle boilerplate removal.
- Use the researcher agent to extract only the relevant passages (a summarization sub-call) before passing to the analyst.
- Track running token estimate (rough: `len(text) / 4`). If approaching 150K tokens, stop adding more content.
- Structure the analyst prompt to process one Finding at a time, not all at once.

**Detection:** API errors mentioning context window exceeded. Reports that seem to ignore half the gathered sources.

**Phase:** Address in Phase 1 (researcher agent). The content truncation strategy must be set before the pipeline is integrated end-to-end.

---

### Pitfall 9: Cache Poisoning from Failed Scrapes

**What goes wrong:** A URL is scraped but returns a Cloudflare challenge page, a login wall, or an empty body. This failure response is cached to disk. On subsequent runs (even after the real page is available), the cache returns the failed/empty result forever.

**Why it happens:** The cache key is the URL hash. The cache doesn't inspect whether the stored content is valid before returning it. A "scrape" that returns `<html><body>Please enable JavaScript</body></html>` looks like a successful scrape to the cache layer.

**Prevention:**
- Validate cached content before returning: check minimum word count (e.g., >100 words), absence of Cloudflare/CAPTCHA markers.
- Store a `is_valid` flag and `status_code` alongside the cached content. Return cache misses for invalid entries.
- Add a `--no-cache` CLI flag for debugging.
- Set cache TTL (e.g., 24 hours for news, 7 days for reference content) to prevent stale data.

**Detection:** Investigation consistently returns empty evidence for specific URLs. The cached file for that URL is small (<500 bytes) or contains CAPTCHA text.

**Phase:** Address in Phase 1 (cache module). Invalid-content detection must be part of the initial cache design.

---

## Minor Pitfalls

---

### Pitfall 10: Telegram Message Length Limit (4096 Characters)

**What goes wrong:** The reporter sends a full investigation summary to Telegram. If the summary exceeds 4096 characters (Telegram's hard limit per message), the API returns a `MessageTooLong` error. The bot crashes or silently fails to send the summary.

**Prevention:**
- Never send the full report via Telegram. Send a short summary (5-10 bullet points, <2000 chars) and direct the user to the FastAPI viewer or a file path.
- Implement a `truncate_for_telegram(text, max_chars=3800)` utility that hard-truncates with a "... [truncated, see full report]" suffix.

**Phase:** Address in Phase 2 (Telegram bot). Simple fix, but easy to forget.

---

### Pitfall 11: DuckDuckGo `SafeSearch` Filtering Research Results

**What goes wrong:** DDG's default SafeSearch filters may suppress legitimate research results (e.g., medical content, security research, drug references) that Sherlock needs to investigate. The researcher gets back sanitized results and misses key sources.

**Prevention:**
- Set `safesearch="off"` in `DDGS().text()` calls.
- Document this decision; it's intentional for a research agent.

**Phase:** Address in Phase 1. One-line fix but important for result quality.

---

### Pitfall 12: Pydantic v2 `.dict()` vs `.model_dump()` Confusion

**What goes wrong:** Code written with Pydantic v1 patterns uses `.dict()` to serialize models. In Pydantic v2, `.dict()` is deprecated (still works but raises a warning). More critically, some v2 behaviors differ: `model_validate` vs `parse_obj`, `model_json_schema` vs `schema()`. Mixed usage causes deprecation noise and occasional subtle bugs.

**Prevention:**
- Use Pydantic v2 APIs exclusively: `.model_dump()`, `.model_validate()`, `.model_json_schema()`.
- Add a `ruff` rule or grep CI check to flag `.dict()` usage: `grep -r "\.dict()" sherlock/` fails the build if non-zero.

**Phase:** Address in Phase 1 (models.py). Establish the pattern before writing any agent code.

---

### Pitfall 13: pymupdf4llm Returning Empty String for Scanned PDFs

**What goes wrong:** A PDF is uploaded for parsing. It's a scanned document (image-only PDF, no text layer). `pymupdf4llm.to_markdown()` returns an empty string or near-empty Markdown. The document parser reports success, but no content was extracted.

**Prevention:**
- Check word count of the extracted text after parsing. If `len(text.split()) < 20`, flag the document as `ParseFailed(reason="likely_scanned_pdf")`.
- Log a clear message: "PDF appears to be image-only (scanned). OCR not supported in v1."
- Do not block investigation on a failed document parse — skip and continue.

**Phase:** Address in Phase 3 (document parsing). Out of scope for core pipeline but must not crash.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Phase 1: Core pipeline | Hallucinated URLs in reporter output | Validate all report URLs against `investigation.sources` before writing to disk |
| Phase 1: Core pipeline | DDG empty results treated as success | Explicit zero-result detection + `SearchFailed` sub-task status |
| Phase 1: Cache module | Invalid scrape responses cached permanently | Validate content quality before writing to cache; set TTL |
| Phase 1: Pydantic models | v1 `.dict()` patterns mixed with v2 | Use v2 APIs only from the first commit |
| Phase 1: Structured output | ValidationError crashes investigation | Wrap every `model_validate` in try/except; continue on failure |
| Phase 1: Content length | Raw scraped text overflows LLM context | Truncate to 3000 chars per source before analyst pass |
| Phase 2: Telegram bot | Stale webhook blocks polling | Call `delete_webhook()` unconditionally at bot startup |
| Phase 2: Telegram bot | Message >4096 chars crashes send | Truncate summaries; never send full reports via Telegram |
| Phase 2: Long-lived process | Crawl4AI browser memory leak | Use `async with` context manager; one shared crawler instance |
| Phase 3: Document parsing | Scanned PDFs return empty content | Detect empty output; log clearly; skip gracefully |
| All phases | Blocking I/O in async functions | Enforce `aiofiles`, `asyncio.sleep`, run_in_executor pattern |
| Setup | Playwright browsers not installed | Fail-fast check at startup; document `playwright install chromium` |

---

## Sources

- Training knowledge (cutoff Aug 2025) on: `duckduckgo-search` library behavior and `RatelimitException`, Anthropic Claude tool_use structured output behavior, `python-telegram-bot` v20+ webhook/polling interaction, Crawl4AI Playwright lifecycle management, Pydantic v2 migration patterns, asyncio blocking anti-patterns.
- Confidence: MEDIUM. All pitfalls are grounded in known library behaviors as of Aug 2025. Verify Crawl4AI-specific behaviors against https://docs.crawl4ai.com before Phase 1 implementation — the library evolves rapidly.
- No live web verification was available during this research session.
