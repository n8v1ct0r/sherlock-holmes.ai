"""Conductor agent — orchestrates the investigation by breaking queries into sub-tasks."""

from __future__ import annotations

import json
from datetime import datetime

import anthropic

from sherlock.config import settings
from sherlock.models import (
    Evidence,
    EvidenceSource,
    Finding,
    Investigation,
    InvestigationType,
    SubTask,
)


CONDUCTOR_SYSTEM = """You are Sherlock, an AI investigation conductor. Given a research query, you:

1. Classify the investigation type (osint, document_analysis, competitive_intel, legal_regulatory, general_research)
2. Break it into 2-5 discrete, actionable sub-tasks
3. Assign each sub-task to the right agent (researcher, analyst)

Respond ONLY with valid JSON matching this schema:
{
  "investigation_type": "general_research",
  "sub_tasks": [
    {
      "description": "What to investigate",
      "agent": "researcher"
    }
  ]
}

Be specific in sub-task descriptions. Each should be independently actionable."""


async def plan_investigation(query: str) -> Investigation:
    """Take a raw query and produce an investigation plan with sub-tasks."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model=settings.model,
        max_tokens=1024,
        system=CONDUCTOR_SYSTEM,
        messages=[{"role": "user", "content": query}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    plan = json.loads(raw)

    investigation = Investigation(
        query=query,
        investigation_type=InvestigationType(plan["investigation_type"]),
        status="planned",
        sub_tasks=[
            SubTask(description=t["description"], agent=t["agent"]) for t in plan["sub_tasks"]
        ],
    )

    return investigation


async def execute_investigation(investigation: Investigation, notify: bool = False) -> Investigation:
    """Execute all sub-tasks and synthesize findings into a final report."""
    from sherlock.agents.researcher import execute_research_task
    from sherlock.tools.telegram import (
        notify_investigation_started,
        notify_task_completed,
        notify_task_failed,
    )

    investigation.status = "running"

    if notify:
        await notify_investigation_started(investigation.query, len(investigation.sub_tasks))

    for task in investigation.sub_tasks:
        task.status = "running"
        try:
            if task.agent == "researcher":
                findings = await execute_research_task(task.description)
                task.findings = findings
                task.status = "completed"
            else:
                # Default to researcher for now
                findings = await execute_research_task(task.description)
                task.findings = findings
                task.status = "completed"

            if notify:
                await notify_task_completed(task.description, len(task.findings))

        except Exception as e:
            task.status = "failed"
            task.error = str(e)

            if notify:
                await notify_task_failed(task.description, str(e))

    # Collect all findings
    investigation.findings = [f for task in investigation.sub_tasks for f in task.findings]
    investigation.status = "completed"
    investigation.completed_at = datetime.now()

    return investigation
