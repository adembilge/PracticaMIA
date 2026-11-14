"""Human-readable, downloadable PDF from a verified preparation manifest.

No documents, OCR pages, government forms, personal identifiers or LLM text
are embedded. The PDF is generated in memory and is never stored in Neon.
"""
from __future__ import annotations

from html import escape
from io import BytesIO
from unicodedata import normalize

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer,
)

ISSUE_TEXT = {
    "private_document_processing_not_enabled": (
        "Secure document review is not enabled. No attachment validation took place."
    ),
    "document_review_unavailable": "Encrypted document review is unavailable.",
    "no_documents_reviewed": (
        "No private documents were reviewed. Check the current ANPR attachment requirements."
    ),
    "document_needs_extraction": "Uploaded document needs field extraction.",
    "document_needs_user_confirmation": "Uploaded document needs user corrections/confirmation.",
    "document_conflict": "A document conflicts with confirmed case information.",
    "document_needs_manual_review": "Contradictory document content needs manual review.",
    "document_unreadable": "An uploaded document could not be read.",
    "document_no_supported_fields": "No supported labeled values could be extracted.",
    "document_needs_confirmed_intake": "Document needs matching confirmed case information.",
    "document_needs_case_information": "A reviewed field is missing from confirmed case intake.",
    "document_unsupported_category": (
        "An uploaded identity or other supporting document has not been "
        "automatically extracted or validated. Review it yourself."
    ),
    "document_limit_exceeded": "Document count is inconsistent; contact support.",
    "unscanned_document": "A document has no valid malware-scan record.",
}


def _plain(value: object, *, max_chars: int = 600) -> str:
    """Conservatively transliterate for stock PDF fonts and escape XML markup."""
    text = normalize("NFKD", str(value)).encode(
        "ascii", errors="ignore"
    ).decode("ascii")
    return escape(" ".join(text.split())[:max_chars], quote=True)


def render_preparation_pdf(package: dict) -> bytes:
    if package.get("status") != "reviewable_draft" or (
        package.get("download_allowed") is not True
    ) or package.get("official_submission") is not False:
        raise ValueError("Only owner-reviewed draft manifests may be exported")
    if not package.get("confirmed_facts") or len(package.get("checklist", [])) != 5:
        raise ValueError("The signed checklist and confirmed case facts are required")

    document = BytesIO()
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "PMTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=18, leading=22, textColor=colors.HexColor("#173950"),
        spaceAfter=8,
    )
    heading = ParagraphStyle(
        "PMHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=11, leading=14, textColor=colors.HexColor("#173950"),
        spaceBefore=15, spaceAfter=7, keepWithNext=True,
    )
    body = ParagraphStyle(
        "PMBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9, leading=13, spaceAfter=5, splitLongWords=True,
    )
    small = ParagraphStyle(
        "PMSmall", parent=body, fontSize=7.5, leading=10, spaceAfter=4,
    )
    warning = ParagraphStyle(
        "PMWarning", parent=body, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#8D351E"), spaceAfter=8,
    )

    def line(label: str, value: object, style=body):
        story.append(Paragraph(
            f"<b>{_plain(label, max_chars=90)}</b> {_plain(value)}", style
        ))

    story: list = []
    story.append(Paragraph("PracticaMIA | Case preparation draft", title))
    story.append(Paragraph(
        "DEMONSTRATION ONLY - NOT AN OFFICIAL APPLICATION, "
        "SUBMISSION RECEIPT OR ELIGIBILITY DECISION.", warning,
    ))
    line("Case reference:", package["case_reference"])
    line("Generated (UTC):", package["generated_at"])
    line("Procedure:", "Milan change of residence (first reviewed example)")
    line("Ruleset:", package["reviewed_ruleset"])
    story.append(HRFlowable(
        width="100%", thickness=0.6, color=colors.HexColor("#C4D4DB")
    ))

    story.append(Paragraph("1. User-confirmed example facts", heading))
    story.append(Paragraph(
        "These values were entered and confirmed by the user. "
        "PracticaMIA has not checked official registers or identity.", body
    ))
    for fact in package["confirmed_facts"]:
        line(fact["label"] + ":", fact["value"])

    story.append(Paragraph("2. Reviewed source-backed actions", heading))
    story.append(Paragraph(
        "The following English actions are copied from the signed first-route "
        "ruleset. The source record was approved at generation time; "
        "recheck current instructions before acting.", body
    ))
    for i, entry in enumerate(package["checklist"], start=1):
        story.append(Paragraph(
            f"<b>{i}. {_plain(entry['description'], max_chars=900)}</b>", body
        ))
        # Not all evidence is guaranteed current. Never hide archived snapshots.
        for evidence in entry["evidence"]:
            title_label = _plain(evidence["title"], max_chars=160)
            source_url = evidence["official_url"]
            url_attribute = escape(source_url, quote=True)
            prefix = ("Archived ANPR snapshot (may be outdated)"
                      if evidence["archived_reference"] else "Reviewed source")
            story.append(Paragraph(
                f"{_plain(prefix)}: "
                f'<link href="{url_attribute}" color="#17648C">{title_label}</link>'
                f" | Review: {_plain(evidence['reviewed_at'][:10])}"
                f" | Citation: {_plain(evidence['citation_id'], max_chars=90)}",
                small,
            ))
        story.append(Spacer(1, 4))

    story.append(Paragraph("3. Private-document review", heading))
    story.append(Paragraph(
        "This export contains status labels only: no source document, image, "
        "raw OCR, identity number, address or extracted page text.", body
    ))
    if not package["documents"]:
        story.append(Paragraph(
            "No reviewed private-document metadata is included.", body
        ))
    for item in package["documents"]:
        line(f"Document {item['number']} ({item['category']}):",
             item["review_status"])
        for comparison in item["comparisons"]:
            line("Compared field:", f"{comparison['field']} - {comparison['result']}",
                 small)

    story.append(Paragraph("4. Issues and limitations to resolve", heading))
    issues = package["outstanding_issues"]
    if issues:
        for item in issues:
            story.append(Paragraph(
                "- " + _plain(ISSUE_TEXT.get(item, "Manual review is required.")),
                body,
            ))
    else:
        story.append(Paragraph(
            "No issues were detected by the limited example checks. "
            "This does not validate attachments or eligibility.", body
        ))
    story.append(Paragraph(
        "The reviewed catalog does not establish a complete list of mandatory "
        "attachments for an individual applicant. Confirm the current documents "
        "required by the official ANPR service.", warning,
    ))

    story.append(Paragraph("5. User-only official handoff", heading))
    story.append(Paragraph(
        "Verify current requirements on the official websites and submit "
        "your own application. PracticaMIA does not submit anything.", body,
    ))
    for label, url in [
        ("ANPR official website", package["official_handoff"]["anpr_portal"]),
        ("Comune di Milano service", package["official_handoff"]["milan_service"]),
    ]:
        story.append(Paragraph(
            f'<link href="{escape(url, quote=True)}" color="#17648C">'
            f"{_plain(label)}</link>", body,
        ))
    story.append(Paragraph(
        "No government application has been sent, received or accepted. "
        "This document is a synthetic, user-reviewable preparation summary.",
        warning,
    ))

    pdf = SimpleDocTemplate(
        document, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=19 * mm, bottomMargin=19 * mm, pageCompression=1,
        title="PracticaMIA - Draft case preparation",
        author="PracticaMIA",
        subject="Non-official first-scenario preparation draft",
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#5A6971"))
        canvas.drawString(20 * mm, 12 * mm, "DRAFT - NOT SUBMITTED")
        canvas.drawRightString(
            A4[0] - 20 * mm, 12 * mm, f"Page {doc.page}"
        )
        canvas.restoreState()

    pdf.build(story, onFirstPage=footer, onLaterPages=footer)
    payload = document.getvalue()
    if not payload.startswith(b"%PDF-") or len(payload) > 1_000_000:
        raise ValueError("Export size or integrity check failed")
    return payload
