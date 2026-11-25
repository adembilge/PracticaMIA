# Faz 7 — LangGraph ajanı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sahte bir dil modeli ile graf, parçalardan cevap ve doğrulanmış atıf üretir. İkinci arama en fazla bir kez olur. Parça yoksa veya dil desteklenmiyorsa model çağrılmaz.

**Architecture:** Üç düğüm: `prepare`, `retrieve`, `generate`. Kenar, `REFINE` satırı ve `retrieval_round == 0` ise `retrieve` düğümüne döner. Hafıza bu fazda parametredir; Faz 8 son altı mesajı verir.

**Tech Stack:** LangGraph, langchain-groq. Testler ağa çıkmaz.

**Önkoşul:** [phase-06-arama.md](phase-06-arama.md).

**Sonraki:** [phase-08-akis.md](phase-08-akis.md).

## Global Constraints

- Model `openai/gpt-oss-120b`. Sıcaklık `0.1`. `max_tokens` `700`.
- `retrieval_round` yalnız `0` ve `1`.
- Desteklenmeyen dil cümlesi: `PracticaMIA answers in English and Italian. Ask your question again in one of those languages.`
- Cevaptaki URL, `parse_generation` içinde `https?://\S+` silindikten sonra kalır. Kart URL’si yalnız parça kaydındandır.
- Bilinmeyen atıf kimliği düşer.

## Bu fazın dosyaları

- `backend/app/agent/__init__.py`
- `backend/app/agent/state.py`
- `backend/app/agent/parse.py`
- `backend/app/agent/prompt.py`
- `backend/app/agent/graph.py`
- `backend/tests/test_parse.py`
- `backend/tests/test_prompt.py`
- `backend/tests/test_graph.py`

---

### Task 7.1: Durum ve ayrıştırma

**Files:**
- Create: `backend/app/agent/state.py`
- Create: `backend/app/agent/parse.py`
- Create: `backend/tests/test_parse.py`

**Interfaces:**

```python
class Citation(TypedDict):
    chunk_id: str
    title: str
    url: str
    heading: str
    fetched_at: str

class AgentState(TypedDict):
    question: str
    language: Literal["en", "it"]
    unsupported_language: bool
    topic: str
    history: list[dict]
    chunks: list[dict]
    retrieval_round: int
    refined_query: str | None
    answer: str
    citations: list[Citation]
    insufficient: bool

def parse_generation(raw: str) -> tuple[str, list[str], str | None]: ...
def validate_citations(ids: list[str], chunks: list[dict]) -> list[Citation]: ...
def strip_urls(text: str) -> str: ...
```

- [ ] **Step 1: Testleri yaz**

```python
def test_parse_citations_and_refine():
    raw = "Renew at the Questura.\nCITATIONS: aaa, bbb\nREFINE: rinnovo permesso"
    answer, ids, refine = parse_generation(raw)
    assert answer == "Renew at the Questura."
    assert ids == ["aaa", "bbb"]
    assert refine == "rinnovo permesso"

def test_parse_without_refine():
    answer, ids, refine = parse_generation("Testo.\nCITATIONS: aaa")
    assert refine is None
    assert ids == ["aaa"]

def test_parse_without_marker():
    answer, ids, refine = parse_generation("Solo testo.")
    assert answer == "Solo testo."
    assert ids == []
    assert refine is None

def test_empty_refine_is_none():
    _answer, _ids, refine = parse_generation("Testo.\nCITATIONS:\nREFINE:   ")
    assert refine is None

def test_validate_drops_unknown_ids():
    chunks = [{
        "id": "aaa",
        "title": "T",
        "url": "https://www.poliziadistato.it/articolo/225",
        "heading": "H",
        "fetched_at": "2026-11-01",
    }]
    cites = validate_citations(["aaa", "fake"], chunks)
    assert [item["chunk_id"] for item in cites] == ["aaa"]
    assert cites[0]["url"].endswith("/225")

def test_strip_urls():
    assert "evil.example" not in strip_urls("See https://evil.example/a please.")
    assert strip_urls("See https://evil.example/a please.") == "See  please."
```

- [ ] **Step 2: İşlevleri yaz**

`CITATIONS:` ve `REFINE:` satırları büyük harf ve satır başı ile aranır. Kimlikler virgül ve boşlukla ayrılır, boş parçalar düşer. `strip_urls` `re.sub(r"https?://\S+", "", text)` kullanır ve `parse_generation` cevap metnine bunu uygular. `validate_citations` URL’yi parçadan kopyalar.

- [ ] **Step 3: Testi geçir ve commit et**

```powershell
.\.venv\Scripts\python.exe -m pytest --rootdir=backend backend/tests/test_parse.py -v
git commit -am "feat: parse and validate chunk citations"
```

---

### Task 7.2: İstem

**Files:**
- Create: `backend/app/agent/prompt.py`
- Create: `backend/tests/test_prompt.py`

**Interfaces:**
- `build_prompt(state: AgentState) -> list[dict]`
- İlk öğenin `role` değeri `system`.

- [ ] **Step 1: Sistem metnini birebir yaz**

```text
You are PracticaMIA, an assistant for Italian public-administration procedures.
You answer only from the SOURCE CHUNKS below.
You explain published official procedures.
Write in {language_name}.
If the chunks do not contain the fact, say that the indexed official pages do not state it.
State a fee, deadline, form name, or office only when those words appear in a chunk.
When two chunks disagree, follow the chunk with the later fetched_at and mention that date.
Say that the local comune, questura, ASL, or INPS office can apply the national rule differently.
Do not write a URL.
After the answer, on its own line, write:
CITATIONS: id1,id2
Use only chunk ids from the chunks. If none apply, write:
CITATIONS:
If a different Italian search query would match the official pages better, add one line:
REFINE: short query in Italian
Otherwise omit REFINE.
```

`language_name` haritası: `en` → `English`, `it` → `Italian`.

- [ ] **Step 2: Kullanıcı bloğu**

Sıra sabit:

```text
HISTORY
{role}: {content}

SOURCE CHUNKS
id: {id}
title: {title}
fetched_at: {fetched_at}
heading: {heading}
content: {content}

QUESTION
{question}
```

Birden fazla geçmiş satırı ve parça, aralarında boş satırla yazılır.

- [ ] **Step 3: Test**

```python
def test_prompt_locks_language_and_chunk_id():
    state = {
        "question": "How do I renew?",
        "language": "en",
        "history": [{"role": "user", "content": "earlier"}],
        "chunks": [{"id": "chunk-1", "title": "Permesso", "fetched_at": "2026-11-01", "heading": "Rinnovo", "content": "testo"}],
    }
    messages = build_prompt(state)
    assert messages[0]["role"] == "system"
    assert "Write in English." in messages[0]["content"]
    assert "Do not write a URL." in messages[0]["content"]
    assert "id: chunk-1" in messages[1]["content"]
    assert "earlier" in messages[1]["content"]
```

- [ ] **Step 4: Commit**

```powershell
git commit -am "feat: add the grounded answer prompt"
```

---

### Task 7.3: Graf

**Files:**
- Create: `backend/app/agent/graph.py`
- Create: `backend/tests/test_graph.py`

**Interfaces:**
- `build_graph(embedder, complete, profiles, rpc) -> CompiledGraph`
- `complete(messages: list[dict]) -> str`
- `groq_complete(messages: list[dict]) -> str` testlerde çağrılmaz

- [ ] **Step 1: Düğümleri yaz**

`prepare`:
- `detect_language(question)`.
- `unsupported_language` ise `answer` sabit cümle, `insufficient True`, `citations []`. Dönüş `{"route": "end"}`.
- Değilse `route_topic`, `retrieval_round = 0`, `refined_query None`. Dönüş `{"route": "retrieve"}`.

`retrieve`:
- Sorgu, `refined_query` doluysa odur, değilse `question`.
- `retrieve_chunks`. Liste boşsa `portal_reply`, `insufficient True`, dönüş `{"route": "end"}`.
- Değilse parçalar state’e yazılır, dönüş `{"route": "generate"}`.

`generate`:
- `build_prompt`, `complete`, `parse_generation`, `validate_citations`.
- `refined_query` dolu ve `retrieval_round == 0` ise `retrieval_round = 1` ve dönüş `{"route": "retrieve"}`.
- Aksi halde dönüş `{"route": "end"}`. İkinci turda `refined_query` dolu gelse bile kenar `end` olur. Bunu düğüm, tura bakarak yapar: tur zaten `1` ise refine yok sayılır ve `refined_query` `None` yapılır.

LangGraph `StateGraph(AgentState)`. Koşullu kenarlar dönüşteki `route` anahtarını okur. `END` langgraph.graph.END.

- [ ] **Step 2: Kenar testleri**

Paylaşılan parça:

```python
CHUNK = {
    "id": "known",
    "content": "Il rinnovo si chiede in Questura.",
    "heading": "Rinnovo",
    "url": "https://www.poliziadistato.it/articolo/225",
    "title": "Permesso",
    "topic": "immigrazione",
    "fetched_at": "2026-11-01T00:00:00+00:00",
    "cosine_similarity": 0.8,
}
```

`rpc` her çağrıda `[CHUNK]` döner ve bir sayaç artırır.

1. `complete` ilk çağrıda `"Testo.\nCITATIONS: known\nREFINE: rinnovo permesso"`, ikinci çağrıda `"Testo finale.\nCITATIONS: known"`. `rpc` sayacı `2`. `complete` sayacı `2`. Cevap `Testo finale.` Atıf URL’si `/225` ile biter.
2. `complete` daima `"Testo.\nCITATIONS: known"`. `rpc` sayacı `1`.
3. `rpc` daima `[]`. `complete` sayacı `0`. Cevap Polizia URL’sini içerir.
4. Soru `Oturum iznimi nasıl yenilerim?` ve `_top_lang` taklidi `("tr", 0.99)`. `complete` sayacı `0`. Cevap `PracticaMIA answers in English and Italian.` ile başlar.

- [ ] **Step 3: `groq_complete` yaz**

```python
def groq_complete(messages: list[dict]) -> str:
    from langchain_groq import ChatGroq
    settings = get_settings()
    model = ChatGroq(
        api_key=settings.groq_api_key,
        model_name=settings.llm_model,
        temperature=0.1,
        max_tokens=700,
    )
    result = model.invoke(messages)
    return str(result.content)
```

`test_graph.py` bu adı çağırmaz. `GROQ_API_KEY` boşken graf testleri geçer.

- [ ] **Step 4: Testi geçir ve commit et**

```powershell
.\.venv\Scripts\python.exe -m pytest --rootdir=backend backend/tests/test_parse.py backend/tests/test_prompt.py backend/tests/test_graph.py -v
git commit -am "feat: add the bounded LangGraph answer graph"
```

---

### Task 7.4: Faz çıkışı

- [ ] Üç test dosyası geçer.
- [ ] Graf testi Groq uç noktasına istek atmaz.
- [ ] `fake` atıf kimliği URL üretmez.
- [ ] Üçüncü `complete` çağrısı hiçbir testte yoktur.

Faz 8: [phase-08-akis.md](phase-08-akis.md)
