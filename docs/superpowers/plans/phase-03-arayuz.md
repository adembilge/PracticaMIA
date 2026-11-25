# Faz 3 — Tek arayüz kabuğu

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kullanıcı aynı sitede kayıt olur, girer, dil değiştirir, gizlilik notunu okur, hesabını siler. Sohbet yüzeyi boş bir karşılama gösterir.

**Architecture:** Tarayıcı Supabase Auth ile konuşur. Sohbet ve hesap silme FastAPI’ye gider. Servis rolü tarayıcı paketine girmez.

**Tech Stack:** React 19, React Router 7, Supabase JS, FastAPI. Komutlar PowerShell.

**Önkoşul:** [phase-02-veri.md](phase-02-veri.md).

**Sonraki:** [phase-04-sohbet.md](phase-04-sohbet.md).

## Global Constraints

- Rotalar: `/`, `/register`, `/forgot`, `/privacy`, `/app`, `/app/sources`, `/app/account`.
- Oturum yokken `/app` ve altı `/` adresine gider. Oturum varken `/` adresi `/app` adresine gider.
- Arayüz dilleri `en` ve `it`. Anahtar `localStorage["practica.lang"]`. Varsayılan `en`.
- Kenar çubuğu `280px`. `800px` altında kapalı başlar.
- `DELETE /api/account` → `204`. Kimlik `current_user_id`.
- Admin silme başarısızsa `502` ve `{"code":"upstream","message":"The account could not be deleted."}`. Konuşmalar bu hatadan önce silinmiş kalır.
- Ham Supabase hata metni forma yazılmaz. Genel cümle: `Check the email and password.` / `Controlla email e password.`
- Mühür rengi yalnız birincil düğmededir.

## Bu fazın dosyaları

- `frontend/.env.example`
- `frontend/src/lib/supabase.ts`
- `frontend/src/lib/i18n.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/pages/RegisterPage.tsx`
- `frontend/src/pages/ForgotPage.tsx`
- `frontend/src/pages/PrivacyPage.tsx`
- `frontend/src/pages/ChatPage.tsx`
- `frontend/src/pages/SourcesPage.tsx`
- `frontend/src/pages/AccountPage.tsx`
- `frontend/src/components/Shell.tsx`
- `frontend/src/components/Sidebar.tsx`
- `backend/app/api/__init__.py`
- `backend/app/api/account.py`
- `backend/tests/test_account.py`
- `backend/app/main.py`

---

### Task 3.1: Sözlük ve oturum istemcisi

**Files:**
- Create: `frontend/src/lib/i18n.tsx`
- Create: `frontend/src/lib/supabase.ts`
- Create: `frontend/.env.example`

**Interfaces:**
- Produces: `useI18n(): { lang: "en" | "it"; t: (key: string) => string; setLang: (lang: "en" | "it") => void }`
- Produces: `supabase` tarayıcı istemcisi. Yalnız `VITE_SUPABASE_URL` ve `VITE_SUPABASE_ANON_KEY`.

- [ ] **Step 1: `frontend/.env.example` yaz**

```text
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

- [ ] **Step 2: `supabase.ts` yaz**

```ts
import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(url ?? "", anon ?? "");
```

Dosyada `service_role` veya `GROQ` geçmez. Bunu görev sonunda `Select-String` ile doğrula:

```powershell
Select-String -Path frontend/src/lib/supabase.ts -Pattern "service_role|GROQ"
```

Beklenen: eşleşme yok.

- [ ] **Step 3: Sözlüğü yaz**

`frontend/src/lib/i18n.tsx` içinde `copy` nesnesi bu çiftleri taşır. Birinci değer `en`, ikinci `it`.

- `appName`: PracticaMIA / PracticaMIA
- `signIn`: Sign in / Entra
- `createAccount`: Create account / Crea un account
- `email`: Email / Email
- `password`: Password / Password
- `forgot`: Forgot password / Password dimenticata
- `signOut`: Sign out / Esci
- `newChat`: New chat / Nuova chat
- `sources`: Official sources / Fonti ufficiali
- `account`: Account / Account
- `privacy`: Privacy / Privacy
- `deleteAccount`: Delete account / Elimina account
- `deleteConfirm`: This deletes your chats. / Questo elimina le tue chat.
- `send`: Send / Invia
- `emptyChat`: Ask about an Italian public procedure. / Chiedi di una procedura della pubblica amministrazione.
- `noSources`: No official pages indexed yet. / Nessuna pagina ufficiale indicizzata.
- `quota`: The daily answer capacity is used. Try again tomorrow. / La capacità giornaliera di risposte è esaurita. Riprova domani.
- `disclaimer`: PracticaMIA explains published official procedures. It is not a lawyer, a patronato, or a questura. Check the linked page. / PracticaMIA spiega procedure ufficiali pubblicate. Non è un avvocato, un patronato o una questura. Controlla la pagina collegata.
- `privacyBody`: Do not paste a permit number, codice fiscale, passport number, or a photo of a document. Chats are stored in the EU Supabase project. Deleting the account deletes the chats. / Non incollare numero di permesso, codice fiscale, numero di passaporto o foto di un documento. Le chat restano nel progetto Supabase nell'UE. Eliminare l'account elimina le chat.
- `apiDown`: API unreachable / API non raggiungibile
- `checkEmail`: Check your email / Controlla l'email
- `badCredentials`: Check the email and password. / Controlla email e password.
- `cancel`: Cancel / Annulla
- `menu`: Menu / Menu
- `close`: Close / Chiudi

Sağlayıcı:

```tsx
import { createContext, useContext, useMemo, useState } from "react";

type Lang = "en" | "it";
const KEY = "practica.lang";

const I18nContext = createContext<{
  lang: Lang;
  t: (key: string) => string;
  setLang: (lang: Lang) => void;
} | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const stored = localStorage.getItem(KEY);
  const initial: Lang = stored === "it" ? "it" : "en";
  const [lang, setLangState] = useState<Lang>(initial);
  const value = useMemo(() => ({
    lang,
    t: (key: string) => copy[key]?.[lang] ?? key,
    setLang: (next: Lang) => {
      localStorage.setItem(KEY, next);
      setLangState(next);
    },
  }), [lang]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const value = useContext(I18nContext);
  if (!value) throw new Error("I18nProvider missing");
  return value;
}
```

`copy` tipi `Record<string, { en: string; it: string }>`.

- [ ] **Step 4: Commit**

```powershell
git add frontend/.env.example frontend/src/lib/i18n.tsx frontend/src/lib/supabase.ts
git commit -m "feat: add the interface dictionary and auth client"
```

---

### Task 3.2: Rotalar

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

**Interfaces:**
- Produces: `SessionGate`. Oturum `supabase.auth.getSession` ve `onAuthStateChange` ile okunur.

- [ ] **Step 1: `App.tsx` yaz**

```tsx
import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import type { Session } from "@supabase/supabase-js";
import { I18nProvider } from "./lib/i18n";
import { supabase } from "./lib/supabase";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ForgotPage } from "./pages/ForgotPage";
import { PrivacyPage } from "./pages/PrivacyPage";
import { Shell } from "./components/Shell";
import { ChatPage } from "./pages/ChatPage";
import { SourcesPage } from "./pages/SourcesPage";
import { AccountPage } from "./pages/AccountPage";

export function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data } = supabase.auth.onAuthStateChange((_event, next) => setSession(next));
    return () => data.subscription.unsubscribe();
  }, []);

  if (session === undefined) return <p>…</p>;

  return (
    <I18nProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={session ? <Navigate to="/app" replace /> : <LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot" element={<ForgotPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/app" element={session ? <Shell /> : <Navigate to="/" replace />}>
            <Route index element={<ChatPage />} />
            <Route path="sources" element={<SourcesPage />} />
            <Route path="account" element={<AccountPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </I18nProvider>
  );
}
```

- [ ] **Step 2: `main.tsx` yalnız `App` çizer**

Faz 1’deki sağlık paragrafı kalkar. Sağlık ucu durur; kabuk onu göstermez.

- [ ] **Step 3: Commit**

```powershell
git commit -am "feat: add auth routes and the two interface languages"
```

Sayfalar henüz yokken derleme kırmızıdır. Task 3.3 ve 3.4 dosyaları oluşturur. Bu task’ın commit’i o dosyalar yazıldıktan sonra atılır. Sıra: 3.2 iskeleti, 3.3 sayfaları, sonra tek commit değil. Her task kendi dosyalarını commit eder. 3.2 commit’i sayfa dosyaları boş ihracatken yapılabilir.

Geçici olarak her sayfa dosyasına `export function LoginPage(){ return null }` koy, commit et, Task 3.3 gövdeleri doldurur. Bu geçici ihracat Task 3.3’ün ilk adımında silinir.

---

### Task 3.3: Giriş yüzeyleri

**Files:**
- Create or modify: `frontend/src/pages/LoginPage.tsx`
- Create or modify: `frontend/src/pages/RegisterPage.tsx`
- Create or modify: `frontend/src/pages/ForgotPage.tsx`

**Interfaces:**
- Consumes: `supabase.auth.signInWithPassword`, `signUp`, `resetPasswordForEmail`
- Consumes: `useI18n`

- [ ] **Step 1: `LoginPage` yaz**

Form `email` ve `password` alanlarını `label` ile bağlar. Gönderim `signInWithPassword`. Hata olursa ekranda yalnız `t("badCredentials")`. Alt linkler `/register`, `/forgot`, `/privacy`. Birincil düğmenin sınıfı `seal`.

- [ ] **Step 2: `RegisterPage` yaz**

`signUp({ email, password })`. Başarıda `t("checkEmail")`. Hata dalı yine `t("badCredentials")`.

- [ ] **Step 3: `ForgotPage` yaz**

`resetPasswordForEmail(email, { redirectTo: window.location.origin })`. Başarıda `t("checkEmail")`.

- [ ] **Step 4: Commit**

```powershell
git add frontend/src/pages/LoginPage.tsx frontend/src/pages/RegisterPage.tsx frontend/src/pages/ForgotPage.tsx
git commit -m "feat: add sign-in, registration, and password reset screens"
```

---

### Task 3.4: Kabuk

**Files:**
- Create: `frontend/src/components/Shell.tsx`
- Create: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/pages/ChatPage.tsx`
- Create: `frontend/src/pages/SourcesPage.tsx`
- Create: `frontend/src/pages/AccountPage.tsx`
- Create: `frontend/src/pages/PrivacyPage.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Produces: `Shell` bir `Outlet` ve `Sidebar` dizer.
- `ChatPage` bu fazda `t("emptyChat")` ve `t("disclaimer")` gösterir. Mesaj listesi Faz 4’te gelir.
- `SourcesPage` bu fazda `t("noSources")` gösterir. Faz 9 listeyi bağlar.

- [ ] **Step 1: `Sidebar` sırasını yaz**

1. `t("appName")` başlığı
2. Dil düğmesi. `lang === "en"` ise etiket `IT`, değilse `EN`. Tıklama diğer dile geçer.
3. `/app` linki, metin `t("newChat")`
4. Sohbet listesi için boş `ul`. Faz 4 doldurur.
5. `/app/sources`
6. `/app/account`
7. `/privacy`
8. Çıkış düğmesi: `supabase.auth.signOut()`

`800px` altında sütun `hidden` sınıfı ile kapalı başlar. `Shell` bir `menu` düğmesi ile sınıfı kaldırır. Açıkken kapatma düğmesi `t("close")` der.

- [ ] **Step 2: Sayfalar**

`PrivacyPage` bir `article` içinde `t("privacyBody")` yazar. Oturumsuz rota olduğu için `Shell` dışında durur; sayfanın üstünde `/` linki vardır.

`AccountPage` bir silme düğmesi ve `<dialog>` içerir. Diyalog metni `t("deleteConfirm")`. Onay Task 3.5’te `api.deleteAccount` çağırır. Bu task’ta onay düğmesi diyalogu kapatır ve işlevi çağırmaz. Task 3.5 bağlar.

`ChatPage`:

```tsx
export function ChatPage() {
  const { t } = useI18n();
  return (
    <section>
      <p>{t("emptyChat")}</p>
      <p className="disclaimer">{t("disclaimer")}</p>
    </section>
  );
}
```

- [ ] **Step 3: CSS**

`styles.css` sonuna:

```css
.shell { display: grid; grid-template-columns: var(--sidebar) 1fr; min-height: 100vh; }
.sidebar { background: var(--paper); border-right: 1px solid var(--line); padding: 1rem; }
.seal { background: var(--seal); color: var(--paper); border: 0; padding: 0.6rem 1rem; }
.disclaimer { font-size: 0.9rem; }
.sidebar.hidden { display: none; }
@media (max-width: 800px) {
  .shell { grid-template-columns: 1fr; }
  .sidebar { position: fixed; inset: 0 auto 0 0; width: var(--sidebar); z-index: 2; }
  .sidebar.hidden { display: none; }
}
```

- [ ] **Step 4: Derle**

```powershell
cd frontend
npm run build
```

Beklenen: çıkış kodu 0.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/components frontend/src/pages frontend/src/styles.css
git commit -m "feat: add the single application shell"
```

---

### Task 3.5: Hesap silme

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/account.py`
- Create: `backend/tests/test_account.py`
- Create: `frontend/src/lib/api.ts`
- Modify: `backend/app/main.py`
- Modify: `frontend/src/pages/AccountPage.tsx`

**Interfaces:**
- Produces: `DELETE /api/account`
- Produces: `api.deleteAccount(): Promise<void>`
- `api.ts` her çağrıda `Authorization: Bearer <access_token>` koyar. `204` dışında gövdedeki `message` alanını fırlatır.

- [ ] **Step 1: Testi yaz**

```python
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.main import http_exception_handler

def test_delete_account_removes_rows_then_user(monkeypatch):
    user_id = uuid4()
    calls = []

    class FakeAdmin:
        def delete_user(self, value):
            calls.append(("user", value))

    class FakeAuth:
        admin = FakeAdmin()

    class FakeClient:
        auth = FakeAuth()
        def table(self, name):
            calls.append(("table", name))
            return self
        def delete(self):
            return self
        def eq(self, column, value):
            calls.append((column, str(value)))
            return self
        def execute(self):
            return None

    monkeypatch.setattr("app.api.account.get_supabase", lambda: FakeClient())
    monkeypatch.setattr("app.api.account.current_user_id", lambda: user_id)

    from app.api.account import router
    application = FastAPI()
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.include_router(router)
    response = TestClient(application).delete("/api/account")
    assert response.status_code == 204
    assert ("table", "conversations") in calls
    assert ("table", "usage_daily") in calls
    assert ("user", str(user_id)) in calls
    assert calls.index(("table", "conversations")) < calls.index(("user", str(user_id)))
```

`current_user_id` async olduğu için monkeypatch async bir işlev olmalıdır:

```python
async def fake_user():
    return user_id
monkeypatch.setattr("app.api.account.current_user_id", fake_user)
```

Router bağımlılığı `Depends(current_user_id)` ise monkeypatch yolu bağımlılık çözülmeden önce modüldeki adı değiştirir. `include_router` importtan sonra yapılır. Test importu monkeypatch’ten sonra yap.

- [ ] **Step 2: `account.py` yaz**

```python
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from app.auth import current_user_id
from app.db import get_supabase

router = APIRouter()

@router.delete("/api/account", status_code=204)
async def delete_account(user_id: UUID = Depends(current_user_id)) -> None:
    client = get_supabase()
    client.table("conversations").delete().eq("user_id", str(user_id)).execute()
    client.table("usage_daily").delete().eq("user_id", str(user_id)).execute()
    try:
        client.auth.admin.delete_user(str(user_id))
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"code": "upstream", "message": "The account could not be deleted."}) from exc
```

`main.py` içinde `from app.api.account import router as account_router` ve `app.include_router(account_router)`.

- [ ] **Step 3: Testi geçir**

```powershell
.\.venv\Scripts\python.exe -m pytest --rootdir=backend backend/tests/test_account.py -v
```

- [ ] **Step 4: `api.ts` ve diyalog**

```ts
import { supabase } from "./supabase";

async function authHeader(): Promise<HeadersInit> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("Sign in again.");
  return { Authorization: `Bearer ${token}` };
}

export async function deleteAccount(): Promise<void> {
  const response = await fetch("/api/account", { method: "DELETE", headers: await authHeader() });
  if (response.status === 204) return;
  const body = await response.json();
  throw new Error(body.message ?? "Request failed");
}
```

`AccountPage` onay düğmesi `deleteAccount` çağırır, sonra `supabase.auth.signOut()` ve `navigate("/")`. İptal düğmesi `dialog.close()` çağırır ve hesabı silmez. Diyalog öğesi `useRef<HTMLDialogElement>`. Açılış `showModal()`.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/api frontend/src/lib/api.ts frontend/src/pages/AccountPage.tsx backend/app/main.py backend/tests/test_account.py
git commit -m "feat: delete the account and its chats from the shell"
```

---

### Task 3.6: Faz çıkışı

- [ ] `npm run build` geçer.
- [ ] `pytest --rootdir=backend backend/tests/test_account.py backend/tests/test_auth.py` geçer.
- [ ] Kayıt formu Supabase’e kullanıcı oluşturur.
- [ ] Girişten sonra `/app` açılır. Yenilemeden sonra oturum durur.
- [ ] Dil düğmesi yenilemeden sonra aynı dili korur.
- [ ] Görünüm `800px` iken kenar çubuğu kapalı başlar.
- [ ] Silme diyalogunda iptal hesabı yerinde bırakır.

Faz 4: [phase-04-sohbet.md](phase-04-sohbet.md)
