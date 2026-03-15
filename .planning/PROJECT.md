# Sherlock Holmes AI

## What This Is

An autonomous AI-powered research agent that takes a natural language question, decomposes it into sub-tasks, gathers evidence from the web, synthesizes findings, and produces a fully sourced Markdown report. Accessible via CLI, FastAPI report viewer, and Telegram bot. Built for anyone who needs thorough, cited research without manual browsing.

## Core Value

Every claim in every report must cite a real source. Zero hallucinated evidence — if Sherlock can't find it, it says so.

## Requirements

### Validated

(None yet — starting fresh from spec)

### Active

- [ ] Conductor agent decomposes a query into 2-5 parallelizable sub-tasks with specific search queries
- [ ] Researcher agent executes sub-tasks: search → scrape → extract → structured findings
- [ ] Reporter agent synthesizes findings into a sourced Markdown report with inline citations
- [ ] DuckDuckGo search integration (default, no API key needed)
- [ ] Brave Search API integration (optional, configurable)
- [ ] Crawl4AI async web scraping with 15-second timeout and graceful failure
- [ ] Disk-based cache for all web scrapes (SHA256 URL hash, .sherlock_cache/)
- [ ] Pydantic v2 models for all data boundaries (Investigation, SubTask, Finding, Source, etc.)
- [ ] Structured output from Claude via tool_use (function calling), not markdown parsing
- [ ] Typer CLI: `sherlock investigate "query"` produces a timestamped .md report
- [ ] Telegram bot: receive message → acknowledge → share plan → progress per sub-task → summary + link to full report
- [ ] Telegram notifications: on_investigation_start, on_subtask_complete, on_report_ready
- [ ] FastAPI report viewer: dark-mode UI, list reports, render Markdown as HTML with clickable sources
- [ ] PDF parsing via pymupdf4llm
- [ ] DOCX parsing via python-docx
- [ ] Rich CLI output: panels, tables, spinners for investigation progress
- [ ] Pydantic Settings config from env vars with SHERLOCK_ prefix
- [ ] Async everywhere for I/O (web, LLM, file operations)
- [ ] Graceful degradation: failed scrapes/sub-tasks logged and skipped, never crash

### Out of Scope

- Database persistence (SQLite/aiosqlite) — filesystem reports are sufficient for v1
- Concurrent sub-task execution — sequential first, asyncio.gather later
- Authentication on the report viewer — local-only access
- Docker/deployment packaging — not needed until core loop works
- PyPI publishing — not v1
- OAuth or multi-user support on Telegram — single chat_id auth

## Context

- Rebuilding from scratch based on detailed spec; existing code serves as reference but won't be reused
- Priority flow: Telegram bot end-to-end (message → plan → progress → report)
- Python 3.12+ with uv package manager (pyproject.toml, no requirements.txt)
- Anthropic Claude claude-sonnet-4-20250514 for all agent reasoning via tool_use structured output
- DuckDuckGo as default search, Brave Search API as optional upgrade
- Crawl4AI preferred over raw httpx for JS-rendered pages
- Reports are timestamped Markdown files in sherlock/outputs/

## Constraints

- **LLM Provider**: Anthropic Claude only — no OpenAI, no local models
- **Package Manager**: uv only — no pip, no requirements.txt
- **Data Models**: Pydantic v2 everywhere — no raw dicts crossing function boundaries
- **Evidence Policy**: Every factual claim must trace to a URL or document source
- **LLM Output**: Use tool_use (function calling) for structured JSON — no markdown code block parsing
- **Async**: All I/O-bound operations must be async
- **No Hardcoded Keys**: Everything from env vars via pydantic-settings

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Start fresh, ignore existing code | Spec is detailed enough to rebuild cleanly; existing code doesn't match target architecture | — Pending |
| Telegram bot as priority flow | User's primary interaction mode; validates entire pipeline end-to-end | — Pending |
| DuckDuckGo + Brave dual search | DDG is free/instant for dev; Brave is more reliable for production | — Pending |
| Sequential sub-tasks first | Simpler to debug; concurrent execution is a follow-up optimization | — Pending |
| File-based reports, no database | Simplest persistence; SQLite deferred to v2 | — Pending |
| Crawl4AI over raw httpx | Better handling of JS-rendered pages which are common in modern web | — Pending |

---
*Last updated: 2026-03-15 after initialization*
