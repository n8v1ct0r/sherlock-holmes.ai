# Requirements: Sherlock Holmes AI

**Defined:** 2026-03-15
**Core Value:** Every claim in every report must cite a real source. Zero hallucinated evidence.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Models & Config

- [ ] **MOD-01**: All data boundaries use Pydantic v2 models (Investigation, SubTask, Finding, Source, InvestigationPlan)
- [ ] **MOD-02**: InvestigationType enum classifies queries (osint, document_analysis, competitive_intel, legal_regulatory, general_research)
- [ ] **MOD-03**: InvestigationStatus enum tracks lifecycle (pending, planning, researching, reporting, completed, failed)
- [ ] **MOD-04**: Source model requires mandatory URL for web-sourced evidence
- [ ] **MOD-05**: Finding model links claims to specific sources by index (not all evidence on every finding)
- [ ] **CFG-01**: Settings loaded from env vars with SHERLOCK_ prefix via pydantic-settings
- [ ] **CFG-02**: Configurable research depth (quick/standard/deep) controlling source count per sub-task

### Web Search & Scraping

- [ ] **WEB-01**: DuckDuckGo search via duckduckgo-search library (default, no API key)
- [ ] **WEB-02**: Brave Search API integration (optional, configurable via env var)
- [ ] **WEB-03**: Crawl4AI async web scraping with 15-second timeout
- [ ] **WEB-04**: Graceful scrape failure (return None, log warning, continue investigation)
- [ ] **WEB-05**: Content truncation to max_scrape_chars before LLM ingestion
- [ ] **WEB-06**: Disk-based cache for all scrapes (SHA256 URL hash in .sherlock_cache/)
- [ ] **WEB-07**: Cache content validation (minimum word count, CAPTCHA detection)
- [ ] **WEB-08**: Source deduplication by URL before report generation
- [ ] **WEB-09**: Zero-result detection with retry and exponential backoff for rate limits

### Agents

- [ ] **AGT-01**: Conductor decomposes query into 2-5 sub-tasks with specific search queries via tool_use
- [ ] **AGT-02**: Researcher executes sub-tasks: search → scrape → extract findings via tool_use
- [ ] **AGT-03**: Reporter synthesizes findings into sourced Markdown with inline citations via tool_use
- [ ] **AGT-04**: Post-report URL audit rejects any URL not in investigation.sources
- [ ] **AGT-05**: All LLM calls use Anthropic tool_use (function calling) for structured output
- [ ] **AGT-06**: Every model_validate wrapped in try/except; skip sub-task on failure, never crash
- [ ] **AGT-07**: Report includes failure audit section listing unreachable/blocked sources

### CLI

- [ ] **CLI-01**: `sherlock investigate "query"` produces timestamped .md report in outputs/
- [ ] **CLI-02**: Rich progress display: investigation plan table, per-subtask spinners
- [ ] **CLI-03**: `sherlock reports` lists saved investigation reports
- [ ] **CLI-04**: `sherlock serve` starts FastAPI report viewer
- [ ] **CLI-05**: `sherlock telegram` starts Telegram bot listener
- [ ] **CLI-06**: `--notify` flag sends Telegram notification on completion
- [ ] **CLI-07**: `--depth quick|standard|deep` controls research thoroughness
- [ ] **CLI-08**: `-v/--verbose` flag for detailed output

### Telegram Bot

- [ ] **TG-01**: Incoming message triggers investigation (validates chat_id)
- [ ] **TG-02**: Acknowledge receipt immediately with "investigating..." message
- [ ] **TG-03**: Share investigation plan (sub-task breakdown) in chat
- [ ] **TG-04**: Progress updates per sub-task completion
- [ ] **TG-05**: Final delivery: short summary in chat + link to full report in viewer
- [ ] **TG-06**: Bot uses async context manager for Bot instance (no session leaks)
- [ ] **TG-07**: Messages truncated to <3800 chars (Telegram 4096 limit with buffer)
- [ ] **TG-08**: delete_webhook() on startup before run_polling()

### Report Viewer

- [ ] **VIEW-01**: GET / lists all investigation reports
- [ ] **VIEW-02**: GET /report/{filename} renders Markdown as HTML
- [ ] **VIEW-03**: Dark-mode CSS (inline, no build step)
- [ ] **VIEW-04**: Clickable source links in rendered reports
- [ ] **VIEW-05**: Jinja2 server-side rendering (no React/Node.js build step)

### Document Ingestion

- [ ] **DOC-01**: PDF parsing via pymupdf4llm producing markdown output
- [ ] **DOC-02**: DOCX parsing via python-docx extracting paragraph text
- [ ] **DOC-03**: Scanned/image-only PDF detection with clear error message
- [ ] **DOC-04**: Document evidence flows into same researcher → reporter pipeline

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Analysis

- **ANLYS-01**: Conflict detection — flag when sources contradict each other
- **ANLYS-02**: Confidence scoring per finding (HIGH/MEDIUM/LOW based on corroboration)
- **ANLYS-03**: Source type classification (news / academic / blog / official)
- **ANLYS-04**: Named entity extraction (companies, people, locations)

### Performance

- **PERF-01**: Parallel sub-task execution via asyncio.gather
- **PERF-02**: Concurrent web scraping within sub-tasks

### Persistence

- **PERS-01**: SQLite investigation history via aiosqlite
- **PERS-02**: Investigation memory — retrieve and build on prior findings

### UX

- **UX-01**: Iterative follow-up questions scoped to prior report
- **UX-02**: Domain-scoped investigation (e.g., only .gov/.edu sources)
- **UX-03**: Export to JSON and PDF formats

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-LLM support (OpenAI, local models) | Anthropic-only is a constraint; consistency > flexibility |
| Authentication on report viewer | Local-only access for v1; no public exposure |
| Docker/deployment packaging | Not needed until core loop works |
| PyPI publishing | Not v1 goal |
| Real-time streaming responses | Adds complexity without proportional value for v1 |
| Social/sharing features | Out of scope for a research tool |
| Recursive agent loops | Hard-capped at max_sub_tasks; bounded execution |
| Multi-user Telegram support | Single chat_id auth for v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MOD-01 | Phase 1 | Pending |
| MOD-02 | Phase 1 | Pending |
| MOD-03 | Phase 1 | Pending |
| MOD-04 | Phase 1 | Pending |
| MOD-05 | Phase 1 | Pending |
| CFG-01 | Phase 1 | Pending |
| CFG-02 | Phase 1 | Pending |
| WEB-01 | Phase 2 | Pending |
| WEB-02 | Phase 2 | Pending |
| WEB-03 | Phase 2 | Pending |
| WEB-04 | Phase 2 | Pending |
| WEB-05 | Phase 2 | Pending |
| WEB-06 | Phase 2 | Pending |
| WEB-07 | Phase 2 | Pending |
| WEB-08 | Phase 2 | Pending |
| WEB-09 | Phase 2 | Pending |
| AGT-01 | Phase 3 | Pending |
| AGT-02 | Phase 3 | Pending |
| AGT-03 | Phase 3 | Pending |
| AGT-04 | Phase 3 | Pending |
| AGT-05 | Phase 3 | Pending |
| AGT-06 | Phase 3 | Pending |
| AGT-07 | Phase 3 | Pending |
| CLI-01 | Phase 4 | Pending |
| CLI-02 | Phase 4 | Pending |
| CLI-03 | Phase 4 | Pending |
| CLI-04 | Phase 4 | Pending |
| CLI-05 | Phase 4 | Pending |
| CLI-06 | Phase 4 | Pending |
| CLI-07 | Phase 4 | Pending |
| CLI-08 | Phase 4 | Pending |
| TG-01 | Phase 4 | Pending |
| TG-02 | Phase 4 | Pending |
| TG-03 | Phase 4 | Pending |
| TG-04 | Phase 4 | Pending |
| TG-05 | Phase 4 | Pending |
| TG-06 | Phase 4 | Pending |
| TG-07 | Phase 4 | Pending |
| TG-08 | Phase 4 | Pending |
| VIEW-01 | Phase 4 | Pending |
| VIEW-02 | Phase 4 | Pending |
| VIEW-03 | Phase 4 | Pending |
| VIEW-04 | Phase 4 | Pending |
| VIEW-05 | Phase 4 | Pending |
| DOC-01 | Phase 5 | Pending |
| DOC-02 | Phase 5 | Pending |
| DOC-03 | Phase 5 | Pending |
| DOC-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 42 total
- Mapped to phases: 42
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 after initial definition*
