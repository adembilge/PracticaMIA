# Faz 1 — İskelet ve geliştirme ortamı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `http://localhost:5173` kabuğu açılır, `/api/health` bu kabuktan okunur, depoda gizli anahtar yoktur.

**Architecture:** Vite geliştirmede `/api` isteklerini FastAPI’ye proxyler. Üretimde aynı FastAPI süreci `backend/app/static` altındaki kabuğu sunar. Bu faz o iskeleti kurar.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Vite, React, TypeScript. Komutlar PowerShell. Kök `C:\Users\Atik\Desktop\PracticaMIA`.

**Önkoşul:** Yok. Bu ilk fazdır.

**Sonraki:** [phase-02-veri.md](phase-02-veri.md)

## Global Constraints

- Python 3.12. Node 22. Frontend paket yöneticisi npm.
- `GET /api/health` gövdesi `{"status": "ok"|"degraded", "db": "ok"|"down"|"unconfigured"}`.
- Bu fazda veritabanı yoklaması yoktur. `probe_db()` daima `"unconfigured"` döner. Faz 2 gövdeyi değiştirir.
- `.env`, `frontend/.env.local`, `frontend/.env.production` git’e girmez.
- Pytest kökü `backend` dizinidir: `.\.venv\Scripts\python.exe -m pytest --rootdir=backend`.
- Sayfa zemini `#f4f0e6`, metin `#1c1915`, kağıt `#fffdf8`, çizgi `#d9d0c1`, mühür `#8c2f2f`. Mor gradyan yok.
- Başlık yazı tipi Source Serif 4. Gövde Source Sans 3.

## Bu fazın dosyaları

- `.gitignore`
- `backend/pyproject.toml`
- `backend/app/__init__.py`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/tests/test_health.py`
- `backend/tests/test_spa.py`
- `.env.example`
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `frontend/src/vite-env.d.ts`

---

### Task 1.1: Depo ve Python paketi

**Files:**
- Create: `.gitignore`
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`

**Interfaces:**
- Produces: `pip install -e "backend[dev]"` sonrası `fastapi` ve `pytest` içe aktarılır.

- [x] **Step 1: `.gitignore` yaz**

```gitignore
.venv/
__pycache__/
.pytest_cache/
.env
.env.local
frontend/.env.local
frontend/.env.production
frontend/node_modules/
frontend/dist/
backend/app/static/
.fastembed_cache/
```

- [x] **Step 2: `backend/pyproject.toml` yaz**

```toml
[project]
name = "practica-mia"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn>=0.32",
  "pydantic-settings>=2.6",
  "httpx>=0.27",
  "trafilatura>=2.0",
  "pypdf>=5.0",
  "pyyaml>=6.0",
  "langgraph>=0.2",
  "langchain-groq>=0.2",
  "langchain-core>=0.3",
  "fastembed>=0.4",
  "supabase>=2.10",
  "pyjwt[crypto]>=2.10",
  "langdetect>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.3", "pytest-asyncio>=0.24"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]
testpaths = ["tests"]
markers = ["integration: needs Supabase, Groq, or a model download"]

[tool.setuptools.packages.find]
include = ["app*", "ingest*"]
```

- [x] **Step 3: Boş paket dosyası**

`backend/app/__init__.py` boş kalır.

- [x] **Step 4: Kur ve doğrula**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "backend[dev]"
.\.venv\Scripts\python.exe -c "import fastapi, pytest; print('ok')"
```

Beklenen son satır: `ok`.

- [x] **Step 5: Commit**

```powershell
git add .gitignore backend/pyproject.toml backend/app/__init__.py
git commit -m "chore: scaffold the Python package"
```

---

### Task 1.2: Ayarlar ve sağlık testi

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/tests/test_health.py`
- Create: `.env.example`
- Create: `backend/app/main.py`

**Interfaces:**
- Produces: `get_settings() -> Settings`
- Produces: `probe_db() -> str` bu fazda daima `"unconfigured"`
- Produces: `GET /api/health`

- [x] **Step 1: Başarısız testi yaz**

`backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient
from app.main import app, probe_db

def test_health_without_database():
    client = TestClient(app)
    body = client.get("/api/health").json()
    assert body == {"status": "ok", "db": "unconfigured"}

def test_probe_db_is_unconfigured_until_phase_2():
    assert probe_db() == "unconfigured"
```

- [x] **Step 2: Testi kırmızı çalıştır**

```powershell
.\.venv\Scripts\python.exe -m pytest --rootdir=backend backend/tests/test_health.py -v
```

Beklenen: `app.main` içe aktarılamaz.

- [x] **Step 3: `config.py` yaz**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    groq_api_key: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    llm_model: str = "openai/gpt-oss-120b"
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384
    user_daily_limit: int = 15
    global_daily_limit: int = 40


def get_settings() -> Settings:
    return Settings()
```

- [x] **Step 4: `main.py` yaz**

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.config import get_settings

app = FastAPI(title="PracticaMIA")
STATIC_DIR = Path(__file__).resolve().parent / "static"


def probe_db() -> str:
    return "unconfigured"


@app.get("/api/health")
def health() -> dict[str, str]:
    db = probe_db()
    status = "degraded" if db == "down" else "ok"
    return {"status": status, "db": db}


def register_spa(application: FastAPI) -> None:
    index = STATIC_DIR / "index.html"
    if not index.exists():
        return

    @application.get("/", include_in_schema=False)
    def spa_root():
        return FileResponse(index)

    @application.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return {"code": "not_found", "message": "Not found."}
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


register_spa(app)
```

`get_settings` bu dosyada Faz 2 yoklaması için durur. Bu fazın `probe_db` onu çağırmaz.

- [x] **Step 5: `.env.example` yaz**

```text
GROQ_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_ANON_KEY=
LLM_MODEL=openai/gpt-oss-120b
EMBEDDING_MODEL=intfloat/multilingual-e5-small
```

- [x] **Step 6: Testi yeşile çevir**

Aynı pytest komutu. Beklenen: 2 passed.

- [x] **Step 7: Commit**

```powershell
git add backend/app/config.py backend/app/main.py backend/tests/test_health.py .env.example
git commit -m "feat: add settings and the health endpoint"
```

---

### Task 1.3: Vite kabuğu

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `GET /api/health`
- Produces: ekranda `ok / unconfigured` veya `API unreachable`

- [x] **Step 1: `frontend/package.json` yaz**

```json
{
  "name": "practica-mia-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@supabase/supabase-js": "^2.49.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.1.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0"
  }
}
```

`tsconfig` içinde `"composite"` yoksa `tsc -b` hata verir. Bu faz `build` betiğini şöyle kilitler: `"build": "tsc --noEmit && vite build"`. Üstteki JSON’daki `tsc -b` satırını bu dizge ile değiştir.

- [x] **Step 2: `frontend/tsconfig.json` yaz**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true
  },
  "include": ["src"]
}
```

- [x] **Step 3: `frontend/vite.config.ts` yaz**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
```

- [x] **Step 4: `frontend/index.html` yaz**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>PracticaMIA</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600&family=Source+Serif+4:opsz,wght@8..60,600&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [x] **Step 5: Stil, giriş ve sayfa**

`frontend/src/styles.css`:

```css
:root {
  --bg: #f4f0e6;
  --ink: #1c1915;
  --paper: #fffdf8;
  --line: #d9d0c1;
  --seal: #8c2f2f;
  --sidebar: 280px;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: "Source Sans 3", sans-serif;
}
h1 { font-family: "Source Serif 4", serif; font-weight: 600; }
```

`frontend/src/vite-env.d.ts`:

```ts
/// <reference types="vite/client" />
```

`frontend/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

`frontend/src/App.tsx`:

```tsx
import { useEffect, useState } from "react";

export function App() {
  const [line, setLine] = useState("…");

  useEffect(() => {
    fetch("/api/health")
      .then((response) => response.json())
      .then((body: { status: string; db: string }) => setLine(`${body.status} / ${body.db}`))
      .catch(() => setLine("API unreachable"));
  }, []);

  return (
    <main>
      <h1>PracticaMIA</h1>
      <p>{line}</p>
    </main>
  );
}
```

- [x] **Step 6: Kur, derle, iki süreçle aç**

```powershell
cd frontend
npm install
npm run build
cd ..
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000 --app-dir backend
```

İkinci kabuk: `cd frontend; npm run dev`. Tarayıcı `http://localhost:5173` satırı `ok / unconfigured` gösterir.

- [x] **Step 7: Commit**

```powershell
git add frontend
git commit -m "feat: serve a development shell that reads health"
```

---

### Task 1.4: Statik kabuk paylaşımcısı

**Files:**
- Create: `backend/tests/test_spa.py`
- Modify: `backend/app/main.py` (Task 1.2’deki `register_spa` zaten yazılıdır; bu task onu test eder)

**Interfaces:**
- Consumes: `register_spa`
- Produces: `backend/app/static/index.html` varken `GET /` HTML döner, `GET /api/health` JSON kalır, `GET /kayit` da `index.html` döner.

- [x] **Step 1: Testi yaz**

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import register_spa, STATIC_DIR


def test_spa_serves_index_and_keeps_api(monkeypatch, tmp_path: Path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>PracticaMIA shell</html>", encoding="utf-8")
    monkeypatch.setattr("app.main.STATIC_DIR", static)
    application = FastAPI()

    @application.get("/api/health")
    def health():
        return {"status": "ok", "db": "unconfigured"}

    register_spa(application)
    client = TestClient(application)
    assert client.get("/api/health").json()["db"] == "unconfigured"
    assert "PracticaMIA shell" in client.get("/").text
    assert "PracticaMIA shell" in client.get("/kayit").text
```

`register_spa` çağrı anında `STATIC_DIR` okur. Test, monkeypatch’i `register_spa` çağrısından önce yapar. `register_spa` içindeki `index = STATIC_DIR / "index.html"` globali okuduğu için monkeypatch yolu `app.main.STATIC_DIR` doğrudur.

- [x] **Step 2: Testi çalıştır**

```powershell
.\.venv\Scripts\python.exe -m pytest --rootdir=backend backend/tests/test_spa.py -v
```

Beklenen: PASS. Kırmızıysa `register_spa` dizin varlığını çağrı anında okuyordur; testin monkeypatch’i bundan önce gelsin. Üretim `main.py` modül yüklenirken `register_spa(app)` çağırır. Test ayrı bir `FastAPI()` üstünde çağırır, bu yüzden modül yükündeki erken çağrı testi bozmaz.

- [x] **Step 3: Commit**

```powershell
git add backend/tests/test_spa.py backend/app/main.py
git commit -m "feat: fall back to the built shell outside /api"
```

---

### Task 1.5: Faz çıkışı

- [x] `.\.venv\Scripts\python.exe -m pytest --rootdir=backend backend/tests/test_health.py backend/tests/test_spa.py -v` geçer.
- [x] `npm run build` (`frontend`) çıkış kodu 0.
- [x] `git status` içinde `.env` yoktur.
- [x] Boş commit atılmaz.

Faz 2’ye geç: [phase-02-veri.md](phase-02-veri.md)
