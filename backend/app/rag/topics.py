from pydantic import BaseModel

from ingest.models import TOPICS as INGEST_TOPICS

_TOPIC_ORDER = (
    "immigrazione",
    "cittadinanza",
    "anagrafe",
    "identita_digitale",
    "lavoro_previdenza",
    "fisco",
    "sanita",
    "giustizia",
    "famiglia",
    "impresa",
    "istruzione",
    "mobilita",
    "casa",
)


class TopicProfile(BaseModel):
    topic: str
    description: str
    portal_url: str
    portal_name: str


_PROFILE_DATA: dict[str, dict[str, str]] = {
    "immigrazione": {
        "description": (
            "Permesso di soggiorno, rinnovo, visto, ricongiungimento familiare, asilo, questura e kit postale. "
            "Residence permit, renewal, visa, family reunification and asylum."
        ),
        "portal_url": "https://www.poliziadistato.it/articolo/225",
        "portal_name": "Polizia di Stato",
    },
    "cittadinanza": {
        "description": (
            "Cittadinanza per residenza, matrimonio o discendenza, domanda online, contributo e requisito B1. "
            "Citizenship by residence, marriage or descent."
        ),
        "portal_url": "https://libertaciviliimmigrazione.dlci.interno.gov.it/cittadinanza-invia-la-tua-domanda",
        "portal_name": "Ministero dell'Interno",
    },
    "anagrafe": {
        "description": (
            "Cambio di residenza, iscrizione anagrafica, stato di famiglia, certificati e autocertificazione. "
            "Address change, civil registry and self-certification. "
            "Documenti per la registrazione della residenza dei cittadini non UE. "
            "Residency registration documents for a non-EU citizen."
        ),
        "portal_url": "https://www.anagrafenazionale.interno.it/area-cittadino/",
        "portal_name": "ANPR",
    },
    "identita_digitale": {
        "description": (
            "SPID, CIE, PIN, PUK e identità digitale. Digital identity to enter public services."
        ),
        "portal_url": "https://www.spid.gov.it/",
        "portal_name": "SPID",
    },
    "lavoro_previdenza": {
        "description": (
            "NASpI, contributi, disoccupazione, pensione, INPS, INAIL e infortunio sul lavoro. "
            "Unemployment benefit, contributions, pension and workplace injury."
        ),
        "portal_url": "https://www.inps.it/",
        "portal_name": "INPS",
    },
    "fisco": {
        "description": (
            "Codice fiscale, dichiarazione dei redditi, IMU e Agenzia delle Entrate. "
            "Tax code, tax return and property tax."
        ),
        "portal_url": "https://www.agenziaentrate.gov.it/",
        "portal_name": "Agenzia delle Entrate",
    },
    "sanita": {
        "description": (
            "SSN, tessera sanitaria, medico di base, iscrizione sanitaria e ASL. "
            "National health service, health card and GP."
        ),
        "portal_url": "https://www.salute.gov.it/",
        "portal_name": "Ministero della Salute",
    },
    "giustizia": {
        "description": (
            "Processo civile, notifica, gratuito patrocinio e certificato del casellario. "
            "Civil procedure, legal aid and criminal record certificate."
        ),
        "portal_url": "https://www.giustizia.it/",
        "portal_name": "Ministero della Giustizia",
    },
    "famiglia": {
        "description": (
            "Matrimonio, unione civile, nascita, stato civile e separazione. "
            "Marriage, civil union, birth and civil status."
        ),
        "portal_url": "https://www.anagrafenazionale.interno.it/area-cittadino/",
        "portal_name": "ANPR",
    },
    "impresa": {
        "description": (
            "Partita IVA, registro imprese, apertura attività e SUAP. VAT number and business register."
        ),
        "portal_url": "https://www.registroimprese.it/",
        "portal_name": "Registro Imprese",
    },
    "istruzione": {
        "description": (
            "Riconoscimento del titolo di studio, equipollenza, iscrizione scolastica e università. "
            "Recognition of a foreign qualification and school enrolment."
        ),
        "portal_url": "https://www.cimea.it/",
        "portal_name": "CIMEA",
    },
    "mobilita": {
        "description": (
            "Patente, conversione della patente estera, motorizzazione e bollo auto. "
            "Driving licence conversion and vehicle tax."
        ),
        "portal_url": "https://www.ilportaledellautomobilista.it/",
        "portal_name": "Portale dell'Automobilista",
    },
    "casa": {
        "description": (
            "Contratto di locazione, registrazione, cedolare secca e deposito cauzionale. "
            "Rental contract registration."
        ),
        "portal_url": "https://www.agenziaentrate.gov.it/",
        "portal_name": "Agenzia delle Entrate",
    },
}

TOPICS: dict[str, TopicProfile] = {
    topic: TopicProfile(
        topic=topic,
        description=data["description"],
        portal_url=data["portal_url"],
        portal_name=data["portal_name"],
    )
    for topic, data in _PROFILE_DATA.items()
}

assert set(TOPICS) == INGEST_TOPICS
assert "genel" not in TOPICS

GENERAL_PORTAL = TopicProfile(
    topic="genel",
    description="",
    portal_url="https://www.interno.gov.it/",
    portal_name="Ministero dell'Interno",
)


def seed_topic_profiles(embedder, store) -> None:
    for topic in _TOPIC_ORDER:
        profile = TOPICS[topic]
        embedding = embedder.embed_query(profile.description)
        store.upsert_profile(
            topic,
            profile.description,
            profile.portal_url,
            profile.portal_name,
            embedding,
        )