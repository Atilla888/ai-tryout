# AI-Spaces — Quick Start (Mac, Apple Silicon)

Diese Anleitung gilt für Macs mit M-Chip (M1/M2/M3/M4), auf denen Docker Desktop,
Python-venv und `npm install` bereits einmalig eingerichtet wurden.

Wenn du das Projekt zum ersten Mal auf diesem Mac startest, lies zuerst den Abschnitt
**Einmalige Einrichtung** am Ende dieser Datei.

---

## Warum 4 Terminals?

Das Projekt besteht aus mehreren Programmen, die gleichzeitig laufen müssen.
Jedes Programm belegt sein Terminal dauerhaft (es gibt den Prompt nicht zurück).

| Terminal | Programm | Was es macht |
|----------|----------|--------------|
| 1 | Postgres (Docker) | Die Datenbank |
| 2 | Backend | Die API auf Port 8000 |
| 3 | Orchestrator | Führt eingereichte Jobs aus *(optional)* |
| 4 | Frontend | Die Website auf Port 5173 |

Für einfaches Durchklicken reichen Terminals **1, 2 und 4**.
Terminal **3** nur starten, wenn Jobs wirklich ausgeführt werden sollen.

> **Tipp:** In iTerm2 oder dem Mac-Terminal mit `Cmd` + `T` neue Tabs öffnen.
> Alle Tabs starten am besten im Projektordner (`ai-spaces/`).

---

## Die Befehle

### Terminal 1 — Datenbank

Vom Projektordner (`ai-spaces/`) aus:

```bash
docker compose up -d postgres
```

Der Befehl kehrt sofort zurück (Docker läuft im Hintergrund).
Den Tab kannst du danach weiterverwenden.

### Terminal 2 — Backend (Port 8000)

```bash
cd apps/backend
../../venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal laufen lassen. Es gibt laufend Logs aus — das ist normal.

### Terminal 3 — Orchestrator *(optional, nur für Jobs)*

```bash
cd apps/orchestrator
export API_BASE_URL="http://127.0.0.1:8000"
export INTERNAL_SERVICE_TOKEN="changeme-internal-token"
export CONCURRENCY_LIMIT="2"
export POLL_INTERVAL_SECONDS="3"
../../venv/bin/python main.py
```

Terminal laufen lassen. Im Leerlauf pollt es alle paar Sekunden — normal.

### Terminal 4 — Frontend (die Website)

```bash
cd apps/frontend
npm run dev
```

Terminal laufen lassen, dann im Browser öffnen: **http://localhost:5173** 🎉

---

## Läuft es?

In einem freien Terminal:

```bash
curl http://127.0.0.1:8000/health
```

Erwartete Ausgabe:

```json
{"status":"ok"}
```

Wenn ja, ist das Backend oben. Dann einfach http://localhost:5173 im Browser aufrufen.

---

## Stoppen

Jedes laufende Terminal mit **`Ctrl` + `C`** beenden, in dieser Reihenfolge:

1. Frontend (Terminal 4)
2. Orchestrator (Terminal 3)
3. Backend (Terminal 2)

Dann die Datenbank stoppen:

```bash
docker compose stop postgres
```

---

## Wenn etwas nicht klappt

| Problem | Lösung |
|---------|--------|
| `docker: command not found` | Docker Desktop ist nicht geöffnet — `/Applications/Docker.app` starten |
| Backend startet, kann DB nicht erreichen | `.env` prüfen: `DATABASE_URL` muss `127.0.0.1` statt `localhost` enthalten |
| Website lädt, aber Daten fehlen | Terminal 2 (Backend) läuft nicht mehr |
| Job eingereicht, aber nichts passiert | Terminal 3 (Orchestrator) fehlt — starten |
| Port 8000 schon belegt | `lsof -i :8000` → PID notieren → `kill <PID>` |
| Port 5173 schon belegt | `lsof -i :5173` → PID notieren → `kill <PID>` |

---

## Einmalige Einrichtung (nur beim ersten Mal)

### 1. Docker Desktop installieren

```bash
brew install --cask docker
```

Danach Docker Desktop unter `/Applications/Docker.app` starten und die
Lizenzvereinbarung bestätigen.

### 2. Python-venv anlegen und Abhängigkeiten installieren

Vom Projektordner (`ai-spaces/`) aus:

```bash
python3 -m venv ../../venv
../../venv/bin/pip install -r apps/backend/requirements.txt
../../venv/bin/pip install -r apps/orchestrator/requirements.txt
```

### 3. `.env`-Datei anlegen

```bash
cp .env.example .env
```

Falls `.env.example` nicht existiert, Datei manuell anlegen:

```bash
cat > .env << 'EOF'
POSTGRES_USER=aispacesuser
POSTGRES_PASSWORD=aispacespass
POSTGRES_DB=aispaces

DATABASE_URL=postgresql+asyncpg://aispacesuser:aispacespass@127.0.0.1:5432/aispaces
ALEMBIC_DATABASE_URL=postgresql+psycopg://aispacesuser:aispacespass@127.0.0.1:5432/aispaces

INTERNAL_SERVICE_TOKEN=changeme-internal-token
ARTIFACT_STORAGE_ROOT=storage
AUTH_PROVIDER=dev
EOF
```

### 4. Datenbank-Migrationen einspielen

Postgres muss laufen (`docker compose up -d postgres`), dann:

```bash
cd apps/backend
../../venv/bin/alembic upgrade head
```

### 5. Frontend-Pakete installieren

```bash
cd apps/frontend
npm install
```

Danach kann die App mit den Befehlen oben gestartet werden.
