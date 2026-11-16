"""Human-readable, downloadable PDF from a verified preparation manifest.

No documents, OCR pages, government forms, personal identifiers or LLM text
are embedded. The PDF is generated in memory and is never stored in Neon.
"""
from __future__ import annotations

from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer,
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
    """Escape markup while preserving Italian accents in the built-in fonts."""
    return escape(" ".join(str(value).split())[:max_chars], quote=True)


_IT_ACTIONS = {
    "italian_change_anpr_guidance": "Avvisa l'anagrafe di Milano tramite ANPR entro 20 giorni dal trasferimento. Verifica il canale ufficiale applicabile prima dell'invio.",
    "italian_change_tari_followup": "Verifica separatamente la dichiarazione TARI per la nuova situazione abitativa.",
    "registered_rental_anpr_fields": "Per la locazione registrata (titolo 2), prepara il comune della sede di registrazione, la data del contratto e il numero di registrazione. Verifica i campi nel modulo ANPR attuale.",
    "tenant_attachments_reference_only": "La guida ANPR consultata descrive gli allegati di supporto come generalmente facoltativi per questo caso. Tieni disponibili il contratto e la prova di registrazione se richiesti dal modulo attuale o dal Comune.",
    "applicant_only_anpr_handoff": "Verifica i dati nel servizio ANPR attuale e invia personalmente la dichiarazione.",
}
_IT_FACTS = {
    "citizenship_class": ("Cittadinanza", "Italiana"),
    "registration_context": ("Residenza precedente", "Già registrata in Italia"),
    "destination_municipality": ("Comune di destinazione", "Milano"),
    "household_scope": ("Situazione familiare", "Una persona, senza aggregazione"),
    "housing_basis": ("Titolo di occupazione", "Locazione privata registrata"),
    "move_in_date": ("Data di trasferimento indicata dall'utente", None),
}
_IT_ISSUES = {
    "private_document_processing_not_enabled": "Revisione sicura dei documenti non disponibile.",
    "no_documents_reviewed": "Nessun documento privato è stato esaminato.",
    "document_unsupported_category": "Un documento di identità o di supporto non è stato esaminato automaticamente. Verificalo prima di usarlo.",
}
_IT_DOCUMENT_TERMS = {
    "housing_document": "Documento relativo all'alloggio",
    "identity_document": "Documento di identità",
    "other_supporting_document": "Altro documento di supporto",
    "user_reviewed_unverified": "Esaminato dall'utente",
    "unsupported_category": "Categoria senza estrazione automatica",
    "housing_basis": "Titolo di occupazione",
    "move_in_date": "Data di trasferimento",
    "match": "Corrispondente",
}


def render_preparation_pdf(package: dict, *, lang: str = "en") -> bytes:
    if package.get("status") != "reviewable_draft" or (
        package.get("download_allowed") is not True
    ) or package.get("official_submission") is not False:
        raise ValueError("Only owner-reviewed draft manifests may be exported")
    if not package.get("confirmed_facts") or len(package.get("checklist", [])) != 5:
        raise ValueError("The signed checklist and confirmed case facts are required")

    italian = lang == "it"

    def tr(en: str, it: str) -> str:
        return it if italian else en

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

    def paragraph(value: str, style=body):
        story.append(Paragraph(_plain(value, max_chars=900), style))

    def linked(label: str, url: str, style=body, *, details: str = ""):
        story.append(Paragraph(
            f'<link href="{escape(url, quote=True)}" color="#17648C">{_plain(label)}</link>'
            + (f" | {_plain(details)}" if details else ""), style,
        ))

    draft_title = tr("Case preparation draft", "Bozza di preparazione della pratica")
    paragraph(f"PracticaMIA | {draft_title}", title)
    paragraph(tr(
        "DEMONSTRATION ONLY - NOT AN OFFICIAL APPLICATION, SUBMISSION RECEIPT OR ELIGIBILITY DECISION.",
        "SOLO DIMOSTRAZIONE - NON È UNA DOMANDA UFFICIALE, UNA RICEVUTA O UNA VERIFICA DEI REQUISITI.",
    ), warning)
    line(tr("Case reference:", "Riferimento pratica:"), package["case_reference"])
    line(tr("Generated (UTC):", "Generato (UTC):"), package["generated_at"])
    line(tr("Procedure:", "Procedura:"), tr(
        "Milan change of residence (first reviewed example)",
        "Cambio di residenza a Milano (primo caso esaminato)",
    ))
    line(tr("Ruleset:", "Versione delle regole:"), package["reviewed_ruleset"])
    story.append(HRFlowable(
        width="100%", thickness=0.6, color=colors.HexColor("#C4D4DB")
    ))

    paragraph(tr("1. User-confirmed example facts", "1. Dati di esempio confermati dall'utente"), heading)
    paragraph(tr(
        "The user confirmed these values. PracticaMIA has not checked official registers or identity.",
        "L'utente ha confermato questi dati. PracticaMIA non ha consultato i registri ufficiali né verificato l'identità.",
    ))
    for fact in package["confirmed_facts"]:
        label, value = _IT_FACTS[fact["field"]] if italian else (fact["label"], None)
        line(label + ":", value or fact["value"])

    paragraph(tr("2. Reviewed source-backed actions", "2. Azioni basate sulle fonti esaminate"), heading)
    paragraph(tr(
        "The actions come from the signed ruleset. Recheck the current instructions before acting.",
        "Le azioni sono tradotte dalle regole firmate. Verifica le istruzioni attuali prima di procedere.",
    ))
    for i, entry in enumerate(package["checklist"], start=1):
        description = _IT_ACTIONS[entry["id"]] if italian else entry["description"]
        story.append(Paragraph(f"<b>{i}. {_plain(description, max_chars=900)}</b>", body))
        for evidence in entry["evidence"]:
            prefix = tr("Archived ANPR snapshot", "Versione ANPR archiviata") if evidence["archived_reference"] else tr(
                "Reviewed source", "Fonte esaminata",
            )
            reviewed = tr("Review", "Revisione")
            citation = tr("Citation", "Riferimento")
            linked(f"{prefix}: {evidence['title']}", evidence["official_url"], small, details=(
                f"{reviewed}: {evidence['reviewed_at'][:10]} | {citation}: {evidence['citation_id']}"
            ))
        story.append(Spacer(1, 4))

    worksheet = package.get("anpr_worksheet")
    if worksheet:
        paragraph(tr("3. What to prepare for ANPR", "3. Dati da preparare per ANPR"), heading)
        paragraph(worksheet["section"])
        for field in worksheet["fields"]:
            line(field["portal_label"] + ":", field["label_it" if italian else "label_en"])
        paragraph(tr(
            "Find these values in your records. Verify the fields, applicable attachments and upload limits in the current ANPR form.",
            "Recupera questi dati dai tuoi documenti. Controlla i campi, gli allegati applicabili e i limiti di caricamento nel modulo ANPR attuale.",
        ))
        linked(tr("Archived ANPR guide, p. 12", "Guida ANPR archiviata, p. 12"),
               worksheet["source"]["official_url"], small)

    paragraph(tr("Private-document review", "Revisione dei documenti privati"), heading)
    paragraph(tr(
        "This export contains review status only. Original files, OCR text, addresses and identity numbers are excluded.",
        "La bozza riporta solo lo stato della revisione. File originali, testo OCR, indirizzi e numeri identificativi sono esclusi.",
    ))
    if not package["documents"]:
        paragraph(tr("No reviewed private-document metadata is included.", "Nessun dato di revisione incluso."))
    for item in package["documents"]:
        category, status = item["category"], item["review_status"]
        if italian:
            category = _IT_DOCUMENT_TERMS[category]
            status = _IT_DOCUMENT_TERMS[status]
        line(f"{tr('Document', 'Documento')} {item['number']} ({category}):", status)
        for comparison in item["comparisons"]:
            field, result = comparison["field"], comparison["result"]
            if italian:
                field, result = _IT_DOCUMENT_TERMS[field], _IT_DOCUMENT_TERMS[result]
            line(tr("Compared field:", "Campo confrontato:"), f"{field} - {result}", small)

    paragraph(tr("Issues and limitations to resolve", "Controlli da completare"), heading)
    for issue in package["outstanding_issues"]:
        messages = _IT_ISSUES if italian else ISSUE_TEXT
        paragraph("- " + messages.get(issue, tr("Manual review is required.", "Verifica manuale necessaria.")))
    paragraph(tr(
        "Confirm the applicable attachments and limits in the current ANPR form.",
        "Controlla gli allegati applicabili e i limiti di caricamento nel modulo ANPR attuale.",
    ), warning)

    paragraph(tr("User-only official handoff", "Prosegui sul portale ufficiale"), heading)
    paragraph(tr(
        "Verify the current requirements on the official websites. Review the declaration in ANPR and submit it yourself.",
        "Verifica i requisiti attuali sui siti ufficiali. Controlla la dichiarazione in ANPR e inviala personalmente.",
    ))
    linked(tr("ANPR official website", "Sito ufficiale ANPR"), package["official_handoff"]["anpr_portal"])
    linked(tr("Comune di Milano service", "Servizio del Comune di Milano"), package["official_handoff"]["milan_service"])
    paragraph(tr(
        "No government application has been sent, received or accepted.",
        "Nessuna domanda è stata inviata, ricevuta o accettata.",
    ), warning)

    pdf = SimpleDocTemplate(
        document, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=19 * mm, bottomMargin=19 * mm, pageCompression=1,
        title=f"PracticaMIA - {draft_title}",
        author="PracticaMIA",
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#5A6975"))
        canvas.drawString(20 * mm, 12 * mm, tr("DRAFT - NOT SUBMITTED", "BOZZA - NON INVIATA"))
        canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"{tr('Page', 'Pagina')} {doc.page}")
        canvas.restoreState()

    pdf.build(story, onFirstPage=footer, onLaterPages=footer)
    payload = document.getvalue()
    if not payload.startswith(b"%PDF-") or len(payload) > 1_000_000:
        raise ValueError("Export size or integrity check failed")
    return payload
