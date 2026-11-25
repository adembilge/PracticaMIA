# Faz 2 — Supabase şema, RLS ve JWT

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Frankfurt projesinde tablolar ve `match_chunks` durur. Geçersiz jeton `401` alır. Sağlık ucu veritabanını yoklar.

**Architecture:** Bütün okuma ve yazma Supabase servis rolü istemcisinden gider. Tarayıcı yalnız Auth kullanır. Satır güvenliği, anonim anahtar sızsa bile sohbeti ve korpusu kapatır.

**Tech Stack:** Supabase Postgres, pgvector, PyJWT, FastAPI. Pytest: `.\.venv\Scripts\python.exe -m pytest --rootdir=backend`.

**Önkoşul:** [phase-01-iskelet.md](phase-01-iskelet.md) çıkışı geçti.

**Sonraki:** [phase-03-arayuz.md](phase-03-arayuz.md) ve [phase-05-ingest-a.md](phase-05-ingest-a.md). Faz 4 de bu faza bağlıdır.

## Global Constraints

- Bölge Frankfurt. Ayrı `DATABASE_URL` yoktur.
- `embedding` sütunu `vector(384)`.
- Kullanıcı kimliği yalnız doğrulanmış JWT `sub` alanındandır. `aud` beklentisi `authenticated`.
- `401` gövdesi `{"code":"unauthorized","message":"Sign in again."}`.
- Korpus tablolarında anonim ve `authenticated` politikası yoktur. Servis rolü RLS’i geçer.
- `conversations` ve `messages` politikası `auth.uid()` ile kilitlidir.
- JWKS `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`. Önbellek 10 dakika.
- Sağlık: anahtarlar boşsa `db=unconfigured`. Yoklama başarılıysa `db=ok`. İstisnada `db=down` ve `status=degraded`.

## Bu fazın dosyaları

- `supabase/migrations/20261125120000_init.sql`
- `backend/app/db.py`
- `backend/app/auth.py`
- `backend/app/main.py` (`probe_db` gövdesi)
- `backend/tests/test_health.py`
- `backend/tests/test_auth.py`

Kullanıcı bu fazda Supabase hesabını açar. Project URL, anon key ve service role yerel `.env` dosyasına yazılır. Dosya git’e girmez.

---

### Task 2.1: Tablolar

**Files:**
- Create: `supabase/migrations/20261125120000_init.sql`

**Interfaces:**
- Produces: `conversations`, `messages`, `usage_daily`, `global_usage_daily`, `sources`, `documents`, `chunks`, `topic_profiles`

- [ ] **Step 1: Uzantı ve tabloları bu SQL ile yaz**

```sql
create extension if not exists vector;
create extension if not exists pgcrypto;

create table public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  citations jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table public.usage_daily (
  user_id uuid not null references auth.users(id) on delete cascade,
  day date not null,
  request_count int not null default 0,
  primary key (user_id, day)
);

create table public.global_usage_daily (
  day date primary key,
  request_count int not null default 0
);

create table public.sources (
  id text primary key,
  topic text not null,
  name text not null,
  batch text not null check (batch in ('a', 'b', 'c')),
  portal_url text not null,
  last_crawled_at timestamptz,
  status text not null default 'pending' check (status in ('pending', 'ok', 'error')),
  error text
);

create table public.documents (
  id uuid primary key default gen_random_uuid(),
  source_id text not null references public.sources(id) on delete cascade,
  url text not null unique,
  title text not null,
  topic text not null,
  language text not null default 'it',
  fetched_at timestamptz not null,
  content_hash text not null
);

create table public.chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  chunk_index int not null,
  heading text not null default '',
  content text not null,
  content_hash text not null,
  embedding vector(384),
  tsv tsvector generated always as (to_tsvector('italian', content)) stored,
  unique (document_id, chunk_index)
);

create table public.topic_profiles (
  topic text primary key,
  description text not null,
  portal_url text not null,
  portal_name text not null,
  embedding vector(384)
);
```

- [ ] **Step 2: İndeksleri aynı dosyaya ekle**

```sql
create index chunks_embedding_hnsw on public.chunks
  using hnsw (embedding vector_cosine_ops);
create index chunks_tsv_gin on public.chunks using gin (tsv);
create index documents_topic_idx on public.documents (topic);
create index messages_conversation_idx on public.messages (conversation_id, created_at);
```

- [ ] **Step 3: Commit**

```powershell
git add supabase/migrations/20261125120000_init.sql
git commit -m "feat: add PracticaMIA tables"
```

---

### Task 2.2: Hibrit arama işlevi

**Files:**
- Modify: `supabase/migrations/20261125120000_init.sql`

**Interfaces:**
- Produces: `public.match_chunks(vector(384), text, text, int)`
- Dönüş: `id, content, heading, url, title, topic, fetched_at, cosine_similarity, rank_score`
- `cosine_similarity >= 0.30` olmayan satır dönmez. Sıra `rank_score desc`. Limit `match_count`.
- `topic_filter` boş string ise konu süzgeci yoktur.

- [ ] **Step 1: İşlevi dosyanın sonuna yaz**

```sql
create or replace function public.match_chunks(
  query_embedding vector(384),
  query_text text,
  topic_filter text,
  match_count int
)
returns table (
  id uuid,
  content text,
  heading text,
  url text,
  title text,
  topic text,
  fetched_at timestamptz,
  cosine_similarity float,
  rank_score float
)
language sql
stable
as $$
  with semantic as (
    select
      nearest.id,
      row_number() over (order by nearest.distance) as rnk,
      (1 - nearest.distance)::float as cosine_similarity
    from (
      select
        c.id,
        (c.embedding <=> query_embedding) as distance
      from public.chunks c
      join public.documents d on d.id = c.document_id
      where c.embedding is not null
        and (topic_filter = '' or d.topic = topic_filter)
      order by c.embedding <=> query_embedding
      limit 20
    ) nearest
  ),
  lexical as (
    select
      best.id,
      row_number() over (order by best.rank desc) as rnk
    from (
      select
        c.id,
        ts_rank_cd(c.tsv, websearch_to_tsquery('italian', query_text)) as rank
      from public.chunks c
      join public.documents d on d.id = c.document_id
      where query_text <> ''
        and c.tsv @@ websearch_to_tsquery('italian', query_text)
        and (topic_filter = '' or d.topic = topic_filter)
      order by ts_rank_cd(c.tsv, websearch_to_tsquery('italian', query_text)) desc
      limit 20
    ) best
  ),
  fused as (
    select
      coalesce(s.id, l.id) as id,
      coalesce(s.cosine_similarity, 0)::float as cosine_similarity,
      (
        coalesce(1.0 / (60 + s.rnk), 0) + coalesce(1.0 / (60 + l.rnk), 0)
      )::float as rank_score
    from semantic s
    full outer join lexical l on s.id = l.id
  )
  select
    c.id, c.content, c.heading, d.url, d.title, d.topic, d.fetched_at,
    f.cosine_similarity, f.rank_score
  from fused f
  join public.chunks c on c.id = f.id
  join public.documents d on d.id = c.document_id
  where f.cosine_similarity >= 0.30
  order by f.rank_score desc
  limit match_count;
$$;
```

- [ ] **Step 2: SQL Editor’da dosyanın tamamını çalıştır**

```sql
select proname from pg_proc where proname = 'match_chunks';
```

Beklenen: bir satır.

- [ ] **Step 3: Commit**

```powershell
git commit -am "feat: add hybrid match_chunks"
```

`git commit -am` izlenmeyen dosyayı almaz. Dosya Task 2.1’de izlendiyse `-am` yeter. Değilse `git add` kullan.

---

### Task 2.3: Satır güvenliği

**Files:**
- Modify: `supabase/migrations/20261125120000_init.sql`

**Interfaces:**
- Produces: sekiz tabloda RLS açık. İstemci politikası yalnız `conversations` ve `messages` üzerindedir.

- [ ] **Step 1: Politikaları dosyanın sonuna yaz**

```sql
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.usage_daily enable row level security;
alter table public.global_usage_daily enable row level security;
alter table public.sources enable row level security;
alter table public.documents enable row level security;
alter table public.chunks enable row level security;
alter table public.topic_profiles enable row level security;

create policy conversations_own on public.conversations
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy messages_own on public.messages
  for all
  using (
    exists (
      select 1 from public.conversations c
      where c.id = conversation_id and c.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.conversations c
      where c.id = conversation_id and c.user_id = auth.uid()
    )
  );
```

`sources`, `documents`, `chunks`, `topic_profiles`, `usage_daily`, `global_usage_daily` için `create policy` yazılmaz.

- [ ] **Step 2: SQL’i Supabase’de çalıştır**

- [ ] **Step 3: Anonim anahtarla `chunks` okumayı dene**

Tarayıcıdan veya `curl` ile `apikey` ve `Authorization: Bearer <anon>` başlıklarıyla `GET {SUPABASE_URL}/rest/v1/chunks?select=id` çağır. Beklenen: boş dizi veya izin hatası. Satır içeriği dönmez.

- [ ] **Step 4: Commit**

```powershell
git commit -am "feat: lock chat rows to the signed-in user"
```

---

### Task 2.4: Servis istemcisi ve sağlık yoklaması

**Files:**
- Create: `backend/app/db.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `get_supabase() -> Client`
- Anahtar yoksa `RuntimeError("supabase is not configured")`
- `probe_db()` artık tablo okur

- [ ] **Step 1: `db.py` yaz**

```python
from supabase import Client, create_client

from app.config import get_settings


def get_supabase() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("supabase is not configured")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
```

- [ ] **Step 2: `probe_db` gövdesini değiştir**

```python
def probe_db() -> str:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return "unconfigured"
    try:
        get_supabase().table("global_usage_daily").select("day").limit(1).execute()
    except Exception:
        return "down"
    return "ok"
```

- [ ] **Step 3: Testi ayır**

Mevcut `test_health_without_database` ayarları boş taklit etsin:

```python
def test_health_without_database(monkeypatch):
    monkeypatch.setattr("app.main.probe_db", lambda: "unconfigured")
    body = TestClient(app).get("/api/health").json()
    assert body == {"status": "ok", "db": "unconfigured"}

def test_health_marks_down(monkeypatch):
    monkeypatch.setattr("app.main.probe_db", lambda: "down")
    body = TestClient(app).get("/api/health").json()
    assert body == {"status": "degraded", "db": "down"}
```

Faz 1’deki `test_probe_db_is_unconfigured_until_phase_2` silinir. Yerine anahtarsız ortamda `probe_db() == "unconfigured"` kalır. Test çalışmadan önce süreç ortamında `SUPABASE_URL` boş olmalıdır. Dolu bir kabukta testi şöyle yaz:

```python
def test_probe_unconfigured_when_keys_missing(monkeypatch):
    from app.config import Settings
    monkeypatch.setattr("app.main.get_settings", lambda: Settings(supabase_url="", supabase_service_role_key=""))
    assert probe_db() == "unconfigured"
```

- [ ] **Step 4: Canlı testi işaretle**

```python
import os
import pytest

@pytest.mark.integration
def test_probe_live():
    if not os.environ.get("SUPABASE_URL"):
        pytest.skip("supabase is not configured")
    assert probe_db() == "ok"
```

- [ ] **Step 5: Birim testleri geçir ve commit et**

```powershell
.\.venv\Scripts\python.exe -m pytest --rootdir=backend backend/tests/test_health.py -v -m "not integration"
git commit -am "feat: probe Supabase from the health endpoint"
```

---

### Task 2.5: JWT doğrulama

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/tests/test_auth.py`

**Interfaces:**
- Produces: `async def current_user_id(authorization: Annotated[str | None, Header()] = None) -> UUID`
- Produces: `def decode_access_token(token: str, jwks: dict) -> UUID`

- [ ] **Step 1: Testi yaz**

```python
import time
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.auth import decode_access_token

def _jwks_for(private_key, kid="test-key"):
    public = private_key.public_key().public_numbers()
    e = public.e.to_bytes(3, "big")
    n = public.n.to_bytes((public.n.bit_length() + 7) // 8, "big")
    def b64(raw: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    return {"keys": [{"kty": "RSA", "kid": kid, "use": "sig", "alg": "RS256", "n": b64(n), "e": b64(e)}]}

def test_decode_returns_sub():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    user_id = str(uuid4())
    token = jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 60},
        key, algorithm="RS256", headers={"kid": "test-key"},
    )
    assert str(decode_access_token(token, _jwks_for(key))) == user_id

def test_decode_rejects_other_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(
        {"sub": str(uuid4()), "aud": "authenticated", "exp": int(time.time()) + 60},
        other, algorithm="RS256", headers={"kid": "test-key"},
    )
    with pytest.raises(HTTPException) as caught:
        decode_access_token(token, _jwks_for(key))
    assert caught.value.status_code == 401
```

- [ ] **Step 2: Testi kırmızı çalıştır**

Beklenen: `app.auth` yok.

- [ ] **Step 3: `auth.py` yaz**

```python
import time
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWK

from app.config import get_settings

_CACHE: dict[str, tuple[float, dict]] = {}
UNAUTHORIZED = HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Sign in again."})


def _jwks() -> dict:
    import httpx
    settings = get_settings()
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    cached = _CACHE.get(url)
    now = time.time()
    if cached and now - cached[0] < 600:
        return cached[1]
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    payload = response.json()
    _CACHE[url] = (now, payload)
    return payload


def decode_access_token(token: str, jwks: dict) -> UUID:
    try:
        header = jwt.get_unverified_header(token)
        keys = [item for item in jwks["keys"] if item.get("kid") == header.get("kid")]
        if not keys:
            raise UNAUTHORIZED
        key = PyJWK.from_dict(keys[0]).key
        payload = jwt.decode(token, key, algorithms=[keys[0].get("alg", "RS256")], audience="authenticated")
        return UUID(payload["sub"])
    except HTTPException:
        raise
    except Exception as exc:
        raise UNAUTHORIZED from exc


async def current_user_id(authorization: Annotated[str | None, Header()] = None) -> UUID:
    if not authorization or not authorization.startswith("Bearer "):
        raise UNAUTHORIZED
    token = authorization.removeprefix("Bearer ").strip()
    return decode_access_token(token, _jwks())
```

FastAPI `HTTPException.detail` sözlük olunca gövde `{"detail": {...}}` olur. İstemci `code` alanını kökte bekler. `backend/app/main.py` içine bu işleyiciyi ekle:

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import HTTPException

@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"code": "error", "message": str(exc.detail)})
```

- [ ] **Step 4: Başlıksız uç testi**

`backend/tests/test_auth.py` sonuna:

```python
def test_missing_header_is_401():
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from app.auth import current_user_id
    from app.main import http_exception_handler

    application = FastAPI()
    application.add_exception_handler(HTTPException, http_exception_handler)

    @application.get("/who")
    async def who():
        return {"id": str(await current_user_id(authorization=None))}

    response = TestClient(application).get("/who")
    assert response.status_code == 401
    assert response.json() == {"code": "unauthorized", "message": "Sign in again."}
```

- [ ] **Step 5: Testleri geçir ve commit et**

```powershell
.\.venv\Scripts\python.exe -m pytest --rootdir=backend backend/tests/test_auth.py backend/tests/test_health.py -v -m "not integration"
git add backend/app/auth.py backend/app/main.py backend/app/db.py backend/tests/test_auth.py backend/tests/test_health.py
git commit -m "feat: verify Supabase access tokens"
```

---

### Task 2.6: Faz çıkışı

- [ ] Birim testler geçer.
- [ ] Dashboard’da sekiz tablo görünür.
- [ ] `match_chunks` bir satır döner.
- [ ] Anonim anahtar `chunks` içeriğini okumaz.
- [ ] `.env` git durumunda yoktur.

Faz 3: [phase-03-arayuz.md](phase-03-arayuz.md)
