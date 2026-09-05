# Deploy AfriDocs from GitHub Container Registry (Phase 2)

After CI is green on `main`, the **CD** workflow builds and pushes:

| Image | Used by |
|---|---|
| `ghcr.io/vunganai/afridocs-api` | API, Celery worker, Celery beat |
| `ghcr.io/vunganai/afridocs-frontend` | nginx + static Vite build |

Tags: full git SHA, short SHA (7 chars), and `latest`.

## 1. One-time GitHub setup

1. Open the repo **Settings → Actions → General**.  
   Under **Workflow permissions**, allow **Read and write** (so `GITHUB_TOKEN` can push packages), or keep the workflow `packages: write` permission (already set).
2. After the first successful CD run, open **https://github.com/Vunganai?tab=packages** and confirm both images exist.
3. For a **private** repo, packages are private. On the machine that pulls images:

```bash
echo YOUR_GITHUB_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

Use a PAT with `read:packages` (and `write:packages` only if you push by hand).

4. **Frontend build args** are baked into the image. Add repository **Secrets** (Settings → Secrets and variables → Actions):

| Secret | Example |
|---|---|
| `VITE_SUPABASE_URL` | `https://xxxx.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | anon key from Supabase |
| `VITE_API_BASE_URL` | public API URL, e.g. `https://api.example.com` or `http://YOUR_HOST:8000` |

If these secrets are missing, Docker still builds using placeholder Vite values (login/API calls will not work in that image). Re-run **CD** after adding secrets.

## 2. Deploy on a host (VM or this PC)

Keep using a real `.env` (never commit it). `REDIS_URL` / Celery URLs are overridden in compose to `redis://redis:6379/...`.

```bash
git pull
export AFRIDOCS_TAG=latest          # or a full commit SHA
# optional if your GitHub user is not vunganai:
# export GHCR_OWNER=vunganai

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

- API: `http://HOST:8000`  
- Frontend: `http://HOST:8080` (not 5173; this is nginx)  
- CORS in `.env` must include `http://HOST:8080`

Local **dev** is unchanged: `docker compose up --build` still uses `docker-compose.yml`.

## 3. Update after a merge to main

Wait for **CI** then **CD** on the Actions tab. Then on the host:

```bash
export AFRIDOCS_TAG=latest
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

## 4. Manual image publish

Actions → **CD** → **Run workflow** (`workflow_dispatch`).
