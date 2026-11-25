# Faz 4 — Sohbet kalıcılığı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kullanıcı sorusunu kaydeder, sayfayı yeniler, eski sohbetini görür. Asistan satırı arşivin henüz bağlı olmadığını söyler. Bu cümle Faz 8’de kalkar.

**Architecture:** API bir `ChatStore` protokolüne yazar. Testler bellek store kullanır. Üretim store Supabase servis rolüdür ve her sorguda JWT’den gelen `user_id` filtresini koyar.

**Tech Stack:** FastAPI, Supabase, React. Pytest kökü `backend`.

**Önkoşul:** [phase-03-arayuz.md](phase-03-arayuz.md).

**Sonraki:** [phase-08-akis.md](phase-08-akis.md). Faz 5 ve 6 bu faza bağlı değildir.

## Global Constraints

- Başlık en fazla 60 karakter. `strip` sonrası boş başlık `400` ve `{"code":"bad_request","message":"Title is required."}`.
- İçerik `8000` karakteri aşarsa `400` ve `{"code":"bad_request","message":"Question is too long."}`.
- Başka kullanıcının konuşması `404` ve `{"code":"not_found","message":"Chat not found."}`.
- Geçici asistan metni, soruda `come`, `che`, `per`, `non`, `sono`, `il`, `la` sözcüklerinden en az ikisi varsa: `La domanda è salvata. L'archivio ufficiale non è ancora collegato.`
- Aksi halde: `Your question is saved. The official archive is not connected yet.`
- `citations` bu fazda `[]`.
- Başlık hâlâ `New chat` ise ilk soru başlığı, boşlukları tekilleştirilmiş ilk 60 karakter olur.
- Rota `/app/c/:conversationId`.

## Bu fazın dosyaları

- `backend/app/store.py`
- `backend/tests/memory_store.py`
- `backend/app/api/conversations.py`
- `backend/app/api/messages.py`
- `backend/tests/test_conversations.py`
- `backend/tests/test_messages.py`
- `frontend/src/lib/api.ts`
- `frontend/src/components/MessageList.tsx`
- `frontend/src/components/Composer.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/pages/ChatPage.tsx`
- `frontend/src/App.tsx`

---

### Task 4.1: Store sözleşmesi

**Files:**
- Create: `backend/app/store.py`
- Create: `backend/tests/memory_store.py`
- Create: `backend/tests/test_store.py`

**Interfaces:**
- Produces:

```python
class Conversation(TypedDict):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str

class Message(TypedDict):
    id: str
    conversation_id: str
    role: str
    content: str
    citations: list
    created_at: str

class ChatStore(Protocol):
    def insert_conversation(self, user_id: str, title: str) -> Conversation: ...
    def list_conversations(self, user_id: str) -> list[Conversation]: ...
    def get_conversation(self, user_id: str, conversation_id: str) -> Conversation | None: ...
    def rename_conversation(self, user_id: str, conversation_id: str, title: str) -> Conversation | None: ...
    def delete_conversation(self, user_id: str, conversation_id: str) -> bool: ...
    def list_messages(self, conversation_id: str) -> list[Message]: ...
    def insert_message(self, conversation_id: str, role: str, content: str, citations: list) -> Message: ...
    def touch(self, conversation_id: str, title: str | None) -> None: ...
```

- [ ] **Step 1: Bellek store testi**

A kullanıcısının satırı B’nin `list_conversations` sonucunda yoktur. `get_conversation` yanlış kullanıcıda `None` döner.

- [ ] **Step 2: `MemoryChatStore` yaz**

Sözlükler `id -> Conversation` ve `id -> list[Message]`. `id` değeri `uuid4()` stringidir. Zaman damgası `datetime.now(timezone.utc).isoformat()`. Liste `updated_at` azalan sıradadır.

- [ ] **Step 3: `SupabaseChatStore` yaz**

Her metotta `.eq("user_id", user_id)`. `insert_message` sonrası `conversations.updated_at` alanını `now()` yapar. `get_supabase()` çağrılır.

- [ ] **Step 4: `get_store() -> ChatStore`**

```python
def get_store() -> ChatStore:
    return SupabaseChatStore(get_supabase())
```

- [ ] **Step 5: Testi geçir ve commit et**

```powershell
.\.venv\Scripts\python.exe -m pytest --rootdir=backend backend/tests/test_store.py -v
git add backend/app/store.py backend/tests/memory_store.py backend/tests/test_store.py
git commit -m "feat: add a chat store with a memory double"
```

---

### Task 4.2: Konuşma uçları

**Files:**
- Create: `backend/app/api/conversations.py`
- Create: `backend/tests/test_conversations.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- `POST /api/conversations` gövde `{"title": string}` → `201` ve konuşma
- `GET /api/conversations` → kullanıcının satırları
- `PATCH /api/conversations/{id}` gövde `{"title": string}` → `200`
- `DELETE /api/conversations/{id}` → `204`

- [ ] **Step 1: Testi yaz**

`get_store` bir `MemoryChatStore` dönecek şekilde monkeypatch edilir. `current_user_id` sabit UUID döner. İkinci test başka UUID ile aynı id’yi siler ve `404` alır. Üçüncü test 61 karakterlik başlıkta `400` alır.

- [ ] **Step 2: Router’ı yaz**

```python
def clean_title(title: str) -> str:
    value = " ".join(title.split())
    if not value:
        raise HTTPException(status_code=400, detail={"code": "bad_request", "message": "Title is required."})
    if len(value) > 60:
        raise HTTPException(status_code=400, detail={"code": "bad_request", "message": "Title is too long."})
    return value
```

`user_id` daima `Depends(current_user_id)`. Gövdedeki bir `user_id` alanı okunmaz. Model:

```python
class TitleBody(BaseModel):
    title: str
    model_config = ConfigDict(extra="ignore")
```

- [ ] **Step 3: Router’ı `main.py` içine bağla, testi geçir, commit et**

```powershell
git commit -am "feat: store and list a user's chats"
```

---

### Task 4.3: Geçici cevap

**Files:**
- Create: `backend/app/api/messages.py`
- Create: `backend/tests/test_messages.py`

**Interfaces:**
- Produces: `def holding_answer(content: str) -> str`
- Produces: `def save_turn(user_id: UUID, conversation_id: str, content: str) -> Message`
- `GET /api/conversations/{id}/messages`
- `POST /api/conversations/{id}/messages` gövde `{"content": string}` → `200` ve asistan mesajı

- [ ] **Step 1: Dil testini yaz**

```python
from app.api.messages import holding_answer

def test_holding_answer_italian():
    text = holding_answer("Come posso chiedere il permesso?")
    assert text.startswith("La domanda")

def test_holding_answer_english():
    text = holding_answer("How do I renew a permit?")
    assert text.startswith("Your question")
```

`come` ve `il` iki İtalyanca sözcüktür. İngilizce cümlede bu listedeki sözcükler sözcük sınırında aranır, alt dizgi olarak değil. `re.search(rf"\b{word}\b", content.lower())`.

- [ ] **Step 2: `save_turn` testi**

POST bir kullanıcı satırı ve bir asistan satırı yazar. GET zaman sırasında döner. 8001 karakter `400`. Başlık `New chat` ise `Come cambio residenza oggi subito?` başlığı `Come cambio residenza oggi subito?` olur (60’dan kısa). 70 karakterlik tek sözcüklü soru başlığı 60 karakterde kesilir.

Kayıt sırası: kullanıcı satırı, sonra asistan satırı. Faz 8 `save_turn` içindeki asistan metnini graf çıktısı ile değiştirir. İşlev adı ve kayıt sırası aynı kalır.

- [ ] **Step 3: Uçları yaz ve testi geçir**

Konuşma `get_conversation` ile `None` ise `404`. İçerik boşsa `400` ve `{"code":"bad_request","message":"Question is required."}`.

- [ ] **Step 4: Commit**

```powershell
git commit -am "feat: save questions and a holding answer"
```

---

### Task 4.4: Arayüzde geçmiş

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/components/MessageList.tsx`
- Create: `frontend/src/components/Composer.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`
- Modify: `frontend/src/pages/ChatPage.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Produces: `listConversations`, `createConversation`, `renameConversation`, `deleteConversation`, `listMessages`, `postMessage`
- `postMessage` JSON bekler: `{id, role, content, citations}`. Faz 8 bu işlevi siler.

- [ ] **Step 1: API işlevlerini yaz**

Hepsi Task 3.5’teki `authHeader` kullanır. `postMessage` `response.json()` döner. `204` dönen silmede gövde okunmaz.

Tipler:

```ts
export type Conversation = { id: string; title: string; created_at: string; updated_at: string };
export type ChatMessage = { id: string; role: "user" | "assistant"; content: string; citations: Citation[] };
export type Citation = { chunk_id: string; title: string; url: string; heading: string; fetched_at: string };
```

- [ ] **Step 2: `App` rotasına çocuk ekle**

```tsx
<Route path="c/:conversationId" element={<ChatPage />} />
```

`/app` indeks rotası yeni sohbet oluşturmaz. `ChatPage` parametre yoksa boş karşılama ve bir `t("newChat")` düğmesi gösterir. Düğme `createConversation("New chat")` çağırır ve `/app/c/{id}` adresine gider.

- [ ] **Step 3: Composer ve liste**

`Composer` textarea’sı Enter’da gönderir. Shift+Enter satır kırar. Gönderim sırasında düğme `disabled`. `MessageList` `role` değerine göre `user` ve `assistant` sınıflarını basar. `citations` uzunluğu 0 ise kart basılmaz.

`Sidebar` `listConversations()` sonucunu çizer. Satır tıklanınca `/app/c/{id}`. Yeniden adlandırma `prompt` kullanmaz; satırdaki bir `input` ve kaydet düğmesi vardır. Silme `<dialog>` ile onaylanır, sonra `deleteConversation`.

- [ ] **Step 4: Yenileme**

`ChatPage` `useEffect` içinde `listMessages(conversationId)` çağırır. Jeton yoksa `api` işlevi hata fırlatır ve sayfa `/` rotasına `navigate` eder.

- [ ] **Step 5: Derle ve commit et**

```powershell
cd frontend
npm run build
cd ..
git commit -am "feat: show saved chats in the shell"
```

---

### Task 4.5: Faz çıkışı

- [ ] `pytest --rootdir=backend backend/tests/test_store.py backend/tests/test_conversations.py backend/tests/test_messages.py` geçer.
- [ ] İki hesap aynı başlığı açtığında her biri yalnız kendi satırını görür.
- [ ] Yeniden adlandırma yenilemeden sonra durur.
- [ ] Silinen sohbet listeden ve `GET` ucundan kalkar.
- [ ] Asistan metni arşivin bağlı olmadığını söyler.

Faz 5: [phase-05-ingest-a.md](phase-05-ingest-a.md)
