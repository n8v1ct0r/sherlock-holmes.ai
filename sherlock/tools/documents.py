"""Document tools — parse PDFs and DOCX files into text."""

from __future__ import annotations

from pathlib import Path

from sherlock.models import Evidence, EvidenceSource


async def parse_pdf(file_path: str | Path) -> list[Evidence]:
    """Extract text from a PDF and return as evidence chunks."""
    import fitz  # pymupdf

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    evidence: list[Evidence] = []
    doc = fitz.open(str(path))

    for page_num, page in enumerate(doc, 1):
        text = page.get_text().strip()
        if text:
            evidence.append(
                Evidence(
                    source_type=EvidenceSource.DOCUMENT,
                    source_title=f"{path.name} — Page {page_num}",
                    content=text[:3000],  # Cap per page
                    metadata={"file": str(path), "page": str(page_num)},
                )
            )

    doc.close()
    return evidence


async def parse_docx(file_path: str | Path) -> list[Evidence]:
    """Extract text from a DOCX and return as evidence."""
    from docx import Document

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX not found: {path}")

    doc = Document(str(path))
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    return [
        Evidence(
            source_type=EvidenceSource.DOCUMENT,
            source_title=path.name,
            content=full_text[:10000],
            metadata={"file": str(path)},
        )
    ]
