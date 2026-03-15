# Codebase Structure

**Analysis Date:** 2026-03-15

## Directory Layout

```
sherlock-holmes.ai/
├── sherlock/                      # Main package
│   ├── __init__.py                # Package marker
│   ├── cli.py                     # Typer CLI entrypoint (investigate, serve, telegram, reports commands)
│   ├── api.py                     # FastAPI server with endpoints and report viewer UI
│   ├── config.py                  # Settings management (env variables, paths, defaults)
│   ├── models.py                  # Pydantic data models (Investigation, Evidence, Finding, etc.)
│   ├── agents/                    # Investigation orchestration agents
│   │   ├── __init__.py
│   │   ├── conductor.py           # Plan investigations, assign sub-tasks
│   │   ├── researcher.py          # Execute research tasks: search, scrape, analyze
│   │   └── reporter.py            # Generate markdown reports from findings
│   ├── tools/                     # Reusable tool modules
│   │   ├── __init__.py
│   │   ├── web.py                 # Web search and scraping (DuckDuckGo, BeautifulSoup, caching)
│   │   ├── documents.py           # PDF/DOCX parsing (pymupdf, python-docx)
│   │   └── telegram.py            # Telegram bot and notifications
│   ├── parsers/                   # Output parsers (currently empty, reserved for future)
│   │   └── __init__.py
│   └── outputs/                   # Generated investigation reports (markdown files)
├── tests/                         # Test suite
│   ├── __init__.py
│   └── test_models.py             # Unit tests for Pydantic models
├── .planning/                     # GSD planning documents (this directory)
│   └── codebase/
├── pyproject.toml                 # Project metadata, dependencies, tool config
├── .env                           # Environment variables (secrets; not committed)
├── .gitignore                     # Git ignoring (cache, outputs, .env)
├── CLAUDE.md                      # Project instructions for Claude agents
└── README.md                      # User-facing documentation
```

## Directory Purposes

**sherlock/:**
- Purpose: Main Python package containing all investigation logic
- Contains: Agents, tools, models, entry points, configuration
- Key files: `cli.py` (CLI), `api.py` (REST API), `config.py` (settings), `models.py` (data)

**sherlock/agents/:**
- Purpose: AI agents that orchestrate and execute investigations
- Contains: Conductor (planner), Researcher (gatherer), Reporter (synthesizer)
- Key files: `conductor.py` (task decomposition), `researcher.py` (evidence collection), `reporter.py` (output generation)

**sherlock/tools/:**
- Purpose: Reusable modules for external integrations and utilities
- Contains: Web I/O, document parsing, notifications, caching
- Key files: `web.py` (search + scrape), `documents.py` (PDF/DOCX), `telegram.py` (bot + notifications)

**sherlock/parsers/:**
- Purpose: Output parsers and formatters (reserved for future expansion)
- Contains: Currently empty; designed for custom evidence formatters or schema converters
- Key files: None yet

**sherlock/outputs/:**
- Purpose: Directory where generated investigation reports are saved
- Contains: Markdown files named by timestamp and query slug
- Generated: Yes, created at runtime by `save_report()`
- Committed: No (added to .gitignore)

**tests/:**
- Purpose: Test suite for models and utilities
- Contains: Unit tests using pytest
- Key files: `test_models.py` (Pydantic model validation)
- Run: `uv run pytest tests/ -v`

**.planning/codebase/:**
- Purpose: GSD codebase analysis documents
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, STACK.md, INTEGRATIONS.md, CONCERNS.md
- Generated: By `/gsd:map-codebase` command
- Committed: Yes, versioned with codebase

## Key File Locations

**Entry Points:**
- `sherlock/cli.py`: Typer CLI entrypoint; defines `investigate`, `serve`, `telegram`, `reports` commands
- `sherlock/api.py`: FastAPI application; defines REST endpoints and HTML report viewer
- `sherlock/tools/telegram.py`: Telegram bot application creator and notification functions

**Configuration:**
- `sherlock/config.py`: Settings class loads from `SHERLOCK_*` env vars and `.env` file
- `.env`: Runtime environment (not committed; must be created locally with ANTHROPIC_API_KEY)
- `pyproject.toml`: Project metadata, dependencies, tool configuration (ruff, mypy, pytest)

**Core Logic:**
- `sherlock/agents/conductor.py`: `plan_investigation()` breaks query into sub-tasks; `execute_investigation()` runs them
- `sherlock/agents/researcher.py`: `execute_research_task()` performs search, scrape, analyze cycle
- `sherlock/agents/reporter.py`: `generate_report()` creates markdown; `save_report()` writes to disk
- `sherlock/tools/web.py`: `search_web()` and `scrape_url()` with file-based caching
- `sherlock/tools/documents.py`: `parse_pdf()` and `parse_docx()` extract text from files
- `sherlock/tools/telegram.py`: `send_notification()`, `notify_investigation_complete()`, `create_bot_application()`

**Testing:**
- `tests/test_models.py`: Tests for Evidence, Finding, Investigation, SubTask Pydantic models
- Test discovery: pytest looks in `tests/` directory by default (see `pyproject.toml` line 69)

## Naming Conventions

**Files:**
- Snake_case: `conductor.py`, `web.py`, `test_models.py`
- Entry points in root: `cli.py`, `api.py`, `config.py`, `models.py`
- Agents in subdirectory: `agents/{agent_name}.py` (conductor, researcher, reporter)
- Tools in subdirectory: `tools/{tool_name}.py` (web, documents, telegram)

**Directories:**
- Lowercase: `agents/`, `tools/`, `parsers/`, `tests/`
- Functional grouping by domain (agents = orchestration; tools = I/O)
- `outputs/` for generated files

**Functions:**
- Async functions use `async def` prefix; camelCase or snake_case based on task
- Examples: `plan_investigation()`, `execute_research_task()`, `search_web()`, `notify_investigation_complete()`
- Agent execution functions: `execute_{agent_name}_task()` or `execute_{domain}_task()`

**Classes:**
- PascalCase for all classes: `Investigation`, `Evidence`, `Finding`, `SubTask`, `InvestigationType`, `Settings`
- Enum classes: `InvestigationType`, `EvidenceSource`, `Confidence`
- Models inherit from `pydantic.BaseModel` or `pydantic_settings.BaseSettings`

**Modules:**
- Tool modules expose primary async functions: `search_web()`, `scrape_url()`, `parse_pdf()`, etc.
- Agent modules expose entry-point functions: `plan_investigation()`, `execute_research_task()`, `generate_report()`
- Config module exports singleton: `from sherlock.config import settings`

## Where to Add New Code

**New Feature (e.g., add a new research capability):**
- Primary code: `sherlock/agents/` — add new agent or extend researcher.py
- Tool support: `sherlock/tools/` — add new tool if external I/O needed
- Models: `sherlock/models.py` — add new enums or data classes if needed
- Tests: `tests/test_{feature_name}.py`
- Example: To add PDF analysis agent, create `sherlock/agents/analyzer.py` and update conductor to route to it

**New Tool Integration (e.g., add a new data source):**
- Implementation: `sherlock/tools/{tool_name}.py`
- Pattern: Async functions with graceful error handling and optional caching
- Use in agent: Import tool in agent and call async function
- Example: To add Serp API search, create `sherlock/tools/search_api.py` and import in `researcher.py`

**New Interface (e.g., add a new CLI command or API endpoint):**
- CLI commands: `sherlock/cli.py` — add `@app.command()` function
- API endpoints: `sherlock/api.py` — add `@app.post()` or `@app.get()` route
- Telegram handlers: `sherlock/tools/telegram.py` — add handler in `create_bot_application()`
- Example: To add `sherlock list-cache`, add command to cli.py that calls cache utility

**Utilities and Helpers:**
- Shared helpers in `sherlock/tools/` if external dependency (web, file I/O)
- Pure functions in `sherlock/models.py` if data-related
- Cross-cutting in `sherlock/config.py` if configuration-related
- Example: Add rate limiting helper in tools module, not in agents

## Special Directories

**sherlock/outputs/:**
- Purpose: Generated investigation reports land here
- Generated: Yes, created by `save_report()` in reporter.py at runtime
- Committed: No (in .gitignore)
- Pattern: `{YYYYMMDD}_{HHMMSS}_{query_slug}.md`
- Accessed by: FastAPI GET `/reports/{filename}`, CLI `reports` command

**.sherlock_cache/:**
- Purpose: File-based cache for web requests and scrapes
- Generated: Yes, created by tools/web.py at runtime
- Committed: No (in .gitignore)
- Pattern: Cache keys are SHA256 hashes; files stored as `.json`
- Cleanup: Can be deleted manually; auto-repopulates on next run
- TTL: No expiration (persistent until deleted)

**tests/:**
- Purpose: pytest test suite
- Run command: `uv run pytest tests/ -v`
- Watch mode: `uv run pytest tests/ -v --tb=short`
- Coverage: `uv run pytest tests/ --cov=sherlock`
- New tests: Create `test_{feature}.py` in tests/ directory

---

*Structure analysis: 2026-03-15*
