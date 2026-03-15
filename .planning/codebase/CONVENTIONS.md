# Coding Conventions

**Analysis Date:** 2026-03-15

## Naming Patterns

**Files:**
- Module names: lowercase with underscores (e.g., `web.py`, `conductor.py`, `telegram.py`)
- Agent files: `{agent_name}.py` in `sherlock/agents/` (e.g., `researcher.py`, `reporter.py`, `conductor.py`)
- Tool files: `{tool_name}.py` in `sherlock/tools/` (e.g., `web.py`, `documents.py`, `telegram.py`)
- Model files: `models.py` for all Pydantic models; `config.py` for Settings

**Functions:**
- Public functions: snake_case, descriptive names starting with verbs (e.g., `async def search_web()`, `async def parse_pdf()`, `async def generate_report()`)
- Private functions: Leading underscore prefix with snake_case (e.g., `def _cache_key()`, `def _cache_path()`, `async def _safe_investigate()`)
- Async functions: Explicitly declared with `async def`, all I/O-bound operations are async
- Handler functions: `{entity}_handler()` pattern for event handlers (e.g., `async def start_handler()`, `async def message_handler()`)

**Variables:**
- Constants and enums: UPPERCASE (used in Enum classes: `HIGH`, `MEDIUM`, `LOW`, `SPECULATIVE`)
- Enum class names: Capitalized (e.g., `InvestigationType`, `EvidenceSource`, `Confidence`)
- Model field names: snake_case (e.g., `source_type`, `source_url`, `confidence`, `investigation_type`)
- Local variables: snake_case (e.g., `cache_key`, `findings`, `all_evidence`)

**Types:**
- Model classes inherit from `BaseModel` or `BaseSettings` (Pydantic)
- Enum classes use `str, Enum` or `Enum` mixins
- Type hints: Always present on function signatures and class fields
- Optional fields: Use `Type | None` syntax (Python 3.10+ union syntax)

## Code Style

**Formatting:**
- Ruff with target Python 3.12
- Line length: 100 characters (configured in `pyproject.toml`)
- Uses `ruff format` for code formatting
- Uses `ruff check` for linting with rules: E, F, I, N, W, UP, B, SIM

**Linting:**
- Ruff enforcement of:
  - `E` — pycodestyle errors
  - `F` — pyflakes undefined names
  - `I` — isort import ordering
  - `N` — pep8 naming conventions
  - `W` — pycodestyle warnings
  - `UP` — pyupgrade modernization
  - `B` — flake8-bugbear bug detection
  - `SIM` — flake8-simplify code simplification

**Type Checking:**
- MyPy with `strict = true` mode (configured in `pyproject.toml`)
- All files must pass strict type checking
- Type hints required on all public APIs

## Import Organization

**Order:**
1. `from __future__ import annotations` — Always first (enables PEP 563 postponed evaluation)
2. Standard library imports — `json`, `asyncio`, `logging`, `pathlib`, etc.
3. Third-party imports — `anthropic`, `pydantic`, `httpx`, `fastapi`, `typer`, `bs4`, etc.
4. Local imports — `from sherlock.config import settings`, `from sherlock.models import ...`, etc.

**Path Aliases:**
- No path aliases configured; all imports use full module paths
- Relative imports not used; always use absolute imports from `sherlock` package root

**Example import block:**
```python
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

from sherlock.config import settings
from sherlock.models import Investigation, Finding
```

## Error Handling

**Patterns:**
- Bare `except Exception:` used for graceful degradation in tools (e.g., web scraping, file parsing)
- Fail gracefully: Errors are logged but don't halt execution
- Specific errors only at boundaries: Custom HTTPException raised in FastAPI routes with status codes
- Error propagation in agents: Caught in `execute_investigation()` and stored in `task.error`
- Telegram notifications: Wrapped with try/except and logged to `logger.warning()` or `logger.error()`

**Example:**
```python
try:
    results = await search_web(query)
except Exception:
    continue  # Fail gracefully, continue with what we have
```

**Custom errors:**
- No custom exception classes defined; use built-in exceptions
- `FileNotFoundError` raised when document paths don't exist
- `ValueError` raised for configuration issues (e.g., Telegram not configured)

## Logging

**Framework:** Standard library `logging` module

**Usage:**
- Logger created per module: `logger = logging.getLogger(__name__)`
- Used only in `sherlock/tools/telegram.py` for warnings and errors
- Log levels:
  - `logger.warning()` — Non-critical failures (e.g., Telegram notification failed)
  - `logger.error()` — Critical failures (e.g., Investigation failed via Telegram)

**Pattern:**
```python
logger = logging.getLogger(__name__)

async def send_notification(message: str) -> None:
    try:
        # ...
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")
```

**Console output:** Uses `rich` library for rich terminal output in CLI (`sherlock/cli.py`):
- `Console` for general output
- `Panel` for highlighted sections
- `Progress` for task tracking with spinners

## Comments

**When to Comment:**
- Docstrings required on all public functions and classes (Google or NumPy style)
- Inline comments for non-obvious logic
- Markdown fence stripping in LLM responses documented inline
- Cache behavior explained in function docstrings

**Docstring Pattern:**
```python
async def search_web(query: str, max_results: int = 10) -> list[dict[str, str]]:
    """Search the web using a search API.

    This is a stub that uses DuckDuckGo HTML search as a free fallback.
    Replace with SerpAPI, Brave Search API, or similar for production use.
    """
```

**JSDoc/TSDoc:** Not applicable (Python codebase)

## Function Design

**Size:**
- Functions typically 15-50 lines
- Longer functions (100+ lines) only in CLI/API handlers where readability demands
- Agents keep orchestration logic to 40-50 lines

**Parameters:**
- Positional parameters for required arguments
- Keyword-only parameters with defaults for optional settings (e.g., `max_results: int = 10`)
- Type hints required on all parameters

**Return Values:**
- Typed return statements (e.g., `-> Investigation`, `-> list[Finding]`, `-> None`)
- Async functions use coroutine return types: `async def func() -> ReturnType`
- Functions returning multiple values use tuple unpacking or wrap in a model

**Example:**
```python
async def execute_research_task(task_description: str) -> list[Finding]:
    """Execute a research sub-task: search, scrape, analyze, return findings."""
    # Implementation
    return findings
```

## Module Design

**Exports:**
- Functions exported directly from modules (no barrel exports required)
- Models exported from `sherlock/models.py`
- Settings exported from `sherlock/config.py`
- Tools namespace organized by purpose: `sherlock/tools/web.py`, `sherlock/tools/documents.py`

**Barrel Files:**
- `__init__.py` files exist but are empty (no re-exports)
- Direct imports preferred: `from sherlock.models import Investigation` not `from sherlock import Investigation`

**Module Structure Pattern:**
```python
"""Module docstring with purpose and main exports."""

from __future__ import annotations

# Imports section

# Public functions (no leading underscore)
async def public_function() -> ReturnType:
    """Docstring."""
    # Implementation

# Private helpers (leading underscore)
def _private_helper() -> None:
    """Internal helper."""
```

## Key Architectural Conventions

**Pydantic for Data:**
- All data structures use Pydantic `BaseModel` for validation and serialization
- Models in `sherlock/models.py`: `Investigation`, `Finding`, `Evidence`, `SubTask`, `InvestigationType`, `EvidenceSource`, `Confidence`
- Settings in `sherlock/config.py` use `BaseSettings` with environment variable prefixing

**Async/Await:**
- All I/O operations are async: web requests, file reads, LLM calls
- Functions using async operations must be `async def`
- Orchestration in `sherlock/agents/` uses `asyncio` patterns

**Agent Pattern:**
- Agents receive specific tasks and return structured results
- `conductor.py` — Plans and orchestrates sub-tasks
- `researcher.py` — Gathers and analyzes evidence
- `reporter.py` — Synthesizes findings into reports
- Each agent is independently callable and doesn't maintain state

**Tool Organization:**
- Tools are reusable, focused utility functions
- `web.py` — Search and scrape with caching
- `documents.py` — PDF and DOCX parsing
- `telegram.py` — Telegram bot and notifications
- Tools handle errors gracefully and log non-critically

---

*Convention analysis: 2026-03-15*
