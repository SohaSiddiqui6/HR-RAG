# Deploy — single EC2 box, one Docker container

The most minimal production setup: one EC2 instance running the one image from
[`../Dockerfile`](../Dockerfile). No VPC work, no load balancer, no reverse proxy,
no container registry required.

The image is the **whole product** — the React SPA is built and served by FastAPI
from the same origin, so port 8000 gives you the API *and* the UI.

```
your laptop                          AWS
┌──────────────┐   docker save    ┌──────────────────────────┐
│ docker build │ ───────────────▶ │ EC2 (Amazon Linux 2023)  │
└──────────────┘   over SSH       │  docker run -p 80:8000    │──▶ http://<public-ip>
                                  └──────────┬───────────────┘
                                             │ outbound HTTPS only
             Chroma Cloud · OpenAI · Cohere · Supabase (Postgres + Storage) · Langfuse
```

All state is external (Chroma Cloud, Supabase). **The box is stateless and
disposable** — losing it costs you nothing but a redeploy.

> The deployed image is **serving-only**. `POST /api/ingest` returns **501** — the
> Docling/torch stack is left out to keep the image ~1 GB. Ingestion runs from
> your laptop against the same Chroma collection (see [§7](#7-ingesting-or-refreshing-policy-pdfs)).

---

## 0. Prerequisites

| Need | Notes |
|---|---|
| An AWS account | Free-tier eligible for the instance if it's new (< 12 months). |
| Docker Desktop, running | You already have it (`docker --version`). |
| An SSH client | Bundled with Windows 11 (`ssh` works in Git Bash / PowerShell). |
| `backend/.env`, filled in | Already done — Chroma, OpenAI, Cohere, `DATABASE_URL`, `DOCS_SOURCE=supabase`, the two `SUPABASE_*` keys, `DOCS_BUCKET`. |

You do **not** need the AWS CLI for this guide — everything is the console plus SSH.

---

## 1. Build and smoke-test the image locally

```bash
# from the repo root
docker compose up --build          # → http://localhost:8000
```

Open <http://localhost:8000> — the UI should load and answer a question. Then:

```bash
curl http://localhost:8000/api/health          # {"status":"ok"}
curl http://localhost:8000/api/workspace        # 11 documents, 350 chunks
docker compose down
```

If the build fails in the `web` stage it's a frontend TypeScript error (`tsc -b`)
— fix it in `frontend/` and rebuild. Nothing about the deploy differs.

`docker compose` names its image `hr-rag-app`. Give it the short tag the rest of
this guide uses (layers are cached, so this is instant):

```bash
docker build -t hr-rag:latest .
```

---

## 2. Produce a Docker-safe env file

`docker run --env-file` is **not** as forgiving as `docker compose` — it keeps
inline `# comments` and surrounding quotes as part of the value. Render a clean
one with the same parser the app uses:

```bash
cd backend
uv run python -c "from dotenv import dotenv_values; [print(f'{k}={v}') for k,v in dotenv_values('.env').items() if v]" > ../app.env
cd ..
```

`app.env` now has plain `KEY=value` lines. **It holds secrets** — `.gitignore`
covers it (added alongside `*.pem`); still, delete it once the box is up. Verify
it looks right:

```bash
grep -E '^(OPENAI_API_KEY|DATABASE_URL|DOCS_SOURCE|SUPABASE_URL|SUPABASE_SERVICE_ROLE_KEY|DOCS_BUCKET)=' app.env
```

Leave `COLLECTION_NAME` and `CHROMA_DATABASE` **unset** — the defaults
(`research_papers_hybrid`, `production-rag`) are what you ingested into.

---

## 3. Launch the EC2 instance (console)

**EC2 → Instances → Launch an instance**

| Field | Value |
|---|---|
| Name | `hr-rag` |
| AMI | **Amazon Linux 2023** (64-bit x86) |
| Instance type | **t3.small** (2 GB) — safe. `t3.micro` (1 GB) works for light demo use (free-tier eligible on most new accounts) but sails close to the memory limit — watch `docker stats`. |
| Key pair | Create one, e.g. `hr-rag-key`, download `hr-rag-key.pem`. |
| Network settings → **Allow SSH** | Source: **My IP** |
| Network settings → **Allow HTTP** (port 80) | Source: **Anywhere (0.0.0.0/0)** |
| Storage | 12 GiB gp3 (default 8 is a bit tight with a 1 GB image) |
| Advanced → (leave defaults) | Default VPC, auto-assign public IP is on. |

Launch. Note the **Public IPv4 address** (call it `<IP>`).

> Don't allow HTTPS/443 — there's no TLS in this setup (that's the "no reverse
> proxy" tradeoff). See [§9](#9-adding-https-later-optional) if you want it later.

Fix the key permissions so SSH will use it:

```bash
# Git Bash
chmod 600 hr-rag-key.pem
# if SSH still complains on Windows, use PowerShell:
#   icacls hr-rag-key.pem /inheritance:r /grant:r "$($env:USERNAME):(R)"
```

---

## 4. Install Docker on the instance

```bash
ssh -i hr-rag-key.pem ec2-user@<IP>
```

On the box:

```bash
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
exit                     # re-login so the group membership takes effect
```

```bash
ssh -i hr-rag-key.pem ec2-user@<IP>
docker version           # confirm the daemon responds without sudo
```

---

## 5. Ship the image and the env file

From your **laptop** (repo root):

```bash
# image: ~1 GB, gzips to ~350 MB over the wire
docker save hr-rag:latest | gzip | ssh -i hr-rag-key.pem ec2-user@<IP> "docker load"

# env file
scp -i hr-rag-key.pem app.env ec2-user@<IP>:/home/ec2-user/app.env
```

On the **box**, lock the env file down and run:

```bash
chmod 600 ~/app.env

docker run -d --name hr-rag \
  --restart unless-stopped \
  -p 80:8000 \
  --env-file /home/ec2-user/app.env \
  hr-rag:latest
```

`--restart unless-stopped` + the enabled Docker service means the container comes
back after a reboot or stop/start.

---

## 6. Smoke-test

```bash
curl http://<IP>/api/health                     # {"status":"ok"}
curl http://<IP>/api/workspace                   # 11 documents
curl -X POST http://<IP>/api/ingest              # 501 — expected (serving image)
```

Open `http://<IP>` in a browser — the SPA loads and talks to `/api` on the same
origin. That's the whole app.

Watch logs / check health while testing:

```bash
ssh -i hr-rag-key.pem ec2-user@<IP> 'docker logs -f hr-rag'
```

---

## 7. Ingesting or refreshing policy PDFs

The box can't ingest. To add or update a document:

1. Upload the PDF to the Supabase **`hr-policy-docs`** bucket (dashboard or CLI).
2. From your laptop, against the *same* Chroma Cloud collection the box queries:

   ```bash
   cd backend
   uv sync --group ingestion
   uv run python -m src.rag.ingest        # reads DOCS_SOURCE=supabase from backend/.env
   ```

The manifest lives in Postgres (`ingested_document`), so only new/changed files
are processed. The running container picks up the new chunks on the next query —
no redeploy needed.

---

## 8. Redeploying a new version

```bash
# laptop
docker build -t hr-rag:latest .
docker save hr-rag:latest | gzip | ssh -i hr-rag-key.pem ec2-user@<IP> "docker load"

# box
ssh -i hr-rag-key.pem ec2-user@<IP>
docker rm -f hr-rag
docker run -d --name hr-rag --restart unless-stopped -p 80:8000 --env-file ~/app.env hr-rag:latest
docker image prune -f
```

Save that as `~/redeploy.sh` on the box for the second half.

Changed an env value? Re-run [§2](#2-produce-a-docker-safe-env-file), `scp` the
new `app.env`, then `docker rm -f hr-rag` + `docker run …` again.

---

## 9. Operating notes

| | |
|---|---|
| **Cost** (eu-west-1, approx) | t3.small ≈ $17/mo · public IPv4 ≈ $3.65/mo · 12 GB EBS ≈ $1/mo → **~$22/mo**. `t3.micro` on free tier → just the IP + EBS ≈ **$5/mo**. |
| **Pause the bill** | `Stop` the instance when you're not demoing — you then pay only EBS + IP (~$5/mo). The public IP **changes** on stop/start unless you attach an Elastic IP. |
| **Restart the app** | `docker restart hr-rag` |
| **Region** | Use **eu-west-1** — it's where your Supabase project lives, so DB latency stays low. |
| **Supabase network restrictions** | If you've enabled them in Supabase (Settings → Database), add the EC2 public IP to the allowlist. Off by default. |
| **SSE streaming** | `POST /api/conversations/{id}/messages/stream` streams fine over plain HTTP direct to the container — nothing buffers it. |

---

## 10. Adding HTTPS later (optional, out of scope here)

Plain HTTP is the cost of "no reverse proxy". If you later need TLS, in rough
order of effort:

- **Cloudflare** in front (free) — proxy your domain, it terminates TLS, origin
  stays HTTP. Zero changes on the box.
- **Caddy** on the box — `docker run` Caddy alongside, point it at `hr-rag:8000`,
  it gets a Let's Encrypt cert automatically. ~5 lines. (This *is* a reverse
  proxy, but a 5-line one.)
- **ALB + ACM cert** — the "AWS-native" answer; needs the load balancer and a
  target group you said you didn't want.
