"""Core data models for Sherlock Holmes AI investigations."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class InvestigationType(str, Enum):
    """Types of investigations Sherlock can conduct."""

    OSINT = "osint"
    DOCUMENT_ANALYSIS = "document_analysis"
    COMPETITIVE_INTEL = "competitive_intel"
    LEGAL_REGULATORY = "legal_regulatory"
    GENERAL_RESEARCH = "general_research"


class EvidenceSource(str, Enum):
    """Where a piece of evidence came from."""

    WEB_SCRAPE = "web_scrape"
    SEARCH_ENGINE = "search_engine"
    DOCUMENT = "document"
    API = "api"
    USER_PROVIDED = "user_provided"


class Confidence(str, Enum):
    """Confidence level in a finding."""

    HIGH = "high"  # Multiple corroborating sources
    MEDIUM = "medium"  # Single reliable source
    LOW = "low"  # Unverified or single weak source
    SPECULATIVE = "speculative"  # Inferred, not directly evidenced


class Evidence(BaseModel):
    """A single piece of evidence with full provenance."""

    id: UUID = Field(default_factory=uuid4)
    source_type: EvidenceSource
    source_url: str | None = None
    source_title: str | None = None
    content: str
    retrieved_at: datetime = Field(default_factory=datetime.now)
    confidence: Confidence = Confidence.MEDIUM
    metadata: dict[str, str] = Field(default_factory=dict)


class Finding(BaseModel):
    """An analytical finding backed by evidence."""

    id: UUID = Field(default_factory=uuid4)
    claim: str
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    tags: list[str] = Field(default_factory=list)


class SubTask(BaseModel):
    """A discrete research sub-task assigned by the conductor."""

    id: UUID = Field(default_factory=uuid4)
    description: str
    agent: str  # Which agent handles this: researcher, analyst, etc.
    status: str = "pending"  # pending, running, completed, failed
    findings: list[Finding] = Field(default_factory=list)
    error: str | None = None


class Investigation(BaseModel):
    """A complete investigation from query to report."""

    id: UUID = Field(default_factory=uuid4)
    query: str
    investigation_type: InvestigationType = InvestigationType.GENERAL_RESEARCH
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    status: str = "pending"  # pending, running, completed, failed
    sub_tasks: list[SubTask] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    report_markdown: str | None = None
    report_path: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class InvestigationSummary(BaseModel):
    """Lightweight summary for listing investigations."""

    id: UUID
    query: str
    investigation_type: InvestigationType
    created_at: datetime
    status: str
    finding_count: int
    report_path: str | None = None
