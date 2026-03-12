# CLAUDE.md — Sherlock Holmes AI

## Project Overview

Sherlock Holmes AI is an open-source AI-powered research and investigation agent. It takes a research question or investigation brief, autonomously gathers evidence from multiple sources (web, documents, databases), analyzes findings, and produces structured investigation reports.

**Core principle:** Every investigation must cite its sources. No hallucinated evidence. No fabricated citations. If Sherlock can't find it, it says so.

## Tech Stack

- **Language:** Python 3.12+
- **Package Manager:** uv
- **LLM:** Anthropic Claude API (claude-sonnet-4-20250514 default, claude-opus-4-6 for deep analysis)
- **Web Scraping:** crawl4ai, httpx, beautifulsoup4
- **Document Parsing:** pymupdf, pdfplumber, python-docx
- **CLI:** typer + rich
- **API:** FastAPI + uvicorn
- **Viewer:** Single-page React app (served by FastAPI)
- **Storage:** SQLite via aiosqlite (investigation history)
- **Testing:** pytest + pytest-asyncio

## Architecture

```
sherlock/
├── agents/          # Investigation orchestration agents
│   ├── conductor.py     # Main orchestrator — breaks query into sub-tasks
│   ├── researcher.py    # Web research agent
│   ├── analyst.py       # Evidence synthesis and analysis
│   └── reporter.py      # Report generation
├── tools/           # Reusable tool modules
│   ├── web.py           # Web scraping, search, OSINT
│   ├── documents.py     # PDF/DOCX parsing and extraction
│   ├── search.py        # Search engine integration
│   ├── telegram.py      # Telegram bot — notifications + inbound investigations
│   └── cache.py         # Request caching layer
├── parsers/         # Output parsers and formatters
│   ├── evidence.py      # Evidence chain data models
│   └── report.py        # Report formatting (markdown, JSON, HTML)
├── outputs/         # Generated reports land here
├── config.py        # Settings, API keys, defaults
├── models.py        # Pydantic models for investigations
├── db.py            # SQLite investigation history
└── cli.py           # Typer CLI entrypoint
```

## GSD Workflow

When working on this codebase, follow this order:

1. **Understand** — Read the relevant files before changing anything
2. **Plan** — State what you're going to change and why (one sentence)
3. **Implement** — Make the change
4. **Verify** — Run the relevant test or smoke test
5. **Commit** — Atomic commits with conventional commit messages

## Commands

```bash
# Install dependencies
uv sync

# Run CLI
uv run sherlock investigate "What is Company X's market position?"

# Run with Telegram notifications
uv run sherlock investigate "your question" --notify

# Start Telegram bot (listens for messages → kicks off investigations)
uv run sherlock telegram

# Run API server
uv run uvicorn sherlock.api:app --reload --port 8000

# Run tests
uv run pytest tests/ -v

# Type check
uv run mypy sherlock/

# Format
uv run ruff check --fix sherlock/
uv run ruff format sherlock/
```

## Key Rules

- **Never fabricate sources.** Every claim in a report must trace to a retrieved URL or document.
- **Fail gracefully.** If a tool (scraper, API, parser) fails, log it and continue with what you have.
- **Cache aggressively.** Web requests are cached in `.sherlock_cache/` to avoid redundant fetches.
- **Structured output.** All agent outputs use Pydantic models. No raw dicts floating around.
- **Async by default.** All I/O-bound operations (web, LLM calls, file reads) are async.

## Conventional Commits

```
feat: add new capability
fix: bug fix
refactor: code restructure (no behavior change)
docs: documentation only
test: add or fix tests
chore: dependencies, config, CI
```

## Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...       # Required
SHERLOCK_MODEL=claude-sonnet-4-20250514  # Default model
SHERLOCK_DEEP_MODEL=claude-opus-4-6      # For deep analysis passes
SHERLOCK_CACHE_DIR=.sherlock_cache        # Cache directory
SHERLOCK_OUTPUT_DIR=sherlock/outputs      # Report output directory
SHERLOCK_TELEGRAM_BOT_TOKEN=...          # Telegram bot token (optional)
SHERLOCK_TELEGRAM_CHAT_ID=...            # Telegram chat ID (optional)
```

## On `/clear`

Do NOT auto-plan after `/clear`. Just acknowledge and wait for the next instruction.
