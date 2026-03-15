# Architecture Patterns

**Domain:** Autonomous AI research agent with conductor-orchestrator pipeline
**Researched:** 2026-03-15
**Confidence:** HIGH — based on direct codebase analysis of the existing implementation

---

## Recommended Architecture

The conductor-orchestrator pattern is the right call for this domain. The system decomposes a
research query into parallel sub-tasks, delegates each to a specialized agent, collects structured
evidence, and synthesizes a cited report. The key design principle is that **the Investigation
object is the single source of truth** — it flows through every phase and accumulates state.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Interface Layer                            │
│   CLI (Typer)    │   API (FastAPI)   │   Telegram Bot           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Orchestration Layer (Agents)                  │
│                                                                 │
│   ┌─────────────┐     ┌──────────────┐     ┌───────────────┐   │
│   │  Conductor  │────▶│  Researcher  │────▶│   Reporter    │   │
│   │  (planner)  │     │  (gatherer)  │     │ (synthesizer) │   │
│   └─────────────┘     └──────────────┘     └───────────────┘   │
│          │                   │                     │            │
│          └───────────────────┴─────────────────────┘           │
│                              │                                  │
│                    Investigation (Pydantic model)               │
│              flows through and accumulates state                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Tool Layer (I/O)                         │
│   web.py            │   documents.py   │   telegram.py          │
│   (search+scrape)   │   (PDF/DOCX)     │   (notifications)      │
│                         cache.py                                │
│                         (.sherlock_cache/)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Model Layer                           │
│   models.py: Investigation, SubTask, Finding, Evidence          │
│   config.py: Settings (pydantic-settings, SHERLOCK_* env vars)  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Communicates With | Must NOT |
|-----------|---------------|-------------------|----------|
| `conductor.py` | Classify query, generate 2-5 SubTask objects, execute the task loop | Calls researcher; reads Investigation | Make web requests directly |
| `researcher.py` | For one SubTask: generate queries, gather Evidence, produce Findings | Calls web.py and LLM | Mutate Investigation state |
| `reporter.py` | Take completed Investigation, produce Markdown report, save to disk | Calls LLM; writes to outputs/ | Gather new evidence |
| `web.py` | search_web(), scrape_url(), with disk cache | httpx, DuckDuckGo, crawl4ai | Call LLM |
| `documents.py` | parse_pdf(), parse_docx() → list[Evidence] | pymupdf, python-docx | Call LLM or web |
| `telegram.py` | Bot handler + notification functions | Telegram API, calls conductor | Contain business logic |
| `models.py` | Pydantic models: Investigation, SubTask, Finding, Evidence | Imported by all layers | Import from agents or tools |
| `config.py` | Settings singleton from SHERLOCK_* env vars | pydantic-settings, .env | Import from agents or tools |
| `cli.py` | Typer commands → kick off investigation pipeline | Orchestration layer | Contain research logic |
| `api.py` | FastAPI routes + report viewer UI | Orchestration layer | Contain research logic |

**Dependency rule:** models.py and config.py are at the base — nothing they import can import them back. Tools import models; agents import tools and models; interfaces import agents. No circular deps.

---

## Data Flow

### Primary Investigation Flow

```
User query (string)
        │
        ▼
[Conductor: plan_investigation(query)]
  - LLM call: classify type, generate sub-tasks
  - Returns: Investigation(status="planned", sub_tasks=[SubTask, ...])
        │
        ▼
[Conductor: execute_investigation(investigation)]
  Loop over sub_tasks sequentially:
    │
    ▼ (per task)
  [Researcher: execute_research_task(task.description)]
    - LLM call #1: generate 2-3 search queries
    - Tool calls: search_web(query) × 3 → list[Evidence]
    - (Optional) scrape_url(url) for deeper content → Evidence
    - LLM call #2: analyze evidence → list[Finding] with claims + confidence
    - Returns: list[Finding]
    │
    ▼
  task.findings = findings; task.status = "completed"
    │
    ▼ (after all tasks)
  investigation.findings = flatten(task.findings)
  investigation.status = "completed"
        │
        ▼
[Reporter: generate_report(investigation)]
  - Serialize findings + sources into evidence_text
  - LLM call: produce Markdown with inline citations
  - Returns: markdown string
        │
        ▼
[Reporter: save_report(investigation, markdown)]
  - Write to sherlock/outputs/{timestamp}_{slug}.md
  - Returns: Path
        │
        ▼
[Optional] Telegram: notify_investigation_complete(...)
  - Send summary + file to configured chat
```

### Evidence Provenance Chain

The chain from raw web content to cited claim is:

```
URL / search result snippet
    → Evidence(source_url, source_title, content, source_type=WEB_SCRAPE, retrieved_at)
        → Finding(claim, confidence, evidence=[Evidence...], tags)
            → Investigation.findings[]
                → Reporter serializes finding.evidence[].source_url as markdown links
                    → Report: "Claim X [source](url)"
```

Every node in the chain has a UUID. Evidence is immutable once collected. The key integrity
constraint is: **a Finding with no Evidence items should never reach the Reporter**. The current
implementation violates this for failed sub-tasks — a known gap.

### State Machine

```
Investigation.status:
  pending → planned → running → completed
                            └→ failed (partial findings still collected)

SubTask.status:
  pending → running → completed
                  └→ failed (error captured in task.error)
```

---

## Patterns to Follow

### Pattern 1: Tool Use (Function Calling) for Structured LLM Output

**What:** Use Anthropic's `tool_use` / function calling to enforce JSON schema on LLM responses
instead of asking the LLM to return JSON in its text and then parsing it.

**When:** Every agent-to-LLM boundary where structured data is needed.

**Why better than current approach:** The existing code (`conductor.py:57`, `researcher.py:59,104`)
calls `json.loads()` on freeform text with only markdown fence stripping as preprocessing. A
malformed LLM response crashes the investigation with an unhandled `JSONDecodeError`. Tool use
forces the LLM to populate a defined schema, which the SDK validates before returning.

```python
# Current (fragile):
raw = response.content[0].text.strip()
if raw.startswith("```"):
    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
plan = json.loads(raw)  # Crashes if LLM deviates

# Target (robust):
response = await client.messages.create(
    model=settings.model,
    tools=[{
        "name": "plan_investigation",
        "input_schema": {
            "type": "object",
            "properties": {
                "investigation_type": {"type": "string", "enum": [...]},
                "sub_tasks": {"type": "array", "items": {...}}
            },
            "required": ["investigation_type", "sub_tasks"]
        }
    }],
    tool_choice={"type": "tool", "name": "plan_investigation"},
    ...
)
plan = response.content[0].input  # Already validated dict
```

### Pattern 2: Evidence-First Finding Construction

**What:** Gather evidence before generating findings. Never create a Finding without at least one
Evidence item attached. Attach only the evidence items that support the specific claim, not all
evidence from the task.

**When:** In researcher.py, after evidence gathering, before LLM analysis.

**Why:** The current code attaches ALL gathered evidence to EVERY finding (`researcher.py:112`),
creating O(findings × evidence) duplication. A task with 3 queries × 10 results = 30 Evidence
items gets duplicated across 5 findings = 150 records. The correct pattern is bidirectional:
LLM returns finding claims annotated with source indices, then we map indices to Evidence IDs.

```python
# Pattern: ask LLM to cite by index, then map
"findings": [
    {
        "claim": "...",
        "confidence": "high",
        "evidence_indices": [0, 2, 4]  # which evidence items support this
    }
]
# Then: finding.evidence = [all_evidence[i] for i in f["evidence_indices"]]
```

### Pattern 3: Graceful Degradation with Typed Errors

**What:** Differentiate transient failures (timeout, 429, network error) from permanent ones
(404, bad credentials, malformed input). Log with context; never swallow silently.

**When:** Every `except Exception: continue` block in tools and agents.

**Why:** The current broad catches in `web.py` and `researcher.py` make debugging impossible.
An Anthropic API rate limit looks identical to a network timeout looks identical to a code bug.

```python
# Instead of: except Exception: continue

except httpx.TimeoutException:
    logger.warning("Timeout scraping %s — skipping", url)
    continue
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:
        logger.warning("Rate limited on %s — backing off", url)
        await asyncio.sleep(2)
        continue
    logger.error("HTTP %d on %s", e.response.status_code, url)
    continue
except Exception:
    logger.exception("Unexpected error scraping %s", url)
    continue
```

### Pattern 4: Investigation as Immutable Context Object

**What:** Treat the Investigation as a context object passed by reference through the pipeline.
Each phase reads from it and writes to its designated fields only.

**When:** Designing any new phase or agent.

**Assignment contract:**
- Conductor writes: `investigation.sub_tasks`, `investigation.investigation_type`, `investigation.status`
- Researcher writes: `sub_task.findings`, `sub_task.status`, `sub_task.error` (its own task only)
- Reporter writes: `investigation.report_markdown`, `investigation.report_path`, `investigation.completed_at`
- No phase reads another phase's output fields before that phase completes.

### Pattern 5: Cache-Aside for All Web I/O

**What:** Check cache before any web request. Write to cache after successful response. Use full
SHA256 (not truncated) as the cache key to prevent collision.

**When:** Every call in `web.py` to external URLs.

**Why the current truncation is wrong:** `web.py:92` truncates the SHA256 to 16 chars. At 10K
distinct URLs, collision probability becomes non-negligible. Use the full 64-char hash.

```python
def _cache_key(self, url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()  # full 64 chars, no truncation
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Markdown Parsing of LLM JSON

**What:** Asking the LLM to "return valid JSON" in its text, then stripping fences and parsing.

**Why bad:** LLMs deviate from format under pressure. Any deviation crashes the pipeline. The
fix is tool_use (function calling), which enforces the schema at the API level.

**Consequence:** An investigation that cost several LLM calls fails at the final JSON parse with
zero output and a cryptic `JSONDecodeError`.

**Instead:** Use tool_use with `tool_choice: {"type": "tool"}` to force structured output.

### Anti-Pattern 2: All Evidence on Every Finding

**What:** Attaching all gathered evidence to every finding in a task.

**Why bad:** Memory scales at O(findings × evidence). A 5-finding task with 30 evidence items
becomes 150 records. When serialized into the Reporter prompt, this blows through context limits.

**Consequence:** Reports that include many tasks will hit token limits. Evidence in reports becomes
meaningless (every finding cites every source).

**Instead:** Map specific evidence items to each finding by index or ID.

### Anti-Pattern 3: Silent Exception Swallowing

**What:** `except Exception: continue` or `except Exception: pass` without logging.

**Why bad:** Production failures become invisible. Rate limits, quota exhaustion, DNS failures,
and code bugs all look identical: the task completes with fewer findings, no warning.

**Consequence:** Users get incomplete reports with no indication of what failed or why.

**Instead:** Log with full context (URL, query, exception type, message) at minimum WARNING level.

### Anti-Pattern 4: Status Strings Instead of Enums

**What:** `investigation.status: str = "pending"` accepting arbitrary strings.

**Why bad:** Typos create impossible states. `"complted"` is accepted. State machine logic
(`if task.status == "completed"`) silently misfires.

**Consequence:** Bugs in status transitions are invisible until behavior diverges.

**Instead:** `InvestigationStatus(str, Enum)` with values PENDING, PLANNED, RUNNING, COMPLETED, FAILED.

### Anti-Pattern 5: Agent Dispatch Default Fallback

**What:** `if task.agent == "researcher": ... else: # default to researcher anyway`

**Why bad:** The conductor can now assign unknown agent types (e.g., "analyst") and they silently
run as researcher. Future agent types can never be properly routed.

**Consequence:** Impossible to add a proper `analyst` agent without breaking existing plans.

**Instead:** `raise ValueError(f"Unknown agent type: {task.agent}")` — fail loudly so the
conductor's planning prompt can be fixed.

---

## Component Build Order

The system has clear dependency layers. Build bottom-up:

```
Layer 0 (No dependencies):
  models.py          — Pydantic models, enums, data contracts
  config.py          — Settings, env vars, directory setup

Layer 1 (Depends on Layer 0):
  tools/web.py       — search_web(), scrape_url(), cache
  tools/documents.py — parse_pdf(), parse_docx()
  tools/telegram.py  — send_notification(), notify_*()

Layer 2 (Depends on Layer 0 + 1):
  agents/researcher.py — execute_research_task() → list[Finding]
  agents/reporter.py   — generate_report(), save_report()

Layer 3 (Depends on Layer 0 + 1 + 2):
  agents/conductor.py  — plan_investigation(), execute_investigation()

Layer 4 (Depends on Layer 3, the full pipeline):
  cli.py            — Typer commands
  api.py            — FastAPI endpoints + report viewer
  tools/telegram.py — Bot handler (inbound message → conductor)
```

**Implication for phases:**

1. Build Layer 0 first (models + config). No phase should proceed without solid data models —
   they are the contract every other component depends on.
2. Build Layer 1 (tools) before agents. Agents must call real tools to be testable.
3. Build researcher before conductor. The conductor calls researcher; you can't test conductor
   without a working researcher.
4. Add interfaces last. CLI and API are thin wrappers — they're only testable end-to-end once
   the agent pipeline works.

---

## Scalability Considerations

| Concern | Now (v1, sequential) | Near-term (asyncio.gather) | Future |
|---------|----------------------|---------------------------|--------|
| Sub-task concurrency | Sequential loop in conductor | `asyncio.gather(*tasks)` with semaphore | Queue-based worker pool |
| Web request concurrency | Semaphore missing (config says max 5, not enforced) | Enforce semaphore in web.py | Rate-limit per domain |
| LLM token cost | One Anthropic client per agent call (no connection pooling) | Shared client singleton | Token budget tracking per investigation |
| Report storage | Filesystem flat files | Add SQLite via aiosqlite (already in deps) | Object storage for multi-user |
| Evidence size | All evidence in memory per investigation | Streaming evidence to disk | Vector store for semantic dedup |

The sequential-first approach in PROJECT.md is correct. Sequential is debuggable; concurrent is
fast. Add `asyncio.gather` for sub-tasks only after the sequential path is solid and tested.

---

## Evidence Integrity Constraints

These are non-negotiable for the project's core value proposition ("no hallucinated evidence"):

1. **No Finding without Evidence.** A Finding with `evidence=[]` must not reach the Reporter.
   The Reporter must skip or flag it, never invent a citation for it.

2. **source_url is mandatory for web-sourced Evidence.** `Evidence.source_url` is currently
   `Optional[str]` in models.py, but web-scraped evidence without a URL is unverifiable. Add
   a Pydantic validator: if `source_type in (WEB_SCRAPE, SEARCH_ENGINE)` then `source_url`
   must be non-None.

3. **LLM must not introduce URLs.** The Reporter's prompt gives it findings + source URLs. If
   it introduces new URLs not in the evidence, those are fabricated. The system prompt should
   explicitly prohibit this, and a post-generation check should verify every URL in the report
   appears in `investigation.findings[*].evidence[*].source_url`.

4. **Confidence must reflect corroboration.** `Confidence.HIGH` should require ≥2 Evidence
   items from different sources. The researcher agent should enforce this in its tool schema.

---

## Sources

- Direct codebase analysis: `sherlock/agents/conductor.py`, `researcher.py`, `reporter.py`
- Direct codebase analysis: `sherlock/models.py`, `sherlock/config.py`, `sherlock/tools/web.py`
- `.planning/codebase/ARCHITECTURE.md` — existing architectural analysis (HIGH confidence)
- `.planning/codebase/CONCERNS.md` — identified implementation gaps (HIGH confidence)
- Anthropic tool_use pattern: training knowledge (MEDIUM confidence — verify against current SDK docs)
- Evidence integrity constraints: derived from PROJECT.md core value proposition (HIGH confidence)
