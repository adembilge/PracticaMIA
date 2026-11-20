"""Fixed Phase 4 originals for the isolated source review catalogue."""

from dataclasses import dataclass
from datetime import datetime
from app.knowledge.html_extraction import EXTRACTION_VERSION, VOID_AWARE_EXTRACTION_VERSION


# SQLite file discriminator for this standalone catalogue.
PILOT_REVIEW_APPLICATION_ID = 0x504D4952


@dataclass(frozen=True)
class PilotSource:
    institution: str
    jurisdiction: str
    procedure_id: str
    title: str
    official_url: str
    content_sha256: str
    retrieved_at: datetime
    extraction_version: str = EXTRACTION_VERSION

    def registry_fields(self, source_id: str) -> dict[str, str]:
        return {
            "id": source_id,
            "institution": self.institution,
            "jurisdiction": self.jurisdiction,
            "procedure_id": self.procedure_id,
            "language": "it",
            "title": self.title,
            "official_url": self.official_url,
            "document_type": "service_page",
        }


POSTAL_APPOINTMENT_SOURCE_ID = "poste-residence-permit-appointments"


PILOT_SOURCES = {
    "torino-banns-office": PilotSource(
        "Città di Torino", "IT-TO-TORINO", "marriage_banns", "Ufficio pubblicazioni di matrimonio",
        "https://www.comune.torino.it/amministrazione/ufficio-pubblicazioni-matrimonio-0",
        "e7fdc3626542170333ae6aeafbf08fc8f2ed8a3eaccaef6a0756683312d0d8c3",
        datetime.fromisoformat("2026-11-20T14:27:38+00:00"),
    ),
    "torino-banns-service": PilotSource(
        "Città di Torino", "IT-TO-TORINO", "marriage_banns", "Richiedere le pubblicazioni di matrimonio",
        "https://www.comune.torino.it/servizi/richiedere-pubblicazioni-matrimonio",
        "c57e3b219288b77fb5f7af63c74b005cb471b1538423af1dea04f179282537d4",
        datetime.fromisoformat("2026-11-20T14:27:37+00:00"),
    ),
    "portale-immigrazione-code-16": PilotSource(
        "Portale Immigrazione", "IT", "residence_permit_renewal",
        "Codice 16 - Permesso di Soggiorno per Lavoro Subordinato",
        "https://www.portaleimmigrazione.it/ITA/lavoroSubordinato.html",
        "02bb7a627c0e3836d87b65c9f76b798bac5c8cd813a88659c3208ea381c1975e",
        datetime.fromisoformat("2026-11-20T14:27:33+00:00"),
    ),
    "portale-immigrazione-procedure": PilotSource(
        "Portale Immigrazione", "IT", "residence_permit_renewal", "La Procedura",
        "https://www.portaleimmigrazione.it/ITA/nuovaProcedura.html",
        "6c4715686b3d89f641c91fa302308a2f374f87a611ebd1b8c2f3e2fbe97be6f1",
        datetime.fromisoformat("2026-11-20T14:27:33+00:00"),
    ),
    POSTAL_APPOINTMENT_SOURCE_ID: PilotSource(
        "Poste Italiane", "IT", "residence_permit_renewal", "Permessi di soggiorno",
        "https://www.poste.it/guida-rilascio-e-rinnovo-permesso-di-soggiorno/",
        "73f54fe10c5b18f207b3da0271f83216a92b8591e5e2e9540688d39929080a5f",
        datetime.fromisoformat("2026-11-20T15:32:03+00:00"),
        extraction_version=VOID_AWARE_EXTRACTION_VERSION,
    ),
}

# Every claim points to the exact original passages from the acquisition record.
PILOT_CLAIM_PASSAGES = {
    "T1": (
        ("torino-banns-office", 9, "0a37ae3b0e8be8a02574f6f55450d6f9b89eed993efc1f61b62a0b959fc1acd4"),
        ("torino-banns-service", 11, "067ab354e26f0e48a9831213af153236754a4c8dc5cba4a57b75b72ba31d9020"),
        ("torino-banns-service", 12, "4759a9ca53a8689520008ea0c65e89687530b495e8b51500b186a49ffc3edd89"),
    ),
    "T2": (
        ("torino-banns-service", 17, "ca0a35937a0ccae67a3a2ac4b49e8561ad3f245256f894faf6a8dbc9438a0761"),
    ),
    "T3": (
        ("torino-banns-service", 14, "862afa54f370ce5bed4bf877be118b8bcd51475900f0e59968e73a8fcf879621"),
        ("torino-banns-service", 15, "0965848e11327d68d6f3933d5b773460a0c0b32f9aff8172cb61df8e4d2a99d2"),
    ),
    "Q1": (
        ("portale-immigrazione-code-16", 3, "d4f618deccae2e9a8e86cd6a7c79ec3e5cfbd38a3b604320c62ca3a53dfecd01"),
        ("portale-immigrazione-code-16", 5, "b9be6dc48a32161f6f7a26fb19a1385e76fcd9991a9fa01e99b3296899438c23"),
    ),
    "Q2": (
        ("portale-immigrazione-procedure", 35, "1fef9aa6247abf32b2d36dadf3087ab988c56a4e46f2824b9a535cd4c90af9c3"),
    ),
    "Q3": (
        (POSTAL_APPOINTMENT_SOURCE_ID, 80, "76c14f96a6bee582a67585cbbca1eac595b892479d6dfd321d401f83394b15f9"),
        (POSTAL_APPOINTMENT_SOURCE_ID, 81, "8afcbde4d26364599ac5a36f1b0ab9d88232c1ec86ca59c27af930e7bfec5950"),
    ),
}
