# 🔍 Sherlock Holmes AI

**AI-powered research and investigation agent.** Give it a question, wake up to a sourced report.

Sherlock takes a research query, breaks it into sub-tasks, autonomously gathers evidence from the web and documents, analyzes findings, and produces a structured Markdown report with full source attribution. Every claim cites its source. No hallucinated evidence.

## How It Works

```
You → "Who are the top 5 players in the AI code editor market and how do they compare?"
                                    ↓
                        🎯 Conductor Agent
                     (breaks into sub-tasks)
                    ↓           ↓           ↓
              🔎 Researcher  🔎 Researcher  🔎 Researcher
              (web + OSINT)  (documents)    (competitive)
                    ↓           ↓           ↓
                        📊 Analyst Agent
                     (synthesize findings)
                                ↓
                        📝 Reporter Agent
                    (structured MD report)
                                ↓
              sherlock/outputs/20260311_ai_code_editor_market.md
                                ↓
                        📱 Telegram Notification
                    ("Investigation complete — 12 findings")
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/yourusername/sherlock-holmes-ai.git
cd sherlock-holmes-ai

# 2. Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies
uv sync

# 4. Set your API key
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# 5. Run an investigation
uv run sherlock investigate "What are the leading open-source AI agent frameworks and how do they compare?"
```

## Commands

```bash
# Run an investigation
uv run sherlock investigate "your research question"

# Run with verbose output
uv run sherlock investigate "your question" -v

# Start the web viewer
uv run sherlock serve

# List saved reports
uv run sherlock reports
```

## Investigation Types

| Type | What It Does |
|------|-------------|
| **OSINT** | Web scraping, public records, open-source intelligence gathering |
| **Document Analysis** | Parse PDFs/DOCX, extract key information, cross-reference |
| **Competitive Intel** | Market positioning, product comparison, pricing analysis |
| **Legal/Regulatory** | Statute lookup, compliance research, regulatory tracking |
| **General Research** | Broad topic research with multi-source synthesis |

The conductor agent automatically classifies your query and routes to the right investigation type.

## Architecture

```
sherlock/
├── agents/
│   ├── conductor.py     # Orchestrator — plans the investigation
│   ├── researcher.py    # Gathers evidence from web + docs
│   └── reporter.py      # Generates the final report
├── tools/
│   ├── web.py           # Search + scrape with caching
│   ├── documents.py     # PDF/DOCX parsing
│   └── telegram.py      # Telegram bot — notifications + kick off investigations
├── models.py            # Pydantic data models
├── config.py            # Settings (env-driven)
├── cli.py               # Typer CLI
└── api.py               # FastAPI + report viewer
```

**Three agents, clear separation of concerns:**

- **Conductor** breaks a query into 2–5 actionable sub-tasks
- **Researcher** executes each sub-task: search → scrape → analyze → findings
- **Reporter** synthesizes all findings into a sourced Markdown report

## Telegram Integration

Sherlock can notify you via Telegram as investigations progress, and you can kick off new investigations by messaging the bot directly.

**Setup:**

1. Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → get your bot token
2. Message your new bot, then get your chat ID (send `/start` to the bot, then visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`)
3. Add to your `.env`:

```bash
SHERLOCK_TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
SHERLOCK_TELEGRAM_CHAT_ID=your_chat_id
```

**What you get:**

- 📨 **Progress updates** — notified when investigation starts, each sub-task completes, and final report is ready
- 🔍 **Message to investigate** — send any message to the bot and Sherlock kicks off an investigation on it
- 📎 **Report delivery** — final Markdown report sent directly to your Telegram chat

**Commands:**

```bash
# Start the Telegram bot (runs alongside investigations)
uv run sherlock telegram

# Run investigation with Telegram notifications
uv run sherlock investigate "your question" --notify
```

## Report Viewer

Start the web viewer to browse investigation reports:

```bash
uv run sherlock serve
# Open http://localhost:8000
```

Minimal dark-mode UI that renders your Markdown reports with clickable source links.

## Design Principles

1. **Source everything.** Every claim traces to a URL or document. If it can't be sourced, it gets flagged.
2. **Fail gracefully.** If a scrape fails or an API errors out, the agent continues with available evidence.
3. **Cache aggressively.** Web requests cache in `.sherlock_cache/` to avoid redundant fetches and save API costs.
4. **Structured data.** All outputs flow through Pydantic models. No loose dicts.
5. **Async by default.** All I/O (web, LLM, files) is async for performance.

## Development

```bash
# Install with dev dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/ -v

# Lint + format
uv run ruff check --fix sherlock/
uv run ruff format sherlock/

# Type check
uv run mypy sherlock/
```

## Roadmap

- [x] Telegram bot integration (notifications + message-to-investigate)
- [ ] Analyst agent (deeper cross-referencing and synthesis pass)
- [ ] Multi-document investigation mode (upload a folder of PDFs)
- [ ] Investigation history via SQLite
- [ ] Concurrent sub-task execution
- [ ] Brave Search / SerpAPI integration for better search results
- [ ] Export to PDF/DOCX
- [ ] MCP server for integration with Claude Desktop
- [ ] Telegram inline report preview

## License

MIT
