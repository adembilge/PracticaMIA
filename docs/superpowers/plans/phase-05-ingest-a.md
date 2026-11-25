# Faz 5 — Ingest ve A grubu korpus

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A grubu sayfaları parçalanır, gömülür ve `chunks` tablosuna yazılır. Aynı içerik ikinci çalıştırmada yeniden gömülmez.

**Architecture:** Katalog YAML’dir. İndirme izin listesi ve `robots.txt` ile kapanır. Gömme `intfloat/multilingual-e5-small`. Birim testler modeli yüklemez.

**Tech Stack:** httpx, trafilatura, pypdf, fastembed, PyYAML, Supabase.

**Önkoşul:** [phase-02-veri.md](phase-02-veri.md).

**Sonraki:** [phase-06-arama.md](phase-06-arama.md).

## Global Constraints

- User-Agent: `PracticaMIA-bot/0.1 (public administration study assistant)`.
- Alan adı başına en az `1` saniye. Zaman aşımı `20` saniye. Yönlendirme en fazla `3`.
- `robots.txt` okunamazsa `skipped_reason="robots"`.
- Kaynak başına en fazla `30` sayfa.
- Parça `500` sözcük, bindirme `80` sözcük. Sözcük `text.split()`.
- Pasaj öneki `passage: `. Soru öneki `query: `. Vektör L2-normalize. Boyut `384`.
- 200 sözcükten kısa metin `skipped`.
- Yasak URL parçası: `0554_initaliainregola`.
- İzinli sonekler: `interno.gov.it`, `poliziadistato.it`, `portaleimmigrazione.it`, `integrazionemigranti.gov.it`, `normattiva.it`, `gazzettaufficiale.it`, `spid.gov.it`, `agenziaentrate.gov.it`, `inps.it`, `inail.it`, `salute.gov.it`, `lavoro.gov.it`, `giustizia.it`, `registroimprese.it`, `mur.gov.it`, `cimea.it`, `ilportaledellautomobilista.it`.
- Konular: `immigrazione`, `cittadinanza`, `anagrafe`, `identita_digitale`, `lavoro_previdenza`, `fisco`, `sanita`, `giustizia`, `famiglia`, `impresa`, `istruzione`, `mobilita`, `casa`.

## Bu fazın dosyaları

- `backend/ingest/__init__.py`
- `backend/ingest/models.py`
- `backend/ingest/catalog.py`
- `backend/ingest/fetch.py`
- `backend/ingest/extract.py`
- `backend/ingest/chunk.py`
- `backend/ingest/discover.py`
- `backend/ingest/upsert.py`
- `backend/ingest/__main__.py`
- `backend/ingest/sources.yaml`
- `backend/app/rag/__init__.py`
- `backend/app/rag/embed.py`
- `backend/tests/test_catalog.py`
- `backend/tests/test_fetch.py`
- `backend/tests/test_chunk.py`
- `backend/tests/test_embed_prefix.py`
- `backend/tests/test_ingest_run.py`

---

### Task 5.1: Katalog modeli

**Files:**
- Create: `backend/ingest/__init__.py`
- Create: `backend/ingest/models.py`
- Create: `backend/ingest/catalog.py`
- Create: `backend/tests/test_catalog.py`

**Interfaces:**
- Produces: `SourceSpec` ve `load_sources(batch: Literal["a","b","c","all"]) -> list[SourceSpec]`

- [ ] **Step 1: Testi yaz**

Geçici YAML:

```yaml
sources:
  - id: one
    topic: immigrazione
    name: One
    batch: a
    portal_url: https://www.poliziadistato.it/articolo/225
    urls: ["https://www.poliziadistato.it/articolo/225"]
    keywords: [permesso]
  - id: two
    topic: anagrafe
    name: Two
    batch: a
    portal_url: https://www.anagrafenazionale.interno.it/area-cittadino/
    urls: ["https://www.anagrafenazionale.interno.it/area-cittadino/"]
    keywords: [residenza]
  - id: three
    topic: fisco
    name: Three
    batch: b
    portal_url: https://www.agenziaentrate.gov.it/
    urls: ["https://www.agenziaentrate.gov.it/"]
    keywords: [IMU]
```

`load_sources("a", path)` iki kayıt döner. Konu `spor` ise `ValueError`. `portal_url: http://example.com` ise `ValueError`.

- [ ] **Step 2: Modeli yaz**

```python
TOPICS = {
    "immigrazione", "cittadinanza", "anagrafe", "identita_digitale",
    "lavoro_previdenza", "fisco", "sanita", "giustizia", "famiglia",
    "impresa", "istruzione", "mobilita", "casa",
}

class SourceSpec(BaseModel):
    id: str
    topic: str
    name: str
    batch: Literal["a", "b", "c"]
    portal_url: str
    urls: list[str]
    keywords: list[str]
    max_pages: int = 30

    @field_validator("topic")
    @classmethod
    def known_topic(cls, value: str) -> str:
        if value not in TOPICS:
            raise ValueError(value)
        return value

    @field_validator("portal_url", "urls")
    @classmethod
    def https_only(cls, value):
        items = value if isinstance(value, list) else [value]
        for item in items:
            if not str(item).startswith("https://"):
                raise ValueError(item)
        return value
```

`load_sources` dosyayı `yaml.safe_load` ile okur. Varsayılan yol `Path(__file__).with_name("sources.yaml")`. Test yol parametresi verir.

- [ ] **Step 3: Testi geçir ve commit et**

```powershell
.\.venv\Scripts\python.exe -m pytest --rootdir=backend backend/tests/test_catalog.py -v
git commit -am "feat: load the official source catalog"
```

---

### Task 5.2: İndirme

**Files:**
- Create: `backend/ingest/fetch.py`
- Create: `backend/tests/test_fetch.py`

**Interfaces:**
- Produces:

```python
ALLOWED_HOST_SUFFIXES: tuple[str, ...]
USER_AGENT = "PracticaMIA-bot/0.1 (public administration study assistant)"

class FetchResult(BaseModel):
    url: str
    status: int
    content_type: str
    body: bytes
    skipped_reason: str | None

def host_allowed(url: str) -> bool: ...
def fetch_url(url: str, client: httpx.Client, robots_for, now: Callable[[], float], host_next: dict[str, float]) -> FetchResult: ...
```

`robots_for(host) -> RobotFileParser | None`. `None` dönüşü `skipped_reason="robots"`.

- [ ] **Step 1: Testleri yaz**

`httpx.MockTransport` ile:

- `https://evil.example/a` → `skipped_reason="host"`, transport çağrı sayacı 0 artmaz. Sayaç transport’un kendisindedir; `host_allowed` istekten önce döner.
- Robots `Disallow: /secret` ve URL o yolda → `skipped_reason="robots"`.
- Aynı host için `now` listesi `[0, 0, 1]` ise ikinci fetch üçüncü saate kadar bekler. Bekleme `time.sleep` yerine enjekte edilen `sleep(seconds)` ile sayılır. Beklenen uyku `1`.
- Son URL `https://www.poliziadistato.it/login` → `skipped_reason="login"`. Aynı kural yolunda `accedi` varsa da geçerlidir.
- `content-type: image/png` → `skipped_reason="type"`.
- `text/html` ve `application/pdf` gövdeyi döner.

- [ ] **Step 2: `fetch_url` yaz**

Host soneki `host == suffix` veya `host.endswith("." + suffix)`. Karşılaştırma küçük harftir.

- [ ] **Step 3: Testi geçir ve commit et**

```powershell
git commit -am "feat: fetch allowlisted official pages"
```

---

### Task 5.3: Metin ve parça

**Files:**
- Create: `backend/ingest/extract.py`
- Create: `backend/ingest/chunk.py`
- Create: `backend/tests/test_chunk.py`

**Interfaces:**
- `extract_html(body: bytes, url: str) -> tuple[str, str]` başlık ve düz metin.
- `extract_pdf(body: bytes) -> tuple[str, str]`. Başlık yoksa `"document"`.
- `chunk_text(text: str, max_tokens: int = 500, overlap_tokens: int = 80) -> list[ChunkDraft]`

```python
class ChunkDraft(BaseModel):
    heading: str
    content: str
    chunk_index: int
    content_hash: str
```

- [ ] **Step 1: Parça testlerini yaz**

`word` sözcüğünden 1200 tane, arada bir satır `# Residenza`. Sonuçta en az 3 parça. Ardışık parçaların son 80 sözcüğü ile sonraki parçanın başı örtüşür. Başlıktan sonraki parçanın `heading` değeri `Residenza`. Boş metin `[]`. `content_hash` sha256 ve girdi boşlukları tekilleştirilmiş metindir: `" ".join(content.split())`.

- [ ] **Step 2: Çıkarıcı ve parçalayıcıyı yaz**

HTML `trafilatura.extract(body, url=url, output_format="txt")` ve metadata başlığı. PDF `pypdf.PdfReader(BytesIO(body))`, sayfa metinleri `\n` ile birleşir. Çıktı boşsa `("", "")`.

Parçalama: satır `# ` ile başlıyorsa heading güncellenir ve satır gövdeye girmez. Sözcük penceresi `max_tokens`, adım `max_tokens - overlap_tokens`.

- [ ] **Step 3: Testi geçir ve commit et**

```powershell
git commit -am "feat: extract and chunk official text"
```

---

### Task 5.4: Gömme öneki

**Files:**
- Create: `backend/app/rag/__init__.py`
- Create: `backend/app/rag/embed.py`
- Create: `backend/tests/test_embed_prefix.py`

**Interfaces:**
- `as_passage(text: str) -> str`
- `as_query(text: str) -> str`
- `l2_normalize(vector: list[float]) -> list[float] | None` — norm 0 ise `None`
- `class Embedder` metotları `embed_passages(texts: list[str]) -> list[list[float]]` ve `embed_query(text: str) -> list[float]`

- [ ] **Step 1: Önek ve norm testleri**

```python
def test_prefixes():
    assert as_passage("ciao").startswith("passage: ")
    assert as_query("ciao").startswith("query: ")

def test_normalize_unit():
    vector = l2_normalize([3.0, 4.0])
    assert vector is not None
    assert abs(sum(item * item for item in vector) - 1) < 1e-9

def test_normalize_zero():
    assert l2_normalize([0.0, 0.0]) is None
```

- [ ] **Step 2: `Embedder` yaz**

`fastembed.TextEmbedding` kurucuda yüklenir. `embed_passages` her metne `as_passage` uygular, sonra `l2_normalize`. `None` olan parça listeden düşer ve çağıran o parçayı yazmaz. Birim test `Embedder` kurmaz. Ayrı bir `FakeEmbedder` testlerde 384 tane `1/math.sqrt(384)` döner.

- [ ] **Step 3: Commit**

```powershell
git commit -am "feat: prefix and normalize embeddings"
```

---

### Task 5.5: Yazma

**Files:**
- Create: `backend/ingest/upsert.py`
- Create: `backend/tests/test_upsert.py`

**Interfaces:**
- `upsert_document(source: SourceSpec, url: str, title: str, text: str, embedder, store) -> Literal["inserted","unchanged","skipped"]`
- `store` metotları: `find_document(url) -> dict | None`, `replace_chunks(document_id, rows)`, `insert_document(...) -> id`, `delete_chunks(document_id)`.

- [ ] **Step 1: Test**

Aynı hash ikinci çağrıda `unchanged` ve `embed_passages` sayacı artmaz. Hash değişince eski parçalar silinir, dönüş `inserted`. 10 sözcüklük metin `skipped`.

- [ ] **Step 2: Kuralı yaz**

Hash `hashlib.sha256(" ".join(text.split()).encode()).hexdigest()`. Belge dili `it`. `fetched_at` UTC `isoformat`.

Kaynak özeti ayrı işlevdedir: `finish_source(source_id, outcomes: list[str], errors: list[str], store) -> None`. En az bir `inserted` veya `unchanged` varsa `status=ok`. Hepsi `skipped` veya boşsa `status=error` ve `error` ilk neden. `last_crawled_at` her çağrıda güncellenir.

- [ ] **Step 3: Commit**

```powershell
git commit -am "feat: embed chunks and skip unchanged documents"
```

---

### Task 5.6: A grubu katalog ve keşif

**Files:**
- Create: `backend/ingest/sources.yaml`
- Create: `backend/ingest/discover.py`
- Modify: `backend/tests/test_catalog.py`

**Interfaces:**
- `load_sources("a")` 14 kayıt döner.
- `discover(html: str, page_url: str, source: SourceSpec, seen: set[str]) -> list[str]`

- [ ] **Step 1: 14 kaydı yaz**

Her kayıtta `batch: a` ve `max_pages: 30`. Portal, tek tohum URL ve anahtarlar:

| id | topic | url | keywords |
| --- | --- | --- | --- |
| polizia-permesso | immigrazione | https://www.poliziadistato.it/articolo/225 | permesso, soggiorno, questura, rinnovo |
| interno-immigrazione | immigrazione | https://www.interno.gov.it/it/temi/immigrazione-e-asilo | immigrazione, asilo, visto, ricongiungimento |
| portale-immigrazione | immigrazione | https://portaleimmigrazione.it/ | permesso, kit, poste, rinnovo |
| integrazione-migranti | immigrazione | https://www.integrazionemigranti.gov.it/ | integrazione, permesso, lavoro |
| normattiva-tu-immigrazione | immigrazione | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:1998-07-25;286 | soggiorno, espulsione, lavoro |
| dlci-cittadinanza | cittadinanza | https://libertaciviliimmigrazione.dlci.interno.gov.it/cittadinanza-invia-la-tua-domanda | cittadinanza, domanda, contributo, B1 |
| portale-cittadinanza | cittadinanza | https://cittadinanza.dlci.interno.it | cittadinanza, SPID, CIE |
| normattiva-cittadinanza | cittadinanza | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:1992-02-05;91 | cittadinanza, matrimonio, residenza |
| anpr-cittadino | anagrafe | https://www.anagrafenazionale.interno.it/area-cittadino/ | residenza, cambio, certificato, autocertificazione |
| normattiva-anagrafe-legge | anagrafe | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:1954-12-24;1228 | anagrafe, popolazione |
| normattiva-anagrafe-regolamento | anagrafe | https://www.normattiva.it/uri-res/N2Ls?urn:nir:presidente.repubblica:decreto:1989-05-30;223 | residenza, dimora, famiglia |
| normattiva-autocertificazione | anagrafe | https://www.normattiva.it/uri-res/N2Ls?urn:nir:presidente.repubblica:decreto:2000-12-28;445 | autocertificazione, dichiarazione sostitutiva |
| spid | identita_digitale | https://www.spid.gov.it/ | SPID, identità, gestore |
| cie | identita_digitale | https://www.cartaidentita.interno.gov.it/ | CIE, carta, identità |

`name` alanı id’nin boşluklu halidir. `portal_url` tohum URL ile aynıdır. Normattiva kayıtlarında `portal_url` `https://www.normattiva.it/` olur.

- [ ] **Step 2: Keşif testi**

HTML içinde iki `a` etiketi. Biri anahtar sözcüğü taşır ve izinli hosttadır, diğeri `https://evil.example` olur. `discover` yalnız birincisini döner. Görülmüş URL ikinci kez dönmez. `seen` boyutu `max_pages` ise liste boştur.

Anahtar, URL’de veya bağlantı metninde, büyük-küçük harf duyarsız aranır.

- [ ] **Step 3: Yasak URL**

```python
def test_catalog_excludes_stale_brochure():
    text = Path("ingest/sources.yaml").read_text(encoding="utf-8")
    assert "0554_initaliainregola" not in text
```

- [ ] **Step 4: Commit**

```powershell
git add backend/ingest/sources.yaml backend/ingest/discover.py backend/tests/test_catalog.py
git commit -m "feat: add the first official source catalog"
```

---

### Task 5.7: Çalıştırıcı

**Files:**
- Create: `backend/ingest/__main__.py`
- Create: `backend/tests/test_ingest_run.py`

**Interfaces:**
- `python -m ingest run --batch a|b|c|all`
- Satır biçimi: `{id} {status} inserted={n} unchanged={n} skipped={n}`
- Supabase yoksa çıkış kodu `2` ve stdout `supabase is not configured`

- [ ] **Step 1: Sahte tur testi**

`fetch_url` sabit HTML döner. `FakeEmbedder` 384 boyutlu birim vektör verir. `MemoryIngestStore` bir belge ve en az bir parça tutar. İkinci `run_batch` aynı belge için `unchanged` sayar.

`run_batch(batch, fetch, embedder, store) -> int` çıkış kodunu döner. Bir kaynakta istisna olursa o kaynak `error` olur ve döngü sürer. İşlevin kendisi istisna yutmazsa çıkış kodu `1` olur; kaynak içi HTTP skip çıkış kodunu `0` bırakır.

- [ ] **Step 2: CLI**

```python
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?")
    parser.add_argument("--batch", default="a", choices=["a", "b", "c", "all"])
    args = parser.parse_args(argv)
    ...
```

Komut `python -m ingest run --batch a`. İlk konumsal argüman `run` değilse çıkış kodu `2`.

- [ ] **Step 3: Canlı A taraması**

`.env` doluyken:

```powershell
.\.venv\Scripts\python.exe -m ingest run --batch a
```

Beklenen: en az bir satırda `ok`. HTTP 200 vermeyen normattiva kaydı `error` olur, komut `0` ile biter. Supabase SQL Editor: `select count(*) from chunks;` sıfırdan büyüktür.

- [ ] **Step 4: Commit**

```powershell
git commit -am "feat: run the batch A ingest"
```

---

### Task 5.8: Faz çıkışı

- [ ] `pytest --rootdir=backend backend/tests/test_catalog.py backend/tests/test_fetch.py backend/tests/test_chunk.py backend/tests/test_embed_prefix.py backend/tests/test_upsert.py backend/tests/test_ingest_run.py` geçer.
- [ ] İkinci canlı tarama gömme çağrısını artırmaz; satırlarda `unchanged` vardır.
- [ ] `chunks` ile birleşen `documents.url` hostları izin listesindedir.

Faz 6: [phase-06-arama.md](phase-06-arama.md)
