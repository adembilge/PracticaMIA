# Faz 10 — Yayın ve uçtan uca doğrulama

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tek HTTPS adresi kabuğu ve API’yi sunar. Haftalık iş A grubunu yeniden tarar ve sağlık ucunu çağırır. Tarayıcı senaryosu kayıt, soru, atıf, geçmiş, silme, kota ve dar ekranı doğrular.

**Architecture:** Tek Docker imajı Node ile kabuğu derler, Python ile API’yi çalıştırır. Cloud Run `europe-west1`, bellek `1Gi`, zaman aşımı `120`, en az `0`, en fazla `2` örnek. Servis herkese açıktır; kimliği uygulama JWT’si kontrol eder.

**Tech Stack:** Docker, Cloud Run, GitHub Actions.

**Önkoşul:** [phase-09-korpus.md](phase-09-korpus.md).

**Sonraki:** Yok. Bu son fazdır.

## Global Constraints

- Port `8080`.
- `GROQ_API_KEY` ve `SUPABASE_SERVICE_ROLE_KEY` imaj katmanına ve git deposuna yazılmaz.
- `frontend/.env.production` git’e girmez. İçinde yalnız `VITE_SUPABASE_URL` ve `VITE_SUPABASE_ANON_KEY` vardır.
- Haftalık cron `0 6 * * 1`. İş `batch a` tarar. Groq anahtarı bu işte yoktur.
- İkinci yayın belgesi açılmaz. Adımlar bu dosyadadır.

## Bu fazın dosyaları

- `Dockerfile`
- `.dockerignore`
- `.github/workflows/weekly-ingest.yml`

---

### Task 10.1: İmaj

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

**Interfaces:**
- `docker build -t practica-mia .` sonrası `8080` sağlık ve kabuk verir.

- [ ] **Step 1: `Dockerfile` yaz**

```dockerfile
FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend /app
COPY --from=web /web/dist /app/app/static
RUN pip install --no-cache-dir .
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('intfloat/multilingual-e5-small')"
ENV PORT=8080
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

`backend` paketi `/app` altında `app` ve `ingest` dizinlerini görür. `pip install .` çalışma dizini `/app` ve `pyproject.toml` oradadır. `COPY backend /app` bu dosyayı taşır.

- [ ] **Step 2: `.dockerignore` yaz**

```text
.venv
frontend/node_modules
frontend/dist
.git
.env
frontend/.env.local
backend/tests
**/__pycache__
```

`frontend/.env.production` bu listede yoktur. `.gitignore` onu depodan uzak tutar. Dosya yerelde durur ve `COPY frontend` ile imaja girer. İçinde servis rolü bulunmaz.

- [ ] **Step 3: Yerel imaj**

```powershell
docker build -t practica-mia .
docker run --rm -p 8080:8080 --env-file .env practica-mia
```

`http://localhost:8080/api/health` JSON döner. `http://localhost:8080/` kabuğu açar.

- [ ] **Step 4: Commit**

```powershell
git add Dockerfile .dockerignore
git commit -m "feat: package the shell and API in one image"
```

---

### Task 10.2: Cloud Run

**Files:**
- Yok. Bu task uzak servisi kurar.

**Interfaces:**
- Servis adı `practica-mia`. Bölge `europe-west1`. Bellek `1Gi`. Zaman aşımı `120`. `min-instances 0`. `max-instances 2`. `--allow-unauthenticated`.

- [ ] **Step 1: Üretim anonim anahtarını yaz**

`frontend/.env.production`:

```text
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon>
```

`git status` bu dosyayı göstermez. Göstermezse `.gitignore` satırı eksiktir; Faz 1’deki satır durmalıdır.

- [ ] **Step 2: Servisi yayınla**

```powershell
gcloud run deploy practica-mia --source . --region europe-west1 --memory 1Gi --timeout 120 --min-instances 0 --max-instances 2 --allow-unauthenticated
```

- [ ] **Step 3: Ortam değişkenlerini ver**

```powershell
gcloud run services update practica-mia --region europe-west1 --set-env-vars "LLM_MODEL=openai/gpt-oss-120b,EMBEDDING_MODEL=intfloat/multilingual-e5-small,SUPABASE_URL=$env:SUPABASE_URL,SUPABASE_ANON_KEY=$env:SUPABASE_ANON_KEY,SUPABASE_SERVICE_ROLE_KEY=$env:SUPABASE_SERVICE_ROLE_KEY,GROQ_API_KEY=$env:GROQ_API_KEY"
```

Değerler kabuğun ortamından okunur. Komut satırı geçmişine yapıştırmak için dosyaya yazma. `gcloud run services describe` çıktısında servis rolünün değeri düz metin görünebilir. Onu sohbet kaydına kopyalama.

- [ ] **Step 4: Sağlık**

Servis URL’sine `GET /api/health`. Beklenen `{"status":"ok","db":"ok"}`.

---

### Task 10.3: Haftalık iş

**Files:**
- Create: `.github/workflows/weekly-ingest.yml`

**Interfaces:**
- Cron `0 6 * * 1` ve `workflow_dispatch`.
- Secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SERVICE_URL`.

- [ ] **Step 1: İş akışını yaz**

```yaml
name: weekly-ingest
on:
  schedule:
    - cron: "0 6 * * 1"
  workflow_dispatch:
jobs:
  ingest:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ./backend
      - run: python -m ingest run --batch a
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
      - run: curl --fail "${{ secrets.SERVICE_URL }}/api/health"
```

- [ ] **Step 2: Elle çalıştır**

GitHub Actions içinden `workflow_dispatch`. Beklenen: yeşil iş. Sağlık gövdesinde `db` değeri `ok`.

- [ ] **Step 3: Commit**

```powershell
git add .github/workflows/weekly-ingest.yml
git commit -m "feat: recrawl batch A and wake the service every Monday"
```

---

### Task 10.4: Tarayıcı senaryosu

Kod commit’i yok. Üretim URL’sinde iki hesapla yapılır.

- [ ] **Step 1: Hesap A**

Kayıt ol. E-postayı doğrula. Gir. Boş sohbette `How do I renew a residence permit?` düğmesine tıkla. Akan metin bitsin. En az bir kart açılsın. Kartın hostu izin listesinde olsun. Sayfayı yenile. Aynı sohbet ve kart duruyor olsun.

- [ ] **Step 2: Geçmiş**

`Come cambio residenza?` gönder. Yeni sohbet aç. Kenar çubuğunda iki satır olsun. Birini yeniden adlandır, yenile, ad duruyor olsun. Diğerini sil, listeden kalksın.

- [ ] **Step 3: Hesap B**

Başka bir tarayıcı profilinde ikinci hesap aç. A’nın sohbet başlığı listede olmasın.

- [ ] **Step 4: Kaynaklar ve gizlilik**

Kaynaklar sayfasında A, B ve C grupları ve en az bir tarih görünsün. Gizlilik metni permit numarası yapıştırmamayı söylesin.

- [ ] **Step 5: Dar ekran**

Görünümü `390x844` yap. Kenar çubuğu kapalı gelsin. Menüden sohbet seçilebilsin. Composer görünür kalsın ve bir soru gönderilebilsin.

- [ ] **Step 6: Red yolları**

Oturumu kapatıp `/app` aç. Giriş sayfasına dönsün. Kota için test hesabında `usage_daily.request_count` değerini `15` yap ve bir soru gönder. Ekranda yarın yeniden deneme cümlesi görünsün. Yeni asistan satırı oluşmasın.

- [ ] **Step 7: Hesap silme**

Hesap B’yi diyalogdan sil. Aynı e-posta ile giriş olmasın. Supabase’de B’nin `conversations` satırı kalmasın.

---

### Task 10.5: Faz çıkışı

- [ ] Tek URL hem `/` hem `/api/health` verir.
- [ ] `gcloud run services describe practica-mia --region europe-west1` içinde `maxScale` `2` olur.
- [ ] Haftalık iş elle çalıştırmada yeşildir.
- [ ] Task 10.4 adımlarının her biri üretimde görülmüştür.
- [ ] `git status` içinde `.env` ve `.env.production` yoktur.
- [ ] Depo metninde servis rolü yoktur: `Select-String -Path . -Pattern "service_role" -Exclude *.md` uygulama kodunda eşleşme vermez. Eşleşme yalnız ortam örneğindeki boş anahtar adında durabilir. Değer satırı boş olmalıdır.
