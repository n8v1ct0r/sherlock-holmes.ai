"""Tests for Sherlock Holmes AI core models and tools."""

from sherlock.models import (
    Confidence,
    Evidence,
    EvidenceSource,
    Finding,
    Investigation,
    InvestigationType,
    SubTask,
)


def test_evidence_creation():
    e = Evidence(
        source_type=EvidenceSource.WEB_SCRAPE,
        source_url="https://example.com",
        content="Test content",
    )
    assert e.source_url == "https://example.com"
    assert e.confidence == Confidence.MEDIUM  # default


def test_finding_with_evidence():
    evidence = Evidence(
        source_type=EvidenceSource.SEARCH_ENGINE,
        source_url="https://example.com",
        content="Some evidence",
    )
    finding = Finding(
        claim="Test claim",
        evidence=[evidence],
        confidence=Confidence.HIGH,
        tags=["test"],
    )
    assert len(finding.evidence) == 1
    assert finding.confidence == Confidence.HIGH


def test_investigation_lifecycle():
    inv = Investigation(
        query="Test query",
        investigation_type=InvestigationType.GENERAL_RESEARCH,
    )
    assert inv.status == "pending"
    assert inv.completed_at is None
    assert len(inv.sub_tasks) == 0


def test_subtask_creation():
    task = SubTask(
        description="Research competitor pricing",
        agent="researcher",
    )
    assert task.status == "pending"
    assert task.agent == "researcher"
