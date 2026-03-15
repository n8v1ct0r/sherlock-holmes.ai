# Feature Landscape

**Domain:** Autonomous AI research agents (CLI + bot + API)
**Researched:** 2026-03-15
**Confidence Note:** Web and search tools were unavailable during this research session. All findings are drawn from training knowledge (cutoff August 2025) of Perplexity, GPT Researcher, Tavily, AutoGPT research mode, You.com Research, and Exa.ai. Confidence levels reflect this constraint.

---

## Table Stakes

Features users expect from any AI research agent. Missing one of these and users treat the product as a toy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Natural language query input | Every competitor supports free-form questions | Low | Already planned |
| Multi-source web search | Perplexity, GPT Researcher, Tavily all do this | Low-Med | DDG + Brave covers this |
| Real-time web scraping (not static index) | Users expect fresh data, not stale embeddings | Med | Crawl4AI handles JS-rendered pages |
| Inline source citations in output | Core trust mechanic — without citations, users distrust results | Med | Sherlock's core principle; every claim needs a URL |
| Graceful failure on unreachable sources | Flaky scrapers that crash the whole run kill trust fast | Low | Already in scope (log + skip) |
| Structured Markdown report output | Standard format; readable in any viewer | Low | Already planned |
| Progress feedback during long runs | Research takes 30-90s; silent runs feel broken | Low-Med | Rich CLI spinners + Telegram progress already planned |
| Query decomposition into sub-tasks | Single-query → single-search is too shallow; users expect depth | Med | Conductor agent already planned |
| Deduplication of sources | Citing the same URL three times erodes trust | Low | Must deduplicate by URL before report generation |
| Handling of paywalled/blocked pages | Common — NYT, Bloomberg, academic journals block scrapers | Med | Log as "blocked", continue; note in report |

---

## Differentiators

Features that separate a research agent from a search engine wrapper. Not universally expected, but create strong user preference when present.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Evidence chain transparency | Show *why* each claim was included, not just what it says — lets user audit the reasoning | High | GPT Researcher does shallow version; Sherlock can do deeper traceability via Pydantic Finding → Source chain |
| Conflict detection across sources | Flag when Source A says X and Source B says Y — adds genuine analytical value | High | Most agents ignore contradictions; this is a strong differentiator |
| Confidence scoring per finding | "HIGH / MEDIUM / LOW" on each synthesized claim based on source count and quality | Med | Uncommon in OSS agents; Perplexity does a partial version |
| Telegram-native investigation flow | Message → acknowledged → plan shared → per-subtask updates → report link | Med | Unique interaction model; most agents are web-only |
| Document ingestion (PDF/DOCX) | Research over uploaded files, not just the web | Med | pymupdf + python-docx already planned; enables "investigate this contract" use cases |
| Investigation memory / history | Retrieve past investigations, build on prior findings | Med | Deferred to v2 (SQLite); but the file-based outputs already partially solve this |
| Iterative follow-up questions | Ask a follow-up that scopes into a prior report's findings | High | Not planned for v1; requires session context |
| Domain-scoped investigation | "Only search .gov and .edu sources" or "Only look at Reddit + HN" | Med | Source filtering at the search level; useful for OSINT |
| Confidence-based source ranking | Prefer peer-reviewed / gov / primary sources over SEO blogs | High | Requires source quality heuristics; rare in OSS agents |
| Export formats beyond Markdown | JSON (for programmatic use), HTML (for sharing), PDF | Med | JSON is high value for downstream automation; HTML via FastAPI viewer partially covers this |
| Failure audit log in report | Report includes a section: "These sources were tried but failed" | Low | Builds trust; unusual but easy to add |
| Configurable research depth | "Quick (3 sources)" vs "Deep (15 sources, 2 rounds)" | Low | Single param; GPT Researcher has this |
| Named entity extraction | Pull companies, people, locations as structured data from findings | High | Adds machine-readable value on top of prose |
| Parallelized sub-task execution | Run 5 sub-task searches concurrently → 5x faster | Med | Sequential first (already scoped); asyncio.gather for v2 |

---

## Anti-Features

Things that seem like features but actively harm the product. Build these and Sherlock becomes worse.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Hallucinated citations | The #1 trust killer for AI research tools; Perplexity has been publicly caught doing this | Require every claim to trace to a fetched URL; if no source, say "not found" |
| Answer without sources shown | Hides the evidence chain; users can't verify | Always render citations inline, not just in a bibliography |
| Overlong reports with padding | GPT Researcher often produces 5000-word walls of text that bury the actual findings | Cap reports at ~1500 words unless depth mode; lead with summary |
| Silent failure on tool errors | Crashing or silently skipping without telling the user destroys trust | Log every failure explicitly; note in report which sources were unreachable |
| Treating all sources as equal | An SEO spam blog and a government report are not equivalent | Flag source type (news / academic / blog / official) even if scoring is simple |
| Real-time streaming with no caching | Re-fetching the same URLs on every run wastes money and time | Cache all scrapes by URL hash; already planned |
| Multi-LLM switching | Supporting OpenAI + Anthropic + local models adds complexity with no user benefit for this project | Anthropic-only; the constraint is an asset (consistent behavior, one API surface) |
| Auth-gated report viewer in v1 | Adds friction before the core loop is validated | Local-only access; no auth until there's a reason to expose publicly |
| Recursive agent loops without budget | AutoGPT-style infinite loops that run up API costs and never terminate | Hard cap: max N sub-tasks, max M pages per sub-task, hard timeout |
| Social/sharing features | Out of scope for a research tool; adds no investigative value | File-based reports are the sharing mechanism |

---

## Feature Dependencies

```
Query input
  → Query decomposition (Conductor)
    → Search execution per sub-task (Researcher)
      → Web scraping per search result
        → Content extraction + deduplication
          → Evidence synthesis (Analyst)
            → Source citation linking
              → Report generation (Reporter)
                → CLI output
                → Telegram notification
                → FastAPI report viewer

Document ingestion (PDF/DOCX)
  → Content extraction
    → Evidence synthesis (same path as web findings above)

Conflict detection
  → Requires: Evidence synthesis complete
  → Requires: Multiple sources per claim

Confidence scoring
  → Requires: Source count per finding
  → Requires: Source type classification (basic)

Investigation history / memory
  → Requires: Database (SQLite) — deferred to v2
  → File-based reports partially fulfill this

Parallel sub-task execution
  → Requires: Sequential version working and tested first
```

---

## MVP Recommendation

Prioritize for v1 (already largely reflected in PROJECT.md):

1. **Query decomposition → parallel web search → scrape → structured findings** — the core evidence-gathering pipeline
2. **Inline citations in every report** — the non-negotiable trust mechanic
3. **Failure audit section in reports** — "Tried but failed" list; low complexity, high trust signal
4. **Telegram bot end-to-end** — validates the full pipeline; primary interaction mode
5. **Configurable research depth** — `--depth quick|standard|deep`; low complexity, immediately useful

Defer from v1:

| Feature | Reason to Defer |
|---------|----------------|
| Conflict detection | Requires solid evidence model first; add in v2 |
| Confidence scoring | Needs source quality heuristics; v2 |
| Parallel sub-task execution | Sequential is faster to debug; asyncio.gather in v2 |
| Named entity extraction | High complexity, niche use case for v1 |
| Investigation history (SQLite) | Already scoped out; file reports are sufficient |
| Iterative follow-up questions | Requires session context; v2 |

---

## Competitive Benchmarks

| Competitor | Key Strength | Key Weakness | Sherlock Differential |
|------------|-------------|--------------|----------------------|
| Perplexity AI | Polished UX, fast, great citations | Closed source, web-only, no document ingestion | Open source, CLI/Telegram, document support |
| GPT Researcher (OSS) | Proven architecture, many integrations | Verbose output, OpenAI-dependent, no Telegram | Claude-native, evidence chain traceability, Telegram-first |
| Tavily | Excellent search API quality | API-only (no end-user product), no synthesis | Full investigation pipeline, not just retrieval |
| AutoGPT research mode | Flexible agent loop | Unpredictable, expensive, often loops forever | Bounded execution: hard cap on sub-tasks and depth |
| You.com Research | Good for structured outputs | Web-only, closed, no programmatic access | File-based + API outputs for automation |

**Confidence:** MEDIUM — based on training data through August 2025. Perplexity and GPT Researcher feature sets well-documented; Tavily and AutoGPT research mode less thoroughly verified.

---

## Sources

- Training knowledge of GPT Researcher (github.com/assafelovic/gpt-researcher) through August 2025 — MEDIUM confidence
- Training knowledge of Perplexity AI product features through August 2025 — MEDIUM confidence
- Training knowledge of Tavily API documentation through August 2025 — MEDIUM confidence
- Training knowledge of AutoGPT architecture through August 2025 — LOW-MEDIUM confidence
- PROJECT.md: feature requirements already validated by project owner — HIGH confidence
- CLAUDE.md: architectural constraints (evidence policy, async, Pydantic) — HIGH confidence

**Note:** Web search was unavailable during this research session. Findings should be validated against current GPT Researcher README and Perplexity changelog before roadmap finalization.
