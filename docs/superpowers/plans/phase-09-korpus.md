# Faz 9 — B ve C korpusu ile altın testler

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 13 konunun her birinde en az bir resmi tohum vardır. Altın sorular beklenen konuya ve hosta düşer. Kaynaklar sayfası son tarama tarihini gösterir. Korpus 40.000 parçayı geçmez.

**Architecture:** B ve C, Faz 5 katalog şemasına eklenir. Keşif kuralı değişmez. Kaynaklar sayfası parça metnini döndürmez.

**Tech Stack:** Mevcut ingest, FastAPI, React.

**Önkoşul:** [phase-05-ingest-a.md](phase-05-ingest-a.md) ve [phase-08-akis.md](phase-08-akis.md).

**Sonraki:** [phase-10-yayin.md](phase-10-yayin.md).

## Global Constraints

- `max_pages` her yeni kaynakta `30`.
- Parça tavanı `40000`. Aşımda `upsert_document` `skipped` döner ve kaynak hatası `corpus cap` olur.
- `GET /api/sources` gövdesinde `content` anahtarı yoktur.
- Altın test `integration` işaretlidir. `RUN_INTEGRATION=1` değilse atlanır.
- Groq altın testte çağrılmaz.
- İstek gövdesindeki `user_id` yok sayılır.

## Bu fazın dosyaları

- `backend/ingest/sources.yaml`
- `backend/ingest/upsert.py`
- `backend/ingest/__main__.py`
- `backend/app/api/sources.py`
- `backend/app/agent/parse.py`
- `backend/tests/test_catalog.py`
- `backend/tests/test_corpus_cap.py`
- `backend/tests/golden/questions.jsonl`
- `backend/tests/test_golden.py`
- `backend/tests/test_sources_api.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_parse.py`
- `backend/tests/test_sse.py`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/SourcesPage.tsx`

---

### Task 9.1: B grubu

**Files:**
- Modify: `backend/ingest/sources.yaml`
- Modify: `backend/tests/test_catalog.py`

**Interfaces:**
- `load_sources("b")` kimlikleri: `agenzia-entrate`, `inps`, `inail`, `salute`, `lavoro`

- [ ] **Step 1: Beş kaydı ekle**

```yaml
  - id: agenzia-entrate
    topic: fisco
    name: Agenzia delle Entrate
    batch: b
    portal_url: https://www.agenziaentrate.gov.it/
    urls: ["https://www.agenziaentrate.gov.it/"]
    keywords: ["codice fiscale", "dichiarazione", "IMU", "partita IVA"]
    max_pages: 30
  - id: inps
    topic: lavoro_previdenza
    name: INPS
    batch: b
    portal_url: https://www.inps.it/
    urls: ["https://www.inps.it/"]
    keywords: ["NASpI", "contributi", "pensione", "disoccupazione"]
    max_pages: 30
  - id: inail
    topic: lavoro_previdenza
    name: INAIL
    batch: b
    portal_url: https://www.inail.it/
    urls: ["https://www.inail.it/"]
    keywords: ["infortunio", "malattia professionale", "premio"]
    max_pages: 30
  - id: salute
    topic: sanita
    name: Ministero della Salute
    batch: b
    portal_url: https://www.salute.gov.it/
    urls: ["https://www.salute.gov.it/"]
    keywords: ["SSN", "tessera sanitaria", "medico", "stranieri"]
    max_pages: 30
  - id: lavoro
    topic: lavoro_previdenza
    name: Ministero del Lavoro
    batch: b
    portal_url: https://www.lavoro.gov.it/
    urls: ["https://www.lavoro.gov.it/"]
    keywords: ["contratto", "lavoro", "assunzione"]
    max_pages: 30
```

- [ ] **Step 2: Test bu beş kimliği `batch == "b"` diye doğrular**

- [ ] **Step 3: Commit**

```powershell
git commit -am "feat: catalog tax, welfare, health, and work sources"
```

---

### Task 9.2: C grubu

**Files:**
- Modify: `backend/ingest/sources.yaml`
- Modify: `backend/tests/test_catalog.py`

**Interfaces:**
- `load_sources("c")` kimlikleri: `giustizia`, `anpr-famiglia`, `registro-imprese`, `cimea`, `mur`, `automobilista`, `locazione`
- `load_sources("all")` konu kümesi 13 isme eşittir

- [ ] **Step 1: Yedi kaydı ekle**

```yaml
  - id: giustizia
    topic: giustizia
    name: Ministero della Giustizia
    batch: c
    portal_url: https://www.giustizia.it/
    urls: ["https://www.giustizia.it/"]
    keywords: ["patrocinio", "casellario", "notifica", "processo"]
    max_pages: 30
  - id: anpr-famiglia
    topic: famiglia
    name: ANPR stato civile
    batch: c
    portal_url: https://www.anagrafenazionale.interno.it/area-cittadino/
    urls: ["https://www.anagrafenazionale.interno.it/area-cittadino/"]
    keywords: ["matrimonio", "nascita", "stato civile", "unione"]
    max_pages: 30
  - id: registro-imprese
    topic: impresa
    name: Registro Imprese
    batch: c
    portal_url: https://www.registroimprese.it/
    urls: ["https://www.registroimprese.it/"]
    keywords: ["impresa", "avvio", "sede", "visura"]
    max_pages: 30
  - id: cimea
    topic: istruzione
    name: CIMEA
    batch: c
    portal_url: https://www.cimea.it/
    urls: ["https://www.cimea.it/"]
    keywords: ["riconoscimento", "titolo", "equipollenza"]
    max_pages: 30
  - id: mur
    topic: istruzione
    name: MUR
    batch: c
    portal_url: https://www.mur.gov.it/
    urls: ["https://www.mur.gov.it/"]
    keywords: ["università", "iscrizione", "titolo"]
    max_pages: 30
  - id: automobilista
    topic: mobilita
    name: Portale dell'Automobilista
    batch: c
    portal_url: https://www.ilportaledellautomobilista.it/
    urls: ["https://www.ilportaledellautomobilista.it/"]
    keywords: ["patente", "conversione", "motorizzazione"]
    max_pages: 30
  - id: locazione
    topic: casa
    name: Registrazione locazione
    batch: c
    portal_url: https://www.agenziaentrate.gov.it/
    urls: ["https://www.agenziaentrate.gov.it/"]
    keywords: ["locazione", "registrazione", "cedolare", "contratto"]
    max_pages: 30
```

- [ ] **Step 2: Konu kümesi testi**

```python
def test_catalog_covers_every_topic():
    topics = {item.topic for item in load_sources("all")}
    assert topics == {
        "immigrazione", "cittadinanza", "anagrafe", "identita_digitale",
        "lavoro_previdenza", "fisco", "sanita", "giustizia", "famiglia",
        "impresa", "istruzione", "mobilita", "casa",
    }
```

- [ ] **Step 3: Taramayı çalıştır**

```powershell
.\.venv\Scripts\python.exe -m ingest run --batch b
.\.venv\Scripts\python.exe -m ingest run --batch c
```

HTTP skip olan kaynak `error` olur. Komut çıkış kodu `0` kalır. Bir kaynak işlenirken yakalanmayan istisna çıkış kodunu `1` yapar.

- [ ] **Step 4: Commit**

```powershell
git commit -am "feat: catalog justice, family, business, study, driving, and housing sources"
```

---

### Task 9.3: Parça tavanı

**Files:**
- Modify: `backend/ingest/upsert.py`
- Modify: `backend/ingest/__main__.py`
- Create: `backend/tests/test_corpus_cap.py`

**Interfaces:**
- `count_chunks` enjekte edilir. Varsayılan uygulama `select id` sayımıdır.
- Sayı `>= 40000` ise yeni yazım yoktur.

- [ ] **Step 1: Test**

```python
def test_cap_skips_insert():
    result = upsert_document(source, url, "Titolo", long_text, embedder, store, count_chunks=lambda: 40000)
    assert result == "skipped"
    assert store.chunk_writes == 0
```

`finish_source` hata listesinde `corpus cap` görürse `sources.error` bu metindir.

- [ ] **Step 2: CLI satırı**

Stdout son satırı `chunk_count={n}`. `n > 40000` ise çıkış kodu `1`. Eşitlik `0` kalır çünkü yeni yazım zaten durmuştur.

- [ ] **Step 3: Commit**

```powershell
git commit -am "feat: stop ingest at the free-tier chunk cap"
```

---

### Task 9.4: Altın liste

**Files:**
- Create: `backend/tests/golden/questions.jsonl`
- Create: `backend/tests/test_golden.py`

**Interfaces:**
- Her satır `{"question","language","topic","host"}`

- [ ] **Step 1: 15 satırı yaz**

```json
{"question":"How do I renew a residence permit?","language":"en","topic":"immigrazione","host":"poliziadistato.it"}
{"question":"Entro quanti giorni va chiesto il permesso dopo l'ingresso?","language":"it","topic":"immigrazione","host":"poliziadistato.it"}
{"question":"Come cambio residenza in un altro comune?","language":"it","topic":"anagrafe","host":"anagrafenazionale.interno.it"}
{"question":"What documents are needed for residency registration as a non-EU citizen?","language":"en","topic":"anagrafe","host":"interno.gov.it"}
{"question":"How do I apply for Italian citizenship by residence?","language":"en","topic":"cittadinanza","host":"interno.gov.it"}
{"question":"Qual è il contributo per la domanda di cittadinanza?","language":"it","topic":"cittadinanza","host":"interno.gov.it"}
{"question":"How do I get SPID?","language":"en","topic":"identita_digitale","host":"spid.gov.it"}
{"question":"Come funziona l'autocertificazione?","language":"it","topic":"anagrafe","host":"normattiva.it"}
{"question":"Come chiedo il codice fiscale?","language":"it","topic":"fisco","host":"agenziaentrate.gov.it"}
{"question":"What is NASpI?","language":"en","topic":"lavoro_previdenza","host":"inps.it"}
{"question":"Come mi iscrivo al servizio sanitario nazionale?","language":"it","topic":"sanita","host":"salute.gov.it"}
{"question":"Come registro un contratto di locazione?","language":"it","topic":"casa","host":"agenziaentrate.gov.it"}
{"question":"How do I convert a foreign driving licence?","language":"en","topic":"mobilita","host":"ilportaledellautomobilista.it"}
{"question":"Come apro una partita IVA?","language":"it","topic":"impresa","host":"registroimprese.it"}
{"question":"Come chiedo il riconoscimento di un titolo di studio estero?","language":"it","topic":"istruzione","host":"cimea.it"}
```

- [ ] **Step 2: Testi yaz**

Her satır için `detect_language` beklenen dili ve `False` verir. `route_topic` beklenen konuyu verir. `retrieve_chunks` en az bir parça döner. Parçalardan birinin hostu beklenen sonekle biter. Host uyuşmazsa o konunun `portal_url` hostu da kabul edilir. İkisi de yoksa test düşer.

`RUN_INTEGRATION` boşsa dosyadaki her test `pytest.skip` olur. Groq istemcisi import edilmez.

- [ ] **Step 3: Commit**

```powershell
git add backend/tests/golden/questions.jsonl backend/tests/test_golden.py
git commit -m "test: add a golden question list for every bureaucracy area"
```

---

### Task 9.5: Kaynaklar sayfası

**Files:**
- Create: `backend/app/api/sources.py`
- Create: `backend/tests/test_sources_api.py`
- Modify: `frontend/src/pages/SourcesPage.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `backend/app/main.py`

**Interfaces:**
- `GET /api/sources` → `{id,name,topic,batch,portal_url,last_crawled_at,status}[]`
- Kimlik `current_user_id` ister.

- [ ] **Step 1: Test**

Store bir satırda `content` alanı da tutar. JSON yanıtının hiçbir öğesinde `content` anahtarı yoktur. Başlıksız istek `401` döner.

- [ ] **Step 2: Uç ve sayfa**

Sorgu `sources` tablosundan yalnız altı sütunu seçer: `id,name,topic,batch,portal_url,last_crawled_at,status`.

Sayfa konuya göre gruplanır. Grup başlığı konu kimliğidir. Satırda ad, durum, tarih ve portal bağlantısı vardır. `last_crawled_at` boşsa `—`. Liste boşsa `t("noSources")`.

`api.listSources()` Task 3.5 başlığını kullanır.

- [ ] **Step 3: Commit**

```powershell
git commit -am "feat: show indexed official sources in the shell"
```

---

### Task 9.6: Kimlik ve URL

**Files:**
- Modify: `backend/tests/test_conversations.py`
- Modify: `backend/tests/test_parse.py`
- Modify: `backend/tests/test_sse.py`
- Modify: `backend/app/agent/parse.py`

**Interfaces:**
- Gövde `{"content":"...","user_id":"<başka uuid>"}` olsa da yazılan satır jetonun `sub` değerini taşır.
- `strip_urls` Faz 7’de vardır. Bu task onun SSE metninde de çalıştığını kilitler.

- [ ] **Step 1: Kimlik testi**

POST gövdesine başka bir UUID koy. `MemoryChatStore` içindeki kullanıcının mesajı jeton UUID’sine bağlı konuşmadadır. Diğer UUID’nin listesi boştur.

- [ ] **Step 2: SSE URL testi**

Sahte model `See https://evil.example/a\nCITATIONS: chunk-1` döner. `token` olayının metninde `evil.example` yoktur. `citations` olayındaki URL parça URL’sidir.

- [ ] **Step 3: Commit**

```powershell
git commit -am "test: keep identity and citations tied to trusted records"
```

---

### Task 9.7: Faz çıkışı

- [ ] `pytest --rootdir=backend -m "not integration"` geçer.
- [ ] `RUN_INTEGRATION=1` altın testi geçer. Düşen satırın kaynağı `sources.status=error` ise o URL düzeltilir ve test yeniden çalışır. Faz bu kırmızıyla kapanmaz.
- [ ] `chunk_count` `40000` altındadır.
- [ ] Kaynaklar sayfası A, B ve C satırlarını gösterir.

Faz 10: [phase-10-yayin.md](phase-10-yayin.md)
