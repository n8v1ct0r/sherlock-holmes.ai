# Testing Patterns

**Analysis Date:** 2026-03-15

## Test Framework

**Runner:**
- pytest 8.3.0+
- pytest-asyncio 0.24.0+ (for async test support)
- Config: `pyproject.toml` with `asyncio_mode = "auto"`
- Test paths: `tests/`

**Assertion Library:**
- pytest built-in assertions (standard `assert` statements)

**Run Commands:**
```bash
# Run all tests
uv run pytest tests/ -v

# Watch mode (requires pytest-watch, not in current deps)
uv run pytest tests/ -v --tb=short

# Coverage (requires pytest-cov, not in current deps)
# Coverage not yet configured
```

## Test File Organization

**Location:**
- Tests co-located in `tests/` directory at project root
- One test file per module being tested
- Pattern: `test_{module_name}.py`

**Naming:**
- Test files: `test_*.py` (e.g., `test_models.py`)
- Test functions: `test_{feature_being_tested}()` (e.g., `test_evidence_creation()`)
- No class-based tests; all functions

**Current Structure:**
```
tests/
├── __init__.py        # Empty marker file
└── test_models.py     # Tests for sherlock/models.py
```

## Test Structure

**Suite Organization:**
- Flat function-based tests (no TestCase classes)
- No fixtures configured yet (tests create objects directly)
- Each test is independent and self-contained

**Test pattern from `tests/test_models.py`:**
```python
def test_evidence_creation():
    e = Evidence(
        source_type=EvidenceSource.WEB_SCRAPE,
        source_url="https://example.com",
        content="Test content",
    )
    assert e.source_url == "https://example.com"
    assert e.confidence == Confidence.MEDIUM  # default
```

**Patterns:**
- **Setup**: Direct object instantiation in test function (no setup/teardown)
- **Assertion**: Single responsibility per test, multiple assertions grouped by concern
- **Naming clarity**: Test name describes what is being tested and expected outcome

## Test Coverage

**Existing Tests:**
- `test_models.py` — Tests Pydantic model creation and defaults (5 tests)
  - `test_evidence_creation()` — Evidence model instantiation
  - `test_finding_with_evidence()` — Finding model with attached evidence
  - `test_investigation_lifecycle()` — Investigation state transitions
  - `test_subtask_creation()` — SubTask model instantiation

**What's NOT Tested (Critical Gaps):**
- Async agent functions (`execute_research_task()`, `plan_investigation()`, `execute_investigation()`)
- Web tools (`search_web()`, `scrape_url()`, caching behavior)
- Document parsing (`parse_pdf()`, `parse_docx()`)
- Report generation (`generate_report()`, `save_report()`)
- API endpoints (`run_investigation()`, `list_reports()`, `get_report()`)
- CLI commands and Telegram bot integration
- LLM response parsing (JSON extraction from markdown fences)
- Error handling and graceful degradation

**Requirements:** None enforced; no coverage target

## Mocking

**Framework:** Not used yet

**What Should Be Mocked (for future tests):**
- `anthropic.AsyncAnthropic` — LLM calls are expensive and non-deterministic
- `httpx.AsyncClient` — External web requests
- `telegram.Bot` — Telegram API calls
- File I/O — For document parsing tests

**What NOT to Mock:**
- Pydantic models — Test with real instances (they're pure data structures)
- Local file operations in cache — Use temporary directories
- Configuration loading — Test with test environment variables

## Async Testing

**Framework Support:**
- pytest-asyncio handles async test functions automatically
- `asyncio_mode = "auto"` in `pyproject.toml` enables implicit async test detection

**Current async test structure:**
- No async tests exist yet; all current tests are synchronous
- Async tests should use `async def test_name()` syntax

**Expected async test pattern:**
```python
async def test_search_web_returns_results():
    results = await search_web("Python asyncio")
    assert len(results) > 0
    assert "title" in results[0]
    assert "url" in results[0]
```

**Note:** Async tests require careful mocking of `httpx.AsyncClient` and `anthropic.AsyncAnthropic` to avoid external dependencies.

## Error Testing

**Patterns used in existing code (but not yet tested):**
- `FileNotFoundError` raised when document doesn't exist: `if not path.exists(): raise FileNotFoundError(...)`
- `ValueError` raised for configuration: `raise ValueError("Telegram not configured...")`
- Graceful exception catching: `except Exception: continue`

**Future error test pattern:**
```python
import pytest

async def test_parse_pdf_missing_file():
    with pytest.raises(FileNotFoundError):
        await parse_pdf("/nonexistent/file.pdf")

def test_telegram_not_configured():
    with pytest.raises(ValueError):
        create_bot_application()  # If telegram_configured is False
```

## Fixtures and Test Data

**Test Data:**
- None currently created; tests use hardcoded values
- Pydantic model defaults tested: `e.confidence == Confidence.MEDIUM`

**Recommended fixtures (not yet implemented):**
```python
@pytest.fixture
def sample_evidence():
    return Evidence(
        source_type=EvidenceSource.WEB_SCRAPE,
        source_url="https://example.com",
        source_title="Example",
        content="Test content",
        confidence=Confidence.HIGH,
    )

@pytest.fixture
def sample_finding(sample_evidence):
    return Finding(
        claim="Test claim",
        evidence=[sample_evidence],
        confidence=Confidence.HIGH,
        tags=["test"],
    )
```

**Location:**
- Recommended: `tests/conftest.py` for shared fixtures
- Currently: None — no conftest.py exists

## Test Types

**Unit Tests:**
- Scope: Pydantic model instantiation and field defaults
- Approach: Synchronous direct instantiation
- Location: `tests/test_models.py`
- Example: `test_evidence_creation()` validates model field assignment

**Integration Tests:**
- Not yet implemented
- Would test: Agent workflows with mocked LLM/web calls
- Recommended location: `tests/test_agents_integration.py`
- Scope: Full investigation pipeline (plan → execute → report)

**E2E Tests:**
- Not implemented
- Not used; agent testing done via CLI with real API calls during development

**API Tests:**
- Not implemented
- Would test: FastAPI endpoints via `httpx.AsyncClient` or `pytest.fixture(client)`
- Recommended: Use FastAPI's TestClient

## Coverage Status

**Current coverage:**
- Model tests: 5 tests covering basic instantiation
- Agent tests: 0 tests
- Tool tests: 0 tests (web, documents, telegram)
- API tests: 0 tests
- CLI tests: 0 tests

**Critical gaps identified:**
1. **Agent orchestration** — `conductor.py`, `researcher.py`, `reporter.py` untested
2. **Web operations** — `search_web()`, `scrape_url()`, caching untested
3. **Document parsing** — `parse_pdf()`, `parse_docx()` untested
4. **Report generation** — `generate_report()`, `save_report()` untested
5. **External integrations** — Telegram, FastAPI endpoints untested
6. **Error paths** — Exception handling not validated

**Test Maintenance:**
- Sync test expectations when models change (e.g., default values)
- Add integration tests before modifying agent orchestration

## Common Testing Constraints

**No Test Database:**
- Investigation history uses SQLite in `.sherlock_cache/investigations.db`
- No tests currently interact with database
- Recommended: Use in-memory SQLite or fixture-based cleanup

**External Service Dependencies:**
- DuckDuckGo search (no API key required but calls live service)
- Anthropic Claude API (requires valid API key and costs money)
- Telegram Bot API (requires valid credentials)
- **Recommendation:** Mock all external services in unit tests

**Cache Behavior:**
- Web tools cache results in `.sherlock_cache/` directory
- Tests don't validate cache behavior yet
- `_cache_key()`, `_read_cache()`, `_write_cache()` untested

## Running Tests Locally

**Full suite:**
```bash
cd /Users/cyrilvictor/Library/Mobile\ Documents/com~apple~CloudDocs/Personal/Portfolio\ Projects/sherlock-holmes.ai/sherlock-holmes.ai
uv run pytest tests/ -v
```

**Single test file:**
```bash
uv run pytest tests/test_models.py -v
```

**Single test:**
```bash
uv run pytest tests/test_models.py::test_evidence_creation -v
```

**With output on failure:**
```bash
uv run pytest tests/ -vv --tb=long
```

---

*Testing analysis: 2026-03-15*
