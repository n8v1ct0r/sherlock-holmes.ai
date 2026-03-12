"""Sherlock Holmes AI — FastAPI server with report viewer."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from sherlock.agents.conductor import execute_investigation, plan_investigation
from sherlock.agents.reporter import generate_report, save_report
from sherlock.config import settings
from sherlock.models import Investigation, InvestigationSummary

app = FastAPI(
    title="Sherlock Holmes AI",
    description="AI-powered research and investigation agent",
    version="0.1.0",
)


@app.post("/investigate", response_model=dict)
async def run_investigation(query: str, notify: bool = False) -> dict:
    """Kick off a new investigation."""
    should_notify = notify and settings.telegram_configured
    investigation = await plan_investigation(query)
    investigation = await execute_investigation(investigation, notify=should_notify)
    markdown = await generate_report(investigation)
    report_path = await save_report(investigation, markdown)
    investigation.report_markdown = markdown
    investigation.report_path = str(report_path)

    if should_notify:
        from sherlock.tools.telegram import notify_investigation_complete
        await notify_investigation_complete(query, len(investigation.findings), report_path)

    return {
        "id": str(investigation.id),
        "query": investigation.query,
        "status": investigation.status,
        "finding_count": len(investigation.findings),
        "report_path": str(report_path),
    }


@app.get("/reports", response_model=list[dict])
async def list_reports() -> list[dict]:
    """List all saved investigation reports."""
    output_dir = settings.output_dir
    if not output_dir.exists():
        return []

    reports = []
    for f in sorted(output_dir.glob("*.md"), reverse=True):
        reports.append(
            {
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "modified": f.stat().st_mtime,
            }
        )
    return reports


@app.get("/reports/{filename}")
async def get_report(filename: str) -> dict:
    """Get a specific report's content."""
    path = settings.output_dir / filename
    if not path.exists() or not path.suffix == ".md":
        raise HTTPException(status_code=404, detail="Report not found")

    return {"filename": filename, "content": path.read_text(encoding="utf-8")}


@app.get("/", response_class=HTMLResponse)
async def viewer() -> str:
    """Minimal report viewer UI."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sherlock Holmes AI</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               background: #0a0a0a; color: #e0e0e0; }
        .container { max-width: 900px; margin: 0 auto; padding: 2rem; }
        h1 { font-size: 1.8rem; margin-bottom: 0.5rem; color: #fff; }
        h1 span { color: #4a9eff; }
        .subtitle { color: #666; margin-bottom: 2rem; font-size: 0.9rem; }
        .report-list { list-style: none; }
        .report-list li { padding: 0.75rem 1rem; border: 1px solid #222;
                          border-radius: 8px; margin-bottom: 0.5rem; cursor: pointer;
                          transition: border-color 0.2s; }
        .report-list li:hover { border-color: #4a9eff; }
        .report-list li .name { font-weight: 600; }
        .report-list li .meta { font-size: 0.8rem; color: #666; }
        #report-content { margin-top: 2rem; padding: 2rem; background: #111;
                          border-radius: 12px; border: 1px solid #222;
                          line-height: 1.7; display: none; }
        #report-content h1, #report-content h2, #report-content h3 {
            color: #fff; margin-top: 1.5rem; margin-bottom: 0.5rem; }
        #report-content a { color: #4a9eff; }
        #report-content ul, #report-content ol { padding-left: 1.5rem; }
        .back-btn { color: #4a9eff; cursor: pointer; margin-bottom: 1rem;
                    display: none; font-size: 0.9rem; }
        .back-btn:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Sherlock Holmes <span>AI</span></h1>
        <p class="subtitle">Investigation reports</p>
        <div class="back-btn" onclick="showList()">← Back to reports</div>
        <ul class="report-list" id="report-list"></ul>
        <div id="report-content"></div>
    </div>
    <script>
        async function loadReports() {
            const res = await fetch('/reports');
            const reports = await res.json();
            const list = document.getElementById('report-list');
            list.innerHTML = reports.map(r => `
                <li onclick="loadReport('${r.filename}')">
                    <div class="name">${r.filename.replace(/^\\d+_/, '').replace('.md', '').replaceAll('_', ' ')}</div>
                    <div class="meta">${(r.size_bytes / 1024).toFixed(1)} KB</div>
                </li>
            `).join('');
        }
        async function loadReport(filename) {
            const res = await fetch(`/reports/${filename}`);
            const data = await res.json();
            document.getElementById('report-content').innerHTML = marked.parse(data.content);
            document.getElementById('report-content').style.display = 'block';
            document.getElementById('report-list').style.display = 'none';
            document.querySelector('.back-btn').style.display = 'block';
        }
        function showList() {
            document.getElementById('report-content').style.display = 'none';
            document.getElementById('report-list').style.display = 'block';
            document.querySelector('.back-btn').style.display = 'none';
        }
        loadReports();
    </script>
</body>
</html>"""
