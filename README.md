# AI-Spaces

Eine Plattform für das Ausführen von KI-Jobs über eine Web-Oberfläche. Nutzer wählen einen Space (ein KI-Modell), geben ihre Eingaben ein und erhalten Ergebnisse zurück – Texte, Audio oder 3D-Modelle – ohne selbst Code schreiben zu müssen.

Entstanden im Rahmen des interdisziplinären SW-Entwicklungsprojekts an der Hochschule Hof, SS 2026.

## Überblick

Nutzer können Spaces durchsuchen und Jobs einreichen. Jeder Job läuft in einem eigenen Kubernetes-Pod und gibt Artefakte zurück, die in der App direkt angezeigt oder heruntergeladen werden können. Space-Ersteller können eigene Spaces mit eigenen Input-Formularen definieren und veröffentlichen. Admins sehen alle Spaces und Nutzer in einem Dashboard.

## Technologien

| Schicht | Technologie |
|---|---|
| Frontend | React 19, TypeScript, Vite |
| Backend | FastAPI, PostgreSQL, SQLAlchemy |
| Auth | Keycloak (OIDC / JWT) |
| Orchestrierung | Python-Orchestrator + Kubernetes Jobs |
| Infrastruktur | Kubernetes (kind lokal), Docker Compose |

## Lokal starten

Es gibt zwei Wege:

Docker Compose (am einfachsten, ca. 5 Minuten):
```bash
cp .env.example .env
docker compose up
```

Kubernetes mit kind (vollständiger Stack):
```bash
bash scripts/setup-kind.sh
```

Details dazu in [QUICKSTART.md](QUICKSTART.md).

## Projektstruktur

```
apps/
  backend/        FastAPI-Backend + Alembic-Migrationen
  frontend/       React-Frontend
  orchestrator/   Job-Orchestrator (subprocess oder K8s)
  sam3d-runner/   SAM 3D Objects Runner (Bild -> GLB)
  acestep-runner/ ACE-Step 1.5 Runner (Text -> Musik)
infra/
  k8s/            Kubernetes-Manifeste
  kind/           kind-Cluster-Config
docs/
  test-results.md     Testprotokoll (Unit, Last, Manuell)
scripts/
  setup-kind.sh   Automatisches kind-Cluster-Setup
```

## Eingebundene KI-Spaces (Mock-Modus, kein GPU nötig)

| Space | Eingabe | Ausgabe |
|---|---|---|
| ACE-Step 1.5 – Text to Music | Text-Prompt | WAV-Audiodatei |
| 3D Generator – SAM 3D Objects | Bild-Upload | GLB-3D-Modell |

## Tests ausführen

```bash
# Backend (228 Tests, 80 % Branch-Coverage)
cd apps/backend
python -m pytest tests/ --cov=app --cov-branch -q

# Frontend (24 Tests)
cd apps/frontend
npm run test
```

Vollständige Testergebnisse: [docs/test-results.md](docs/test-results.md)
