# Roadmap: Sherlock Holmes AI

## Overview

Build a clean-room autonomous research agent in five bottom-up phases. Every phase delivers a verifiable, runnable capability before the next begins. The stack is Pydantic models first (the contract for everything), then web tools (the evidence source), then agents (the intelligence), then all three interfaces together (CLI + Telegram + viewer), and finally document ingestion as a self-contained additive feature. By the end of Phase 4 the priority Telegram flow — message in, plan shared, progress updates, sourced report out — is fully operational. Phase 5 adds PDF/DOCX evidence without disrupting the core pipeline.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Pydantic models, config, and project scaffolding
- [ ] **Phase 2: Tool Layer** - Web search, scraping, caching, and document parsing
- [ ] **Phase 3: Agent Pipeline** - Conductor, researcher, and reporter agents producing cited reports
- [ ] **Phase 4: Interfaces** - CLI, Telegram bot, and FastAPI report viewer
- [ ] **Phase 5: Document Ingestion** - PDF and DOCX evidence feeding the existing pipeline

## Phase Details

### Phase 1: Foundation
**Goal**: The data contracts and configuration layer that every other component depends on are correct and complete.
**Depends on**: Nothing (first phase)
**Requirements**: MOD-01, MOD-02, MOD-03, MOD-04, MOD-05, CFG-01, CFG-02
**Success Criteria** (what must be TRUE):
  1. Running `uv run python -c "from sherlock.models import Investigation, SubTask, Finding, Source, InvestigationPlan; print('ok')"` exits 0
  2. An Investigation object can be constructed, mutated through all InvestigationStatus enum states, and serialized to JSON with no raw dicts
  3. A Source object with no URL raises a validation error; a Source with a URL passes
  4. Running `uv run python -c "from sherlock.config import settings; print(settings.model)"` reads from env and exits 0
  5. Research depth can be set to quick, standard, or deep via CFG-02 and the value is accessible from settings
**Plans**: TBD

Plans:
- [ ] 01-01: Pydantic models and enums (Investigation, SubTask, Finding, Source, InvestigationPlan, InvestigationStatus, InvestigationType)
- [ ] 01-02: Config layer (pydantic-settings with SHERLOCK_ prefix, research depth, model selection)

### Phase 2: Tool Layer
**Goal**: Working, cached, failure-safe web search and scraping tools that agents can call without worrying about rate limits, invalid content, or blocking I/O.
**Depends on**: Phase 1
**Requirements**: WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, WEB-06, WEB-07, WEB-08, WEB-09
**Success Criteria** (what must be TRUE):
  1. `uv run python -c "from sherlock.tools.web import search_web; import asyncio; results = asyncio.run(search_web('Python asyncio')); print(len(results), 'results')"` returns at least 1 result or prints a clear zero-result warning
  2. Scraping a URL that was fetched before returns the cached result without a network call (observable via log output)
  3. Scraping a URL that returns a Cloudflare challenge or CAPTCHA page does not get cached; a valid page does get cached
  4. A scrape that times out or fails returns None and logs a warning — no exception is raised to the caller
  5. Passing the same list of URLs with duplicates into source deduplication returns a list with each URL appearing once
**Plans**: TBD

Plans:
- [ ] 02-01: DuckDuckGo and Brave Search integration with zero-result detection and retry backoff
- [ ] 02-02: Crawl4AI scraping with SHA256 disk cache, content validation, and graceful failure

### Phase 3: Agent Pipeline
**Goal**: A natural language question produces a fully sourced Markdown report where every inline citation traces to a URL that was actually fetched during the investigation.
**Depends on**: Phase 2
**Requirements**: AGT-01, AGT-02, AGT-03, AGT-04, AGT-05, AGT-06, AGT-07
**Success Criteria** (what must be TRUE):
  1. Running the conductor against a test query produces an InvestigationPlan with 2-5 sub-tasks, each with specific search queries, using tool_use (no raw JSON parsing)
  2. The researcher executes a sub-task and returns findings where each Finding references only the specific evidence items that support it (not all evidence)
  3. The reporter generates a Markdown report where every URL in inline citations is present in investigation.sources — the post-generation URL audit passes
  4. A report includes a failure audit section listing any URLs that were tried but unreachable or blocked
  5. A tool_use validation failure on any single sub-task logs the error, skips that sub-task, and continues — the investigation completes with the remaining findings
**Plans**: TBD

Plans:
- [ ] 03-01: Researcher agent (tool_use structured output, per-subtask evidence extraction, index-based citation mapping)
- [ ] 03-02: Reporter agent (sourced Markdown synthesis, post-generation URL audit, failure audit section)
- [ ] 03-03: Conductor agent (query decomposition, sequential sub-task execution loop, investigation lifecycle management)

### Phase 4: Interfaces
**Goal**: Users can run investigations via three interfaces — terminal command, Telegram message, or web viewer — with the Telegram bot as the end-to-end priority flow.
**Depends on**: Phase 3
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06, CLI-07, CLI-08, TG-01, TG-02, TG-03, TG-04, TG-05, TG-06, TG-07, TG-08, VIEW-01, VIEW-02, VIEW-03, VIEW-04, VIEW-05
**Success Criteria** (what must be TRUE):
  1. `uv run sherlock investigate "test query"` produces a timestamped .md file in outputs/ with Rich progress display showing the plan table and per-subtask spinners
  2. Sending a message to the Telegram bot triggers an immediate acknowledgment, then the sub-task plan, then a progress update for each sub-task, then a final summary with a link to the report in the viewer
  3. Opening the FastAPI viewer at localhost shows a list of all reports; clicking a report renders it as dark-mode HTML with clickable source links
  4. `uv run sherlock investigate "test query" --notify` sends a Telegram notification on completion without starting the bot listener
  5. `uv run sherlock investigate "test query" --depth quick` runs a visibly shorter investigation than `--depth deep`
**Plans**: TBD

Plans:
- [ ] 04-01: Typer CLI with Rich progress display (investigate, reports, serve, telegram commands and flags)
- [ ] 04-02: Telegram bot handler (delete_webhook, async context manager, plan sharing, per-subtask progress, message truncation)
- [ ] 04-03: FastAPI report viewer (report listing, Markdown-to-HTML via Jinja2, dark-mode CSS, clickable sources)

### Phase 5: Document Ingestion
**Goal**: Users can include PDF and DOCX files as evidence sources and the documents flow through the same researcher-to-reporter pipeline as web content.
**Depends on**: Phase 3
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04
**Success Criteria** (what must be TRUE):
  1. Passing a text-based PDF to the document tool returns Markdown content that the researcher agent can ingest as evidence
  2. Passing a scanned/image-only PDF returns a clear error message, not an empty string or exception
  3. Passing a .docx file returns extracted paragraph text as evidence
  4. A report generated from a document investigation includes the document as a cited source (not a web URL, but with a clear file path reference)
**Plans**: TBD

Plans:
- [ ] 05-01: PDF parsing (pymupdf4llm), DOCX parsing (python-docx), scanned PDF detection, document evidence integration

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/2 | Not started | - |
| 2. Tool Layer | 0/2 | Not started | - |
| 3. Agent Pipeline | 0/3 | Not started | - |
| 4. Interfaces | 0/3 | Not started | - |
| 5. Document Ingestion | 0/1 | Not started | - |
