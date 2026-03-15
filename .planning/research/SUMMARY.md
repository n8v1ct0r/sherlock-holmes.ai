# Project Research Summary

**Project:** Sherlock Holmes AI
**Domain:** Autonomous AI research and investigation agent (CLI + Telegram bot + FastAPI)
**Researched:** 2026-03-15
**Confidence:** MEDIUM-HIGH

## Executive Summary

Sherlock Holmes AI is an autonomous research agent in a well-documented domain. Competitors (GPT Researcher, Perplexity, Tavily) have established the expected architecture: decompose a query into sub-tasks, gather evidence from the web, synthesize findings with inline citations, and produce a structured report. The recommended approach is the conductor-orchestrator pattern already reflected in the existing codebase — a Conductor agent breaks the query into 2-5 SubTasks, a Researcher agent executes each (search + scrape + extract), and a Reporter agent synthesizes findings into a cited Markdown report. The key constraint that differentiates Sherlock from competitors is strict evidence integrity: every claim in a report must trace to a URL that was actually fetched during the investigation. This constraint shapes every architectural decision.

The existing codebase has the right structure but three significant implementation bugs that must be fixed before anything else: raw JSON parsing from LLM text (replace with tool_use function calling), all evidence attached to every finding (replace with index-based citation mapping), and a fragile DDG HTML scraper (replace with the `duckduckgo-search` PyPI library). Two dependencies are also missing from pyproject.toml: `duckduckgo-search` and `pymupdf4llm`. These are not optional — the existing web.py and documents.py are broken without them. Additionally, Crawl4AI requires a post-install `playwright install chromium` step that is undocumented; any developer who clones the repo will hit a cryptic failure without it.

The primary risks are trust-breaking: hallucinated source URLs in LLM output and silent failures that produce vacuous reports without any error signal. Both can be prevented with upfront validation — a post-generation URL audit and explicit zero-result detection on every search call. Build the evidence integrity constraints (no Finding without Evidence, source_url mandatory for web-sourced evidence, LLM cannot introduce new URLs in reporter) from the start, not as a retrofit. The sequential execution path is correct for v1; parallelism via `asyncio.gather` is a v2 concern once the sequential path is solid and tested.

---

## Key Findings

### Recommended Stack

The stack in pyproject.toml is largely correct. The core LLM layer (Anthropic SDK 0.84.0, claude-sonnet-4-20250514 for agent loops, claude-opus-4-6 for deep synthesis) is the right choice and the only permitted option. Crawl4AI 0.8.0 is the correct scraper — JS-aware, LLM-optimized markdown output — but the 0.8.x API changed from earlier versions; use `BrowserConfig` + `CrawlerRunConfig` explicitly, not the old `verbose=True` pattern. FastAPI + Uvicorn + Pydantic v2 + pydantic-settings is the correct supporting layer. Typer + Rich handles CLI. python-telegram-bot 22.6 handles the bot, but the `Bot` instance must be used as an async context manager in v22+ (the existing telegram.py leaks HTTP sessions by not doing this).

**Core technologies:**
- `anthropic` 0.84.0: Claude API client — only permitted LLM provider; use tool_use for all structured output
- `crawl4ai` 0.8.0: JS-aware web scraping — Playwright-backed, outputs LLM-ready markdown; requires `playwright install chromium` post-install
- `duckduckgo-search` (NOT YET INSTALLED): Search — replace fragile HTML scraping in web.py; add with `uv add duckduckgo-search`
- `pymupdf4llm` (NOT YET INSTALLED): PDF extraction — LLM-optimized markdown output; add with `uv add pymupdf4llm`
- `fastapi` 0.135.1 + `uvicorn` 0.41.0: API and report viewer
- `pydantic` 2.12.5 + `pydantic-settings` 2.13.1: All data models and config; use v2 APIs exclusively (`.model_dump()`, not `.dict()`)
- `python-telegram-bot` 22.6: Telegram bot; always use `async with Bot(...) as bot:` context manager

### Expected Features

Research confirms the current PROJECT.md scope is well-calibrated. All table-stakes features are present in the plan. The most important differentiators for v1 are evidence chain transparency and the Telegram-native investigation flow, both of which are already planned.

**Must have (table stakes):**
- Natural language query input with query decomposition into 2-5 sub-tasks
- Multi-source web search with real-time scraping (not a static index)
- Inline source citations in every report — every claim traces to a fetched URL
- Progress feedback (Rich CLI spinners, Telegram per-subtask updates)
- Graceful failure with explicit failure audit section in reports
- Source deduplication before report generation
- Configurable research depth (`--depth quick|standard|deep`)

**Should have (competitive differentiators):**
- Evidence chain transparency — show which evidence items support each claim (by index mapping)
- Failure audit log in the report — "these sources were tried but blocked/unreachable"
- Conflict detection across sources — flag when Source A contradicts Source B (adds genuine analytical value)
- Confidence scoring per finding (HIGH/MEDIUM/LOW based on corroboration count)
- Domain-scoped investigation (OSINT: only search .gov/.edu or specific communities)

**Defer (v2+):**
- Parallel sub-task execution via `asyncio.gather` — sequential first, concurrent after tests pass
- Investigation memory / SQLite history — file-based reports are sufficient for v1
- Iterative follow-up questions — requires session context
- Named entity extraction — high complexity, niche value for v1
- Export to PDF format
- Confidence-based source ranking (peer-reviewed > gov > blog)

### Architecture Approach

The conductor-orchestrator pattern with the Investigation object as the single source of truth flowing through the pipeline is the right design. Build strictly bottom-up: models.py and config.py first (they are the contract for everything else), then tools (web.py, documents.py, telegram.py), then agents (researcher, reporter, conductor in that order — conductor calls researcher, so researcher must exist first), then interfaces last (cli.py, api.py, telegram bot handler). No circular imports: models and config import nothing from agents or tools.

**Major components:**
1. `models.py` — Pydantic models: Investigation, SubTask, Finding, Evidence; use InvestigationStatus enum (not strings); source_url mandatory for web-sourced evidence
2. `tools/web.py` — search_web() + scrape_url() with cache-aside; replace DDG HTML scraping with `duckduckgo-search` library; use full SHA256 cache keys (not truncated 16-char)
3. `agents/researcher.py` — per-SubTask: generate queries, gather Evidence, map evidence to findings by index (not all evidence on every finding)
4. `agents/reporter.py` — synthesize findings into cited Markdown; post-generation URL audit (reject any URL not in investigation.sources)
5. `agents/conductor.py` — plan investigation, execute sequential task loop, aggregate findings
6. `cli.py` + `api.py` + `tools/telegram.py` (bot handler) — thin interface wrappers, no business logic

### Critical Pitfalls

1. **Hallucinated source URLs in reporter output** — LLM invents plausible URLs it never fetched. Prevention: Reporter receives only the sources list from the research run; add post-generation validation step that diffs report URLs against investigation.sources; reject any URL not in the list.

2. **Silent empty results from DuckDuckGo treated as success** — DDG rate-limits aggressively and returns empty lists silently. Prevention: Explicitly check `len(results) == 0` after every search call; mark sub-task as `SearchFailed`; add jitter between queries (`asyncio.sleep(random.uniform(1.5, 3.5))`); implement retry with exponential backoff for `RatelimitException`.

3. **LLM structured output (tool_use) validation failures crashing investigations** — Even with function calling, schema drift occurs. Prevention: Wrap every `model_validate` call in try/except `ValidationError`; log raw JSON response on failure; skip sub-task and continue rather than crashing the full investigation.

4. **Cache poisoning from invalid scrapes** — Cloudflare challenge pages and login walls get cached as successful scrapes. Prevention: Validate cached content before returning (minimum word count, absence of CAPTCHA markers); store `is_valid` flag alongside cached content; set TTL.

5. **Crawl4AI Playwright browsers not installed** — Cryptic failure that looks like a scraping error. Prevention: Add startup check for Playwright executable; fail fast with clear message; document `playwright install chromium` as required post-install step in README.

---

## Implications for Roadmap

Based on the architecture's layer dependencies and the critical pitfalls requiring early remediation, the recommended phase structure is:

### Phase 1: Foundation — Models, Config, and Core Fixes

**Rationale:** Three existing bugs must be fixed before any feature work builds on top of broken foundations: DDG HTML scraping, raw JSON parsing from LLM text, and all-evidence-on-every-finding. Additionally, two missing dependencies must be added. Data models are the contract for the entire system — they must be solid before tools or agents are written.

**Delivers:** Correct Pydantic models with InvestigationStatus enum and evidence integrity validators; missing dependencies added (duckduckgo-search, pymupdf4llm); Playwright startup check documented; config.py with pydantic-settings; all Pydantic v2 APIs enforced (.model_dump() not .dict()).

**Addresses:** Evidence integrity constraints (no Finding without Evidence, mandatory source_url for web evidence), Pydantic v2 migration, status string-to-enum conversion.

**Avoids:** Pitfall 2 (structured output validation failures), Pitfall 12 (Pydantic v1/v2 mixing), Pitfall 3 (Playwright not installed — document now), Anti-Pattern 4 (status strings).

### Phase 2: Tool Layer — Web Search, Scraping, and Cache

**Rationale:** Agents cannot be built or tested without working tools. The tool layer has two broken implementations (web.py DDG scraping, telegram.py Bot session leaks) and one missing feature (cache content validation). Fix before building agents.

**Delivers:** Corrected web.py using `duckduckgo-search` library; zero-result detection and retry with backoff for DDG; full SHA256 cache keys; cache content validation (word count, CAPTCHA detection, TTL); `aiofiles` for all file I/O; per-page content truncation to 3000 chars before LLM ingestion.

**Uses:** `duckduckgo-search`, `crawl4ai` 0.8.x (BrowserConfig + CrawlerRunConfig), `httpx`, `beautifulsoup4`, `aiofiles`.

**Avoids:** Pitfall 4 (DDG rate limiting + empty results), Pitfall 9 (cache poisoning), Pitfall 7 (blocking I/O in async), Pitfall 8 (LLM context window overflow), Anti-Pattern 5 (truncated SHA256 cache keys).

### Phase 3: Agent Pipeline — Researcher, Reporter, Conductor

**Rationale:** Agents are built in dependency order: researcher first (called by conductor), reporter second (called by conductor), conductor last. All agents must use tool_use (function calling) for structured output — not raw JSON parsing. Evidence-index mapping must replace all-evidence-on-every-finding.

**Delivers:** `researcher.py` using tool_use for Finding extraction with evidence index mapping; `reporter.py` with post-generation URL audit rejecting hallucinated URLs; `conductor.py` with sequential SubTask execution loop; end-to-end pipeline that produces a verifiable cited report from a natural language query.

**Addresses:** Table-stakes features (query decomposition, web search, inline citations, progress feedback, failure audit section in reports), configurable research depth.

**Avoids:** Pitfall 1 (hallucinated source URLs), Pitfall 2 (validation failures crashing investigations), Pitfall 3 (structured output schema drift), Anti-Pattern 1 (markdown parsing of LLM JSON), Anti-Pattern 2 (all evidence on every finding).

### Phase 4: Interfaces — CLI, Telegram Bot, and FastAPI Viewer

**Rationale:** Interfaces are thin wrappers that can only be built after the agent pipeline works end-to-end. Build CLI first (simplest integration), then Telegram bot (long-lived process, more pitfalls), then FastAPI viewer last.

**Delivers:** `cli.py` Typer commands with Rich progress display; `telegram.py` bot handler with `delete_webhook()` on startup, `async with Bot(...)` context manager for notifications, Telegram message truncation (<3800 chars); `api.py` FastAPI endpoints serving report list and Markdown-to-HTML via Jinja2; report viewer (Jinja2 + marked.js, no Node.js build step required).

**Uses:** `typer[all]`, `rich`, `python-telegram-bot` 22.6, `fastapi`, `jinja2`.

**Avoids:** Pitfall 5 (Crawl4AI browser memory leak — shared crawler instance in long-lived bot process), Pitfall 6 (stale webhook blocking polling), Pitfall 10 (Telegram 4096-char limit).

### Phase 5: Document Ingestion

**Rationale:** Document parsing (PDF/DOCX) is independent of the web research pipeline and can be added once the core pipeline is solid. It feeds into the same evidence synthesis path as web scraping.

**Delivers:** `documents.py` using `pymupdf4llm.to_markdown()` for PDF extraction; word count check to detect scanned/image-only PDFs with clear error message; `python-docx` for DOCX paragraph extraction; document Evidence objects flowing into the same researcher → reporter pipeline.

**Avoids:** Pitfall 13 (scanned PDFs returning empty content).

### Phase 6: Differentiators — Conflict Detection and Confidence Scoring

**Rationale:** These features require a solid evidence model with multi-source findings. They can only be added once the core pipeline is tested and producing high-quality findings consistently.

**Delivers:** Conflict detection (flag when sources contradict each other); confidence scoring per finding (HIGH requires >= 2 corroborating sources from different domains); source type classification (news / academic / blog / official).

**Addresses:** Key competitive differentiators from FEATURES.md (conflict detection, confidence scoring, evidence chain transparency).

### Phase Ordering Rationale

- Phases 1-2 fix existing bugs before adding any new functionality — this is non-negotiable; building agents on top of broken tools creates compounding debt.
- Phase 3 follows the architectural layer dependency: tools must exist before agents; researcher must exist before conductor.
- Phase 4 interfaces are last because they are untestable without a working pipeline, and the Telegram bot introduces long-lived process concerns (memory leaks, webhook state) that are easier to address once the core is stable.
- Phase 5 document ingestion is isolated from the web pipeline and can be added without disrupting the core path.
- Phase 6 differentiators require a mature evidence model — adding them before Phase 3 is complete would require rework.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Crawl4AI):** Crawl4AI 0.8.x API surface details (specifically `CrawlerRunConfig` parameter names and `word_count_threshold` behavior) should be verified against the installed package docs before implementation — the library evolves rapidly and training knowledge has a cutoff of August 2025.
- **Phase 4 (Telegram bot):** `python-telegram-bot` 22.x async context manager patterns for `Bot` and `Application` should be verified against current PTB docs before implementation.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Models + Config):** Pydantic v2 + pydantic-settings is a standard, well-documented pattern. No additional research needed.
- **Phase 3 (Anthropic tool_use):** The tool_use / function calling pattern is well-documented in the Anthropic Python SDK. The pattern is confirmed by the SDK changelog (HIGH confidence).
- **Phase 5 (Document parsing):** pymupdf + pymupdf4llm + python-docx are stable, well-documented libraries with clear APIs.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Lock file provides authoritative resolved versions; two missing dependencies identified by code audit; Crawl4AI 0.8.x API details are MEDIUM (verify against installed package) |
| Features | MEDIUM | Based on training knowledge of GPT Researcher, Perplexity, Tavily through August 2025; web search unavailable during research session; competitive landscape may have shifted |
| Architecture | HIGH | Based on direct codebase analysis; architectural patterns (tool_use, evidence-index mapping, bottom-up build order) are well-established; specific bugs confirmed by code audit |
| Pitfalls | MEDIUM | All pitfalls are grounded in known library behaviors (DDG rate limiting, Crawl4AI Playwright lifecycle, PTB webhook state, Pydantic v2 migration); no live verification was available |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Crawl4AI 0.8.x API surface:** `CrawlerRunConfig` exact parameter names and content extraction config options should be validated against `uv run python -c "import crawl4ai; help(crawl4ai.CrawlerRunConfig)"` before implementing web.py. Do not rely solely on pre-0.8 documentation.
- **DDG rate limit behavior in duckduckgo-search 7.x:** The exact exception type for rate limits (`RatelimitException` vs `DuckDuckGoSearchException`) should be verified by checking the library's source after installing. The retry logic in Phase 2 depends on catching the right exception.
- **Brave Search API as production default:** PITFALLS.md recommends making Brave Search the production default and DDG the development fallback. This requires a Brave Search API key (free tier: 2,000 req/month). Validate whether this is acceptable before planning Phase 2 — it changes the search tool architecture.
- **Report viewer approach:** STACK.md recommends Jinja2 + marked.js CDN instead of a React SPA to avoid a Node.js build step. Validate this is acceptable for the "dark-mode, clickable sources" requirement before Phase 4 planning.

---

## Sources

### Primary (HIGH confidence)
- `uv.lock` — authoritative resolved dependency versions
- `pyproject.toml` — declared dependency constraints and tool configuration
- `sherlock/agents/conductor.py`, `researcher.py`, `reporter.py` — confirmed architectural issues (raw JSON parsing, all-evidence-on-every-finding, status strings)
- `sherlock/tools/web.py` — confirmed DDG HTML scraping bug
- `sherlock/tools/telegram.py` — confirmed Bot context manager issue
- `sherlock/models.py`, `sherlock/config.py` — data model audit
- `CLAUDE.md` — architectural constraints (evidence policy, async-by-default, Pydantic)
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONCERNS.md` — prior codebase analysis

### Secondary (MEDIUM confidence)
- Training knowledge of Anthropic Python SDK tool_use pattern (through August 2025)
- Training knowledge of `python-telegram-bot` v22.x context manager requirement (through August 2025)
- Training knowledge of `duckduckgo-search` rate limiting and `RatelimitException` (through August 2025)
- Training knowledge of Crawl4AI 0.8.x `BrowserConfig` / `CrawlerRunConfig` API (through August 2025)
- Training knowledge of GPT Researcher, Perplexity, Tavily feature sets (through August 2025)

### Tertiary (LOW-MEDIUM confidence)
- Competitive landscape (Perplexity, GPT Researcher, AutoGPT, You.com) — features may have evolved since August 2025 cutoff; validate before finalizing feature priorities

---
*Research completed: 2026-03-15*
*Ready for roadmap: yes*
