# Architecture

**Analysis Date:** 2026-03-15

## Pattern Overview

**Overall:** Multi-agent orchestration with task decomposition and evidence-driven analysis.

Sherlock Holmes AI implements a **conductor-orchestrator pattern** where:
1. A conductor agent breaks research queries into discrete sub-tasks
2. Specialized agents (researcher, analyst) execute sub-tasks independently
3. Evidence is collected and verified at each step
4. A reporter agent synthesizes findings into structured reports
5. Multiple interfaces deliver results (CLI, REST API, Telegram)

**Key Characteristics:**
- Task-driven architecture: queries flow through planning → execution → reporting pipeline
- Async-first design for I/O-bound operations (web requests, LLM calls)
- Evidence provenance: every claim must trace to a URL or document source
- Graceful degradation: tool failures don't halt investigation
- Modular tooling: web scraping, document parsing, and notifications are pluggable

## Layers

**Orchestration Layer (Agents):**
- Purpose: Break down research queries, execute sub-tasks, synthesize findings
- Location: `sherlock/agents/`
- Contains: conductor, researcher, reporter agents
- Depends on: LLM client (Anthropic), tools layer, models
- Used by: CLI, API, Telegram bot

**Tool Layer (External I/O):**
- Purpose: Encapsulate interactions with external services and data sources
- Location: `sherlock/tools/`
- Contains: web scraping/search, document parsing, Telegram notifications, caching
- Depends on: external APIs, config settings
- Used by: agents, CLI, API

**Data Model Layer:**
- Purpose: Define investigation, evidence, findings, sub-tasks with Pydantic validation
- Location: `sherlock/models.py`
- Contains: Investigation, Evidence, Finding, SubTask, InvestigationType, Confidence enums
- Depends on: Pydantic
- Used by: all layers

**Configuration Layer:**
- Purpose: Load and manage settings from environment variables
- Location: `sherlock/config.py`
- Contains: Settings class with API keys, paths, agent tuning parameters
- Depends on: pydantic-settings, environment
- Used by: all layers

**Interface Layer:**
- Purpose: Expose investigation capabilities through multiple channels
- Location: `sherlock/cli.py`, `sherlock/api.py`, `sherlock/tools/telegram.py`
- Contains: Typer CLI, FastAPI server, Telegram bot
- Depends on: orchestration layer, config
- Used by: end users, external systems

## Data Flow

**CLI Investigation Flow:**

1. User runs: `sherlock investigate "What is Company X's market position?"`
2. CLI calls `_run_investigation()` async function
3. **Planning Phase:**
   - `plan_investigation(query)` calls conductor agent
   - Conductor (via Anthropic Claude) classifies investigation type and breaks into 2-5 sub-tasks
   - Returns Investigation object with pending sub-tasks
4. **Execution Phase:**
   - `execute_investigation(investigation)` iterates through sub-tasks
   - For each sub-task with agent="researcher":
     - `execute_research_task(task_description)` called
     - Generates 2-3 search queries
     - Performs web searches (cached) via `search_web(query)`
     - Collects Evidence objects with source URLs
     - LLM analyzes evidence and produces findings
   - Findings aggregated at investigation level
5. **Reporting Phase:**
   - `generate_report(investigation)` calls reporter agent
   - Reporter formats findings into markdown with citations
   - `save_report()` writes to timestamped file in `sherlock/outputs/`
6. **Notification Phase (optional):**
   - If `--notify` flag: sends Telegram notification via `notify_investigation_complete()`

**API Investigation Flow:**

1. POST `/investigate?query=...` endpoint
2. Same planning → execution → reporting → notification sequence
3. Returns JSON response with investigation ID, finding count, report path

**Telegram Bot Flow:**

1. User sends message to Telegram bot
2. `message_handler()` validates sender (checks chat_id)
3. Calls `_safe_investigate(on_investigate, query)` in background task
4. Same investigation pipeline runs with notifications enabled
5. Report delivered via Telegram document upload

**State Management:**

- Investigation object is the single source of truth; passes through each phase
- Sub-task status transitions: pending → running → completed | failed
- Investigation status: pending → running → completed | failed
- Evidence immutable once collected; aggregated across findings
- No persistent state layer (no database writes currently); reports saved to filesystem

## Key Abstractions

**Investigation:**
- Purpose: Container for a complete research workflow with query, type, tasks, findings
- Examples: `sherlock/models.py` line 75-88
- Pattern: Pydantic BaseModel with lifecycle status tracking

**Evidence:**
- Purpose: Immutable fact with source provenance (URL or document reference)
- Examples: `sherlock/models.py` line 41-51
- Pattern: Pydantic model; includes source_type, source_url, retrieved_at, confidence metadata

**Finding:**
- Purpose: Analytical claim backed by multiple pieces of evidence
- Examples: `sherlock/models.py` line 54-61
- Pattern: Pydantic model; confidence enum indicates corroboration level

**SubTask:**
- Purpose: Discrete unit of work assigned to an agent
- Examples: `sherlock/models.py` line 64-72
- Pattern: Pydantic model; agent field routes to correct handler

**Agent Functions:**
- Purpose: Async functions that take text input, call LLM, parse structured output
- Examples: `conduct_investigation()`, `execute_research_task()`, `generate_report()`
- Pattern: LLM system prompt → user message → JSON parse → return structured model

## Entry Points

**CLI Entry:**
- Location: `sherlock/cli.py` lines 21-99
- Triggers: `uv run sherlock investigate`, `sherlock serve`, `sherlock telegram`, `sherlock reports`
- Responsibilities: Argument parsing, progress visualization, file I/O, Telegram integration

**API Entry:**
- Location: `sherlock/api.py` lines 22-43
- Triggers: HTTP POST `/investigate`, GET `/reports`, GET `/reports/{filename}`
- Responsibilities: Request validation, endpoint routing, JSON serialization

**Telegram Bot Entry:**
- Location: `sherlock/tools/telegram.py` lines 107-176
- Triggers: Messages in configured Telegram chat
- Responsibilities: Auth check, background task dispatch, notification delivery

## Error Handling

**Strategy:** Fail gracefully with logging. If a tool fails (scraper, API, parser), log and continue.

**Patterns:**

- `try/except` blocks in tools with `continue` fallbacks (web.py lines 49-50, 81-82)
- Graceful degradation: investigation proceeds with partial evidence if search fails
- LLM output robustness: markdown fence stripping handles varied formatting (conductor.py lines 54-55)
- Telegram error handling: catches exceptions, sends user notification (telegram.py lines 34-35)
- Task-level isolation: one sub-task failure doesn't halt other sub-tasks (conductor.py lines 101-106)

## Cross-Cutting Concerns

**Logging:**
- Approach: Python stdlib logging; Telegram tool logs warnings (telegram.py line 14, 35, 59)
- Used for: notification failures, investigation errors via Telegram

**Validation:**
- Approach: Pydantic models enforce type checking and enum constraints
- Examples: InvestigationType, EvidenceSource, Confidence enums guarantee valid states

**Authentication:**
- Approach: Environment variables (ANTHROPIC_API_KEY, SHERLOCK_TELEGRAM_BOT_TOKEN)
- Enforcement: Telegram message handler checks chat_id against settings (telegram.py line 152)

**Caching:**
- Approach: File-based cache in `.sherlock_cache/` using SHA256 hashing
- Purpose: Avoid redundant web requests during development/testing
- Implementation: `_cache_key()`, `_read_cache()`, `_write_cache()` in web.py lines 91-116

**Async Coordination:**
- Approach: `asyncio` used throughout; `asyncio.create_task()` for background Telegram investigations
- Pattern: All I/O operations (LLM, web, file) are async

---

*Architecture analysis: 2026-03-15*
