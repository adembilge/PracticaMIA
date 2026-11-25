# Faz 8 — Akış, kota ve geçmiş

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Composer cevabı token token gösterir. Kartlarda yalnız doğrulanmış kaynaklar durur. 16. kullanıcı sorusu ve 41. genel soru nazik red alır. Faz 4’teki geçici cümle kalkar.

**Architecture:** Kota grafikten önce bakılır. Artış, asistan satırı yazıldıktan sonra yapılır. SSE `fetch` ile okunur. Kota dolunca HTTP `200` ve ilk olay `error` olur.

**Tech Stack:** FastAPI StreamingResponse, LangGraph, React ReadableStream.

**Önkoşul:** [phase-04-sohbet.md](phase-04-sohbet.md) ve [phase-07-langgraph.md](phase-07-langgraph.md).

**Sonraki:** [phase-09-korpus.md](phase-09-korpus.md).

## Global Constraints

- Kullanıcı kotası `15`. Genel kota `40`. Gün `Europe/Rome`.
- `2026-01-15 23:30:00+00:00` anında Roma tarihi `2026-01-16` olur. Kış saati UTC+1’dir.
- Geçmişte son `6` mesaj. Her `content` en fazla `500` karakter.
- Kota mesajı `Accept-Language` `it` ile başlıyorsa: `La capacità giornaliera di risposte è esaurita. Riprova domani.`
- Değilse: `The daily answer capacity is used. Try again tomorrow.`
- Olay adları: `token`, `citations`, `done`, `error`.
- `error.code`: `quota_user`, `quota_global`, `upstream`.
- `api.postMessage` silinir.

## Bu fazın dosyaları

- `backend/app/quota.py`
- `backend/app/agent/history.py`
- `backend/app/agent/stream.py`
- `backend/app/api/messages.py`
- `backend/tests/test_quota.py`
- `backend/tests/test_history.py`
- `backend/tests/test_stream.py`
- `backend/tests/test_sse.py`
- `frontend/src/lib/api.ts`
- `frontend/src/components/CitationList.tsx`
- `frontend/src/components/MessageList.tsx`
- `frontend/src/components/Composer.tsx`
- `frontend/src/pages/ChatPage.tsx`

---

### Task 8.1: Kota

**Files:**
- Create: `backend/app/quota.py`
- Create: `backend/tests/test_quota.py`

**Interfaces:**

```python
class QuotaDecision(TypedDict):
    allowed: bool
    reason: Literal["ok", "user_daily", "global_daily"]

def rome_today(now: datetime | None = None) -> date: ...
def check_quota(user_id: UUID, today: date, store) -> QuotaDecision: ...
def increment_quota(user_id: UUID, today: date, store) -> None: ...
```

`store.get_user_count(user_id, day) -> int`, `store.get_global_count(day) -> int`, `store.bump(user_id, day) -> None`.

- [ ] **Step 1: Testleri yaz**

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def test_rome_rolls_to_next_local_day():
    moment = datetime(2026, 1, 15, 23, 30, tzinfo=timezone.utc)
    assert rome_today(moment) == datetime(2026, 1, 16, tzinfo=ZoneInfo("Europe/Rome")).date()

def test_user_cap():
    decision = check_quota(uuid4(), date(2026, 1, 16), FakeQuota(user=15, global_=0))
    assert decision == {"allowed": False, "reason": "user_daily"}

def test_global_cap():
    decision = check_quota(uuid4(), date(2026, 1, 16), FakeQuota(user=0, global_=40))
    assert decision == {"allowed": False, "reason": "global_daily"}

def test_increment_when_allowed():
    store = FakeQuota(user=14, global_=39)
    user_id = uuid4()
    assert check_quota(user_id, date(2026, 1, 16), store)["allowed"] is True
    increment_quota(user_id, date(2026, 1, 16), store)
    assert store.user == 15
    assert store.global_ == 40
```

`FakeQuota` sayaçları bellekte tutar. `bump` ikisini bir artırır.

- [ ] **Step 2: `rome_today` ve karar sırasını yaz**

Önce kullanıcı, sonra genel. Eşitlik kapıyı kapatır: `count >= limit`. Limit `get_settings()` değerleridir.

Supabase artışı:

```python
client.table("usage_daily").upsert(
    {"user_id": str(user_id), "day": today.isoformat(), "request_count": 1},
    on_conflict="user_id,day",
).execute()
```

Bu satır ilk günde `1` yazar ve sonraki günde mevcut sayacı ezer. Onu kullanma. Artış iki adımlıdır: oku, `request_count + 1` yaz. Aynı kalıp `global_usage_daily` için de geçerlidir. Eşzamanlı iki istek bir sayaç kaçırabilir. Bu fazın kabulü tek süreçte doğru artıştır. `bump` testte bunu kilitler.

- [ ] **Step 3: Testi geçir ve commit et**

```powershell
git commit -am "feat: enforce per-user and global daily quotas"
```

---

### Task 8.2: Geçmiş ve akış tamponu

**Files:**
- Create: `backend/app/agent/history.py`
- Create: `backend/app/agent/stream.py`
- Create: `backend/tests/test_history.py`
- Create: `backend/tests/test_stream.py`

**Interfaces:**

```python
def trim_history(messages: list[dict]) -> list[dict]: ...
def split_stream_chunk(buffer: str, incoming: str) -> tuple[str, str]: ...
```

- [ ] **Step 1: Tarihçe testi**

8 mesajın ilki ve ikincisi düşer. 600 karakterlik `content` 500 karakter olur. Diğer alanlar aynı kalır.

- [ ] **Step 2: Tampon testi**

```python
def test_holds_citation_line():
    visible, held = split_stream_chunk("", "Hello\nCITATIONS: abc")
    assert visible == "Hello"
    assert held == "CITATIONS: abc"

def test_holds_partial_marker():
    visible, held = split_stream_chunk("", "Hello\nCITAT")
    assert visible == "Hello\n"
    assert held == "CITAT"
    visible, held = split_stream_chunk(held, "IONS: abc")
    assert visible == ""
    assert held == "CITATIONS: abc"

def test_holds_refine_line():
    visible, held = split_stream_chunk("", "Done\nREFINE: permesso")
    assert visible == "Done"
    assert "REFINE" not in visible
```

- [ ] **Step 3: Tampon kuralını yaz**

Birleşik metin `buffer + incoming`. Son satır tamamlanmamışsa (`\n` ile bitmiyorsa) o parça held kalır. Tamamlanan satır `CITATIONS:` veya `REFINE:` ile başlıyorsa held’e eklenir ve görünene yazılmaz. Diğer tamamlanan satırlar görünene yazılır. Görünenin sonundaki fazla boş satır korunur; satır içeriği değiştirilmez.

- [ ] **Step 4: Commit**

```powershell
git commit -am "feat: trim history and hold back citation markers"
```

---

### Task 8.3: SSE ucu

**Files:**
- Modify: `backend/app/api/messages.py`
- Create: `backend/tests/test_sse.py`
- Modify: `backend/app/agent/graph.py`

**Interfaces:**
- `POST /api/conversations/{id}/messages` içerik tipi `text/event-stream`
- `data` satırı JSON’dur

- [ ] **Step 1: Kota testi**

`check_quota` `user_daily` döndürürse gövdede `event: error` ve `"code":"quota_user"` vardır. `groq_complete` sayacı 0 kalır. HTTP durumu `200`.

- [ ] **Step 2: Akış testi**

Sahte `complete` `"Answer text\nCITATIONS: chunk-1"` döner. Parça URL’si `https://www.poliziadistato.it/articolo/225`. Olay sırası: `token` metni `Answer text`, `citations` içinde bu URL, `done` içinde `message_id`. Store’da kullanıcı ve asistan satırları vardır. `increment_quota` bir kez çalışır.

`complete` `RuntimeError` fırlatırsa `upstream` olayı gelir, asistan satırı yoktur, kullanıcı satırı durur, kota artmaz.

- [ ] **Step 3: Geçici cümleyi kaldır**

`holding_answer` `messages.py` içinden silinir. `save_turn` grafı çağırır. Test dosyası `messages.py` metninde `not connected yet` arar ve bulamaz.

- [ ] **Step 4: Akış üreticisini yaz**

```python
def sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
```

`ChatGroq.stream` tokenleri `split_stream_chunk` içinden geçer. Görünen parça `token` olayı olur. Akış bitince held tampon `parse_generation` ile ayrılır. `REFINE` ve `retrieval_round == 0` ise ikinci `retrieve` ve ikinci `stream` aynı yanıtta sürer. İkinci turdan sonra refine yok sayılır. Atıflar `validate_citations` çıktısıdır.

Kota kontrolü üreticinin ilk satırındadır. `allowed` ise kullanıcı satırı yazılır, sonra graf çalışır, asistan satırı yazılır, en sonda `increment_quota`.

`Accept-Language` okuması: başlık `it` ile başlarsa İtalyanca kota cümlesi.

- [ ] **Step 5: Testi geçir ve commit et**

```powershell
.\.venv\Scripts\python.exe -m pytest --rootdir=backend backend/tests/test_sse.py backend/tests/test_quota.py -v
git commit -am "feat: stream a grounded answer with quota checks"
```

---

### Task 8.4: Arayüz akışı

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/components/CitationList.tsx`
- Modify: `frontend/src/components/MessageList.tsx`
- Modify: `frontend/src/components/Composer.tsx`
- Modify: `frontend/src/pages/ChatPage.tsx`

**Interfaces:**

```ts
export function streamMessage(
  id: string,
  content: string,
  handlers: {
    onToken: (text: string) => void;
    onCitations: (items: Citation[]) => void;
    onDone: () => void;
    onError: (code: string, message: string) => void;
  },
): Promise<void>
```

- [ ] **Step 1: `postMessage` silinir**

`Select-String -Path frontend/src -Pattern "postMessage"` eşleşme vermez.

- [ ] **Step 2: Okuyucuyu yaz**

`fetch` `Accept-Language` başlığına `useI18n` dilini koyar. Bu başlık `streamMessage` parametresi `lang: "en" | "it"` olur. Gövde `ReadableStream`. Baytlar `TextDecoder` ile satırlara ayrılır. `event:` ve `data:` çifti tamamlanınca JSON ayrılır. JSON bozuksa `onError("upstream", "API unreachable")`. `error` olayı `onError(code, message)` çağırır.

- [ ] **Step 3: Kartlar**

`CitationList` başlık, `fetched_at` ve `target="_blank" rel="noreferrer"` bağlantı basar. `chunk_id === ""` ise tarih satırı yoktur. `url` `https://` ile başlamıyorsa kart yoktur.

Gönderimde kullanıcı balonu hemen belirir. Asistan balonu boş başlar ve tokenlerle büyür. `quota_user` ve `quota_global` balonda `t("quota")` gösterir.

- [ ] **Step 4: Örnek sorular**

Boş sohbette üç düğme. `lang === "en"` ise:

- How do I renew a residence permit?
- How do I change my registered address?
- How do I apply for Italian citizenship by residence?

`it` ise:

- Come rinnovo il permesso di soggiorno?
- Come cambio residenza?
- Come chiedo la cittadinanza per residenza?

Tıklama `streamMessage` çağırır. Composer metnini doldurmaz.

- [ ] **Step 5: Derle ve commit et**

```powershell
cd frontend
npm run build
cd ..
git commit -am "feat: render streaming answers and official citations"
```

---

### Task 8.5: Faz çıkışı

- [ ] Kota, tampon, tarihçe ve SSE testleri geçer.
- [ ] `backend/app/api/messages.py` içinde `not connected yet` yoktur.
- [ ] `frontend/src` içinde `postMessage` yoktur.
- [ ] Yerel A korpusu ve Groq anahtarı varken bir permesso sorusu akar. Kart hostu izin listesindedir. Yenilemeden sonra aynı metin ve kart durur.
- [ ] Sayacı 15 olan kullanıcıda 16. çağrı Groq’a çıkmaz.

Faz 9: [phase-09-korpus.md](phase-09-korpus.md)
