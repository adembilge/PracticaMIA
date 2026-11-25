# Faz 6 — Dil, konu ve hibrit arama

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bir soru dil ve konu alır. `match_chunks` en fazla 4 parça döner. Parça yoksa portal cümlesi üretilir. Groq bu fazda çağrılmaz.

**Architecture:** Konu, soru gömüsünün 13 profil gömüsüne kosinüsüdür. Arama Faz 2’deki `match_chunks` RPC’sidir. Eşik altı konu `genel` olur ve profil tablosunda durmaz.

**Tech Stack:** langdetect, fastembed, Supabase RPC.

**Önkoşul:** [phase-05-ingest-a.md](phase-05-ingest-a.md).

**Sonraki:** [phase-07-langgraph.md](phase-07-langgraph.md).

## Global Constraints

- Konu kosinüsü `>= 0.45`. Altında sonuç `genel`.
- Parça kosinüsü `>= 0.30`. Bu eşik SQL’dedir. Uygulama en fazla `4` parça ister.
- `genel` profil değildir. Portal yedeği `https://www.interno.gov.it/`, ad `Ministero dell'Interno`.
- Dil çifti `(language, unsupported)`. Desteklenmeyen dil `("en", True)`.
- Olasılık eşiği `0.80`.
- İtalyanca işlev sözcükleri: `il`, `lo`, `la`, `di`, `che`, `per`, `non`, `sono`, `come`, `una`.
- İngilizce işlev sözcükleri: `the`, `and`, `how`, `what`, `do`, `is`, `a`, `to`.
- İngilizce portal cümlesi: `The indexed official pages do not state this. Start from {portal_name}: {portal_url}`
- İtalyanca portal cümlesi: `Le pagine ufficiali indicizzate non lo riportano. Parti da {portal_name}: {portal_url}`

## Bu fazın dosyaları

- `backend/app/rag/topics.py`
- `backend/app/rag/language.py`
- `backend/app/rag/retrieve.py`
- `backend/tests/test_topics.py`
- `backend/tests/test_language.py`
- `backend/tests/test_retrieve.py`
- `backend/tests/test_retrieve_live.py`

---

### Task 6.1: Konu profilleri

**Files:**
- Create: `backend/app/rag/topics.py`
- Create: `backend/tests/test_topics.py`

**Interfaces:**

```python
class TopicProfile(BaseModel):
    topic: str
    description: str
    portal_url: str
    portal_name: str

TOPICS: dict[str, TopicProfile]
GENERAL_PORTAL = TopicProfile(
    topic="genel",
    description="",
    portal_url="https://www.interno.gov.it/",
    portal_name="Ministero dell'Interno",
)

def seed_topic_profiles(embedder, store) -> None: ...
```

- [ ] **Step 1: 13 açıklamayı birebir yaz**

- `immigrazione`: `Permesso di soggiorno, rinnovo, visto, ricongiungimento familiare, asilo, questura e kit postale. Residence permit, renewal, visa, family reunification and asylum.` Portal `https://www.poliziadistato.it/articolo/225`, ad `Polizia di Stato`.
- `cittadinanza`: `Cittadinanza per residenza, matrimonio o discendenza, domanda online, contributo e requisito B1. Citizenship by residence, marriage or descent.` Portal `https://libertaciviliimmigrazione.dlci.interno.gov.it/cittadinanza-invia-la-tua-domanda`, ad `Ministero dell'Interno`.
- `anagrafe`: `Cambio di residenza, iscrizione anagrafica, stato di famiglia, certificati e autocertificazione. Address change, civil registry and self-certification.` Portal `https://www.anagrafenazionale.interno.it/area-cittadino/`, ad `ANPR`.
- `identita_digitale`: `SPID, CIE, PIN, PUK e identità digitale. Digital identity to enter public services.` Portal `https://www.spid.gov.it/`, ad `SPID`.
- `lavoro_previdenza`: `NASpI, contributi, disoccupazione, pensione, INPS, INAIL e infortunio sul lavoro. Unemployment benefit, contributions, pension and workplace injury.` Portal `https://www.inps.it/`, ad `INPS`.
- `fisco`: `Codice fiscale, dichiarazione dei redditi, IMU e Agenzia delle Entrate. Tax code, tax return and property tax.` Portal `https://www.agenziaentrate.gov.it/`, ad `Agenzia delle Entrate`.
- `sanita`: `SSN, tessera sanitaria, medico di base, iscrizione sanitaria e ASL. National health service, health card and GP.` Portal `https://www.salute.gov.it/`, ad `Ministero della Salute`.
- `giustizia`: `Processo civile, notifica, gratuito patrocinio e certificato del casellario. Civil procedure, legal aid and criminal record certificate.` Portal `https://www.giustizia.it/`, ad `Ministero della Giustizia`.
- `famiglia`: `Matrimonio, unione civile, nascita, stato civile e separazione. Marriage, civil union, birth and civil status.` Portal `https://www.anagrafenazionale.interno.it/area-cittadino/`, ad `ANPR`.
- `impresa`: `Partita IVA, registro imprese, apertura attività e SUAP. VAT number and business register.` Portal `https://www.registroimprese.it/`, ad `Registro Imprese`.
- `istruzione`: `Riconoscimento del titolo di studio, equipollenza, iscrizione scolastica e università. Recognition of a foreign qualification and school enrolment.` Portal `https://www.cimea.it/`, ad `CIMEA`.
- `mobilita`: `Patente, conversione della patente estera, motorizzazione e bollo auto. Driving licence conversion and vehicle tax.` Portal `https://www.ilportaledellautomobilista.it/`, ad `Portale dell'Automobilista`.
- `casa`: `Contratto di locazione, registrazione, cedolare secca e deposito cauzionale. Rental contract registration.` Portal `https://www.agenziaentrate.gov.it/`, ad `Agenzia delle Entrate`.

- [ ] **Step 2: Test, 13 anahtarı ve `genel` yokluğunu doğrular**

`set(TOPICS) ==` Faz 5’teki `TOPICS` kümesi. `"genel" not in TOPICS`.

- [ ] **Step 3: `seed_topic_profiles`**

Her `description` için `embedder.embed_query`. `store.upsert_profile(topic, description, portal_url, portal_name, embedding)`. Test store’u bellek sözlüğüdür ve sonunda 13 satır vardır. `GENERAL_PORTAL` yazılmaz.

- [ ] **Step 4: Commit**

```powershell
git commit -am "feat: seed thirteen bureaucracy topic profiles"
```

---

### Task 6.2: Dil

**Files:**
- Create: `backend/app/rag/language.py`
- Create: `backend/tests/test_language.py`

**Interfaces:**
- `detect_language(text: str) -> tuple[Literal["en", "it"], bool]`

- [ ] **Step 1: Testleri yaz**

```python
def test_english_question():
    assert detect_language("How do I renew a residence permit?") == ("en", False)

def test_italian_question():
    assert detect_language("Come rinnovo il permesso di soggiorno?") == ("it", False)

def test_turkish_question():
    assert detect_language("Oturum iznimi nasıl yenilerim?") == ("en", True)
```

- [ ] **Step 2: Kuralı yaz**

`langdetect.detect_langs`. `langdetect.DetectorFactory.seed = 0` modül yükünde bir kez.

En yüksek olasılık `>= 0.80` ve dil `en` veya `it` ise `(dil, False)`. Olasılık `>= 0.80` ve dil ikisi de değilse `("en", True)`. Olasılık `0.80` altındaysa sözcük sayımı. Sözcük sınırında, küçük harfte. İtalyanca sayı büyükse `("it", False)`, değilse `("en", False)`. Bu dalda ikinci değer daima `False`.

`langdetect` istisna fırlatırsa sözcük sayımına düş.

- [ ] **Step 3: Testi geçir ve commit et**

`langdetect` kısa cümlede kararsız olabilir. Üç cümle bu kuralla kilitlenir. Test kırmızıysa eşik dalı değil sözcük dalı çalışıyordur; o zaman sözcük sayımı beklenen dili vermelidir. Türkçe cümlede `tespit` olasılığı 0.80 altında kalırsa sözcük sayımı İngilizceye düşer ve `unsupported` yanlışlıkla `False` olur. Bunu önlemek için Türkçe testte `detect_langs` taklit edilir:

```python
def test_turkish_question(monkeypatch):
    monkeypatch.setattr("app.rag.language._top_lang", lambda _text: ("tr", 0.99))
    assert detect_language("Oturum iznimi nasıl yenilerim?") == ("en", True)
```

`_top_lang(text) -> tuple[str, float]` `detect_langs` sonucunu okur. İngilizce ve İtalyanca testler taklit kullanmaz.

- [ ] **Step 4: Commit**

```powershell
git commit -am "feat: detect English, Italian, and other question languages"
```

---

### Task 6.3: Yönlendirme ve arama

**Files:**
- Create: `backend/app/rag/retrieve.py`
- Create: `backend/tests/test_retrieve.py`
- Create: `backend/tests/test_retrieve_live.py`

**Interfaces:**

```python
def cosine(a: list[float], b: list[float]) -> float: ...

def route_topic(query_embedding: list[float], profiles: list[dict]) -> str:
    """Returns a topic id or 'genel'."""

def retrieve_chunks(query: str, topic: str, embedder, rpc) -> list[dict]:
    """Keys: id, content, heading, url, title, topic, fetched_at, cosine_similarity."""

def portal_reply(topic: str, language: Literal["en", "it"]) -> tuple[str, list[dict]]:
    """Citation chunk_id is ''."""
```

`rpc(query_embedding, query_text, topic_filter, match_count) -> list[dict]`.

- [ ] **Step 1: Yönlendirme testi**

```python
def test_route_picks_close_topic():
    profiles = [
        {"topic": "anagrafe", "embedding": [1.0, 0.0]},
        {"topic": "fisco", "embedding": [0.0, 1.0]},
    ]
    assert route_topic([0.9, 0.1], profiles) == "anagrafe"

def test_route_general_below_threshold():
    profiles = [{"topic": "anagrafe", "embedding": [1.0, 0.0]}]
    assert route_topic([0.0, 1.0], profiles) == "genel"
```

Kosinüs `0.45` altı `genel`. İkinci vektörün kosinüsü `0` olduğu için eşik altındadır.

- [ ] **Step 2: `retrieve_chunks` yaz**

1. `embedder.embed_query(query)`.
2. `topic_filter = ""` if `topic == "genel"` else `topic`.
3. `rpc(..., match_count=4)`.
4. Liste boş ve konu `genel` değilse aynı çağrı `topic_filter=""` ile bir kez daha.
5. RPC istisna fırlatırsa `query_text` olarak `" ".join(query.split()[:12])` ile bir kez daha dene. O da fırlatırsa `[]`.

Dönen her öğede `cosine_similarity` float’tır. SQL zaten `0.30` altını keser. Uygulama ikinci bir kesim yapmaz.

- [ ] **Step 3: Portal testi**

```python
def test_portal_reply_english():
    text, cites = portal_reply("immigrazione", "en")
    assert "https://www.poliziadistato.it/articolo/225" in text
    assert cites[0]["chunk_id"] == ""
    assert cites[0]["fetched_at"] == ""

def test_portal_reply_general():
    text, _cites = portal_reply("genel", "it")
    assert "https://www.interno.gov.it/" in text
```

Bilinmeyen konu da `GENERAL_PORTAL` kullanır.

- [ ] **Step 4: Canlı test**

`backend/tests/test_retrieve_live.py` işaret `integration`. `RUN_INTEGRATION` yoksa `pytest.skip`. Soru `Come cambio residenza?`. Kabul: `route_topic` sonucu `anagrafe`, ya da dönen parçalardan birinin URL’si `anagrafenazionale.interno.it` içerir.

- [ ] **Step 5: Commit**

```powershell
git commit -am "feat: route topics and retrieve official chunks"
```

---

### Task 6.4: Faz çıkışı

- [ ] `pytest --rootdir=backend backend/tests/test_topics.py backend/tests/test_language.py backend/tests/test_retrieve.py -v` geçer.
- [ ] `RUN_INTEGRATION=1` ile canlı test, A grubu yüklüyse geçer.
- [ ] Boş profil çağrısı `portal_reply("immigrazione", "en")` Polizia URL’sini içerir.

Faz 7: [phase-07-langgraph.md](phase-07-langgraph.md)
