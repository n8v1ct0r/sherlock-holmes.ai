"""Researcher agent — gathers evidence from web sources for a given sub-task."""

from __future__ import annotations

import json

import anthropic

from sherlock.config import settings
from sherlock.models import Confidence, Evidence, EvidenceSource, Finding
from sherlock.tools.web import scrape_url, search_web

RESEARCHER_SYSTEM = """You are a meticulous research agent. Given a research task:

1. Determine 2-3 search queries that would surface relevant evidence
2. Analyze the search results and identify key findings
3. Rate your confidence in each finding

Respond ONLY with valid JSON:
{
  "search_queries": ["query 1", "query 2"],
  "analysis": "Your synthesis of what you found",
  "findings": [
    {
      "claim": "Specific factual claim",
      "confidence": "high|medium|low|speculative",
      "tags": ["tag1", "tag2"]
    }
  ]
}

RULES:
- Never fabricate information. Only report what the search results actually contain.
- If results are insufficient, say so in the analysis.
- Be specific in claims — avoid vague statements."""


async def execute_research_task(task_description: str) -> list[Finding]:
    """Execute a research sub-task: search, scrape, analyze, return findings."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Step 1: Ask LLM to generate search queries
    plan_response = await client.messages.create(
        model=settings.model,
        max_tokens=1024,
        system=RESEARCHER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Research task: {task_description}\n\nGenerate search queries to investigate this.",
            }
        ],
    )

    raw = plan_response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    plan = json.loads(raw)
    search_queries: list[str] = plan.get("search_queries", [task_description])

    # Step 2: Execute searches and collect evidence
    all_evidence: list[Evidence] = []
    for query in search_queries[:3]:  # Cap at 3 queries
        try:
            results = await search_web(query)
            for result in results[: settings.max_web_results]:
                evidence = Evidence(
                    source_type=EvidenceSource.SEARCH_ENGINE,
                    source_url=result.get("url", ""),
                    source_title=result.get("title", ""),
                    content=result.get("snippet", ""),
                    metadata={"query": query},
                )
                all_evidence.append(evidence)
        except Exception:
            continue  # Fail gracefully, continue with what we have

    # Step 3: Have LLM analyze gathered evidence
    evidence_text = "\n\n".join(
        f"[{e.source_title}]({e.source_url})\n{e.content}" for e in all_evidence
    )

    analysis_response = await client.messages.create(
        model=settings.model,
        max_tokens=2048,
        system=RESEARCHER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Research task: {task_description}\n\n"
                    f"Evidence gathered:\n{evidence_text}\n\n"
                    "Analyze this evidence and produce findings."
                ),
            }
        ],
    )

    raw_analysis = analysis_response.content[0].text.strip()
    if raw_analysis.startswith("```"):
        raw_analysis = raw_analysis.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    analysis = json.loads(raw_analysis)

    # Step 4: Build Finding objects with evidence chain
    findings: list[Finding] = []
    for f in analysis.get("findings", []):
        finding = Finding(
            claim=f["claim"],
            confidence=Confidence(f.get("confidence", "medium")),
            evidence=all_evidence,  # Attach all evidence to each finding for now
            tags=f.get("tags", []),
        )
        findings.append(finding)

    return findings
