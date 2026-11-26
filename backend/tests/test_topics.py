from ingest.models import TOPICS as INGEST_TOPICS

from app.rag.topics import GENERAL_PORTAL, TOPICS, TopicProfile, seed_topic_profiles

EXPECTED_PROFILES: dict[str, dict[str, str]] = {
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
            "Address change, civil registry and self-certification."
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


def test_topics_keys_match_ingest_and_exclude_genel():
    assert set(TOPICS) == INGEST_TOPICS
    assert "genel" not in TOPICS


def test_each_topic_profile_matches_brief():
    assert len(TOPICS) == 13
    for topic, expected in EXPECTED_PROFILES.items():
        profile = TOPICS[topic]
        assert isinstance(profile, TopicProfile)
        assert profile.topic == topic
        assert profile.description == expected["description"]
        assert profile.portal_url == expected["portal_url"]
        assert profile.portal_name == expected["portal_name"]


def test_general_portal_constant():
    assert GENERAL_PORTAL.topic == "genel"
    assert GENERAL_PORTAL.description == ""
    assert GENERAL_PORTAL.portal_url == "https://www.interno.gov.it/"
    assert GENERAL_PORTAL.portal_name == "Ministero dell'Interno"
    assert "genel" not in TOPICS


class FakeEmbedder:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.calls.append(text)
        return [float(len(text)), float(hash(text) % 1000)]


class InMemoryStore:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def upsert_profile(
        self,
        topic: str,
        description: str,
        portal_url: str,
        portal_name: str,
        embedding: list[float],
    ) -> None:
        self.rows[topic] = {
            "topic": topic,
            "description": description,
            "portal_url": portal_url,
            "portal_name": portal_name,
            "embedding": embedding,
        }


def test_seed_topic_profiles_embeds_each_description_and_upserts_thirteen_rows():
    embedder = FakeEmbedder()
    store = InMemoryStore()
    seed_topic_profiles(embedder, store)

    assert len(store.rows) == 13
    assert set(store.rows) == set(TOPICS)
    assert "genel" not in store.rows
    assert len(embedder.calls) == 13

    for topic, profile in TOPICS.items():
        row = store.rows[topic]
        assert row["description"] == profile.description
        assert row["portal_url"] == profile.portal_url
        assert row["portal_name"] == profile.portal_name
        assert row["embedding"] == embedder.embed_query(profile.description)

    assert set(embedder.calls) == {profile.description for profile in TOPICS.values()}