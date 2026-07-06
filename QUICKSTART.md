# AI-Spaces – Quick Start

Es gibt zwei Möglichkeiten, die Anwendung lokal zu starten.

Docker Compose ist der einfachere Weg und dauert ca. 5 Minuten. Kubernetes mit kind ist aufwändiger, zeigt aber den vollständigen Stack mit Keycloak-Login und echten KI-Spaces.

---

## Option A: Docker Compose

Alles läuft in Docker, kein manuelles Starten einzelner Dienste nötig.

Voraussetzungen: Docker Desktop, Python 3.12+, Node 20+

### Schritte

1. Repository klonen und .env anlegen

```bash
git clone https://gitlab.hof-university.de/atilla888/ai-spaces.git
cd ai-spaces
cp .env.example .env
```

2. Python-Abhängigkeiten installieren

Mac / Linux:
```bash
python3 -m venv venv
venv/bin/pip install -r apps/backend/requirements.txt
venv/bin/pip install -r apps/orchestrator/requirements.txt
```

Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\pip install -r apps\backend\requirements.txt
venv\Scripts\pip install -r apps\orchestrator\requirements.txt
```

3. Frontend-Abhängigkeiten installieren

```bash
cd apps/frontend
npm install
cd ../..
```

4. Dienste starten

```bash
docker compose up
```

Postgres, Keycloak, Backend und Orchestrator starten zusammen. Nach ca. 30 Sekunden ist Keycloak bereit. Dann in einem zweiten Terminal das Frontend:

```bash
cd apps/frontend
npm run dev
```

5. App öffnen: http://localhost:5173

Das Backend läuft mit `AUTH_PROVIDER=oidc`. Zum Einloggen muss einmalig ein Nutzer in Keycloak angelegt werden (siehe nächster Schritt).

6. Keycloak-Testnutzer anlegen

Diesen Block einmal ausführen, während `docker compose up` läuft:

```bash
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8080/realms/master/protocol/openid-connect/token \
  -d "client_id=admin-cli&grant_type=password&username=admin&password=admin" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST http://localhost:8080/admin/realms/ai-spaces/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","firstName":"Test","lastName":"User","enabled":true,"credentials":[{"type":"password","value":"test123","temporary":false}]}'

USER_ID=$(curl -s "http://localhost:8080/admin/realms/ai-spaces/users?username=testuser" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
ROLE=$(curl -s http://localhost:8080/admin/realms/ai-spaces/roles/admin \
  -H "Authorization: Bearer $ADMIN_TOKEN")
curl -s -X POST "http://localhost:8080/admin/realms/ai-spaces/users/$USER_ID/role-mappings/realm" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d "[$ROLE]"

echo "Fertig – Login: testuser / test123"
```

7. Datenbankmigrationen ausführen

```bash
# Mac / Linux
cd apps/backend
../../venv/bin/alembic upgrade head

# Windows
cd apps\backend
..\..\venv\Scripts\alembic upgrade head
```

Schnelltest:
```bash
curl http://localhost:8000/health
# Erwartet: {"status":"ok"}
```

Stoppen:
```bash
docker compose down
# im Frontend-Terminal: Ctrl+C
```

---

## Option B: Kubernetes mit kind

Vollständiger Stack auf einem lokalen Kubernetes-Cluster. Enthält Keycloak, beide KI-Spaces (Mock-Modus) und den echten Orchestrator.

Voraussetzungen: Docker Desktop, Python 3.12+, Node 20+, kubectl (`brew install kubectl`)

`kind` wird vom Setup-Skript automatisch installiert (Homebrew auf Mac, Binary auf Linux).

### Automatisches Setup

```bash
bash scripts/setup-kind.sh
```

Das Skript macht folgendes (dauert ca. 5–10 Minuten):
1. kind installieren (falls nicht vorhanden)
2. Cluster `ai-spaces` erstellen
3. alle Docker-Images bauen
4. Images in den Cluster laden
5. alle Dienste deployen (Postgres, Keycloak, Backend, Orchestrator, Frontend)
6. auf Ready-Status warten
7. Port-Forwards starten
8. Keycloak-Testnutzer anlegen
9. beide Mock-Spaces registrieren (ACE-Step + SAM 3D)

Am Ende erscheint:

```
Frontend:  http://localhost:5173   (login: testuser / test123)
Backend:   http://localhost:8000
Keycloak:  http://localhost:8080   (admin: admin / admin123)
```

### Port-Forwards nach Neustart

Port-Forwards überleben kein Terminal-Schließen. Wiederherstellen mit:

```bash
kubectl port-forward -n ai-spaces svc/frontend 5173:80 &
kubectl port-forward -n ai-spaces svc/backend 8000:8000 &
kubectl port-forward -n ai-spaces svc/keycloak 8080:8080 &
```

### Cluster löschen

```bash
kind delete cluster --name ai-spaces
```

---

## Häufige Probleme

| Problem | Lösung |
|---|---|
| `docker: command not found` | Docker Desktop ist nicht gestartet |
| Backend erreicht Postgres nicht | In `.env` den Host von `localhost` auf `127.0.0.1` ändern |
| Login-Redirect-Schleife | Keycloak noch nicht bereit – 30 Sekunden warten und nochmal |
| Job läuft nicht an | Orchestrator läuft nicht (bei Option A: in `docker compose up` enthalten) |
| Port bereits belegt | `lsof -i :8000` (Mac/Linux) oder `netstat -ano \| findstr :8000` (Windows) |
| kind-Cluster existiert schon | `kind delete cluster --name ai-spaces` und Skript erneut starten |

### Dev-Modus (Login überspringen)

In `.env` die Zeile `AUTH_PROVIDER=dev` setzen und das Backend neu starten. Im Dev-Modus wird jede Anfrage automatisch als Admin behandelt, Keycloak wird nicht benötigt.
