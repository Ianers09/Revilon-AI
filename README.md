# Revilon AI

Revilon uses **Ollama by default**. Chat messages go from Django directly to
Ollama on your computer; there is no paid AI API or database required.

## 1. Install and start Ollama

Install Ollama from <https://ollama.com/download>, then open PowerShell:

```powershell
ollama pull llama3.2:3b
ollama serve
```

If the address is already in use, Ollama is already running. On a low-memory
computer, pull `llama3.2:1b` and set that as `OLLAMA_MODEL` instead.

## 2. Start the backend

In a second PowerShell window, from the project folder:

```powershell
Copy-Item backend/.env.example backend/.env
.venv/Scripts/Activate.ps1
pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py runserver
```

The default uses free local SQLite. Verification codes print in this terminal,
so Supabase and an email service are optional.

## 3. Start the frontend

```powershell
Set-Location frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>.

## Verify Ollama

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
ollama run llama3.2:3b "Say hello in one sentence"
```

## Free deployment reality

Ollama needs several GB of persistent RAM and model storage. Typical free web
tiers cannot host it reliably. The genuinely free option is your own computer.

For a temporary public demo, build the frontend and serve everything through
Django:

```powershell
Set-Location frontend
npm run build
Set-Location ../backend
python manage.py collectstatic --noinput
waitress-serve --listen=127.0.0.1:8000 config.wsgi:application
```

Install [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/),
then run this in another terminal:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

The generated `trycloudflare.com` URL is temporary and your computer must stay
on. A permanent always-on Ollama deployment generally needs a paid VPS or spare
machine.

## Ollama configuration

```dotenv
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
```

If Django runs in Docker but Ollama runs on the host, use
`OLLAMA_BASE_URL=http://host.docker.internal:11434`.

## Deploy online for free

The included `render.yaml` deploys the frontend and Django backend together on
Render's free web tier. AI responses use Ollama Cloud's free allowance because
a local Ollama model cannot fit in a free 512 MB Render instance.

1. Push this repository to GitHub.
2. Create a free Postgres database at Supabase and copy its pooled connection
   string (including `?sslmode=require`).
3. Create a free account at <https://ollama.com>, then create an API key in its
   settings.
4. In Render, choose **New > Blueprint**, connect this repository, and deploy
   `render.yaml`.
5. When Render asks for secrets, set `DATABASE_URL` to the Postgres connection
   string and `OLLAMA_API_KEY` to the Ollama key.

The public site will be `https://revilon-ai.onrender.com` if that service name
is available. If Render assigns a different name, update `DJANGO_ALLOWED_HOSTS`,
`CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS` in its dashboard.

Free-tier limits apply: Render sleeps after 15 idle minutes and can take about
a minute to wake; Ollama Cloud has usage limits; and database free tiers have
their own quotas. Do not commit either secret to Git.
