# Testergebnisse – AI-Spaces

Projekt: AI-Spaces · Interdisziplinäres SW-Entwicklungsprojekt · Hochschule Hof · SS 2026
Stand: 2026-07-05
Schema: Foliensatz 08 (Was wird getestet / Voraussetzungen / Vorgehen / Erwartetes Ergebnis / Testergebnis)

---

## Übersicht

| Testkategorie | Werkzeug | Anzahl Tests | Ergebnis |
|---|---|---|---|
| Backend Unit-Tests | pytest 8.x | 228 passed, 7 skipped | 80 % Branch-Coverage |
| Frontend Unit-/UI-Tests | Vitest + @testing-library/react | 24 passed | alle grün |
| Last-Test | scripts/loadtest.py (httpx ASGI) | 2 x 2.000 Requests | 0 Fehler |
| Manuelle Tests | Manuelles Durchklicken | 15 Testfälle (TF-01 bis TF-15) | alle ok |

---

## 1  Backend Unit-Tests (pytest)

Werkzeug: pytest 8.x + pytest-asyncio + pytest-cov
Datenbank: SQLite In-Memory (JSONB → JSON Shim), kein laufender Server nötig
Auth: DevAuthProvider (kein Keycloak nötig), Rollen werden per app.dependency_overrides überschrieben

Ausführung:
```
cd apps/backend
python -m pytest tests/ --cov=app --cov-branch -q
```

Ergebnis:
```
228 passed, 7 skipped  (4,02 s)
Branch-Coverage gesamt: 80 %  (Statement-Miss 204/1193, Branch-Miss 20/182)
```

### Testmodule und Testfälle

#### 1.1  tests/test_validation.py – 30 Tests

| # | Was wird getestet | Voraussetzungen | Vorgehen | Erwartetes Ergebnis | Testergebnis |
|---|---|---|---|---|---|
| 1 | Gültige Minimalconfig | Space-Objekt mit einem text-Input und Container-Image | validate_space_config() aufrufen | valid=True, errors=[] | ok |
| 2 | Fehlender inputs-Key | ui_config ohne inputs | Validation | Fehler: 'inputs' key is required | ok |
| 3 | inputs kein Array | inputs: "string" | Validation | Fehler: 'inputs' must be a list | ok |
| 4 | Leeres inputs-Array | inputs: [] | Validation | Fehler: At least one input is required | ok |
| 5 | Ungültiger Feldname (1abc) | Input mit Name 1abc | Validation | Fehler: Name muss mit Buchstabe/Underscore beginnen | ok |
| 6 | Doppelter Feldname | Zwei Inputs mit gleichem Name | Validation | Fehler: Duplicate input name | ok |
| 7 | Unbekannter Typ | type: "unknown" | Validation | Fehler: type must be one of … | ok |
| 8 | select ohne options | type: "select" ohne options | Validation | Fehler: options is required | ok |
| 9 | select mit leerem options-Array | options: [] | Validation | Fehler: options must be non-empty | ok |
| 10 | select mit ungültigem Eintrag | options: [""] | Validation | Fehler: entries must be non-empty strings | ok |
| 11 | Fehlendes label | Input ohne label | Validation | Fehler: label is required | ok |
| 12 | required kein Boolean | required: "yes" | Validation | Fehler: required must be a boolean | ok |
| 13 | Fehlendes Container-Image | container_image: "" | Validation | Fehler: container_image must not be empty | ok |
| 14 | timeout_seconds kein Integer | timeout_seconds: "300" | Validation | Fehler: must be an integer | ok |
| 15 | timeout_seconds außerhalb Bereich | timeout_seconds: 0 | Validation | Fehler: must be between 1 and 86400 | ok |
| 16 | memory_mb kein Integer | memory_mb: "512" | Validation | Fehler: must be an integer | ok |
| 17 | memory_mb außerhalb Bereich | memory_mb: 63 | Validation | Fehler: must be between 64 and 65536 | ok |
| 18–30 | Weitere Grenzfälle | Korrekte Typen text, image_upload, audio_upload, number, select | Validation | Jeweils valid=True oder gezielte Fehlermeldung | ok |

---

#### 1.2  tests/test_spaces_api.py – 8 Tests

| # | Was wird getestet | Voraussetzungen | Vorgehen | Erwartetes Ergebnis | Testergebnis |
|---|---|---|---|---|---|
| 1 | GET /spaces – leer | Keine Spaces in DB | GET /spaces | [] | ok |
| 2 | GET /spaces – nur veröffentlichte, öffentliche | Mix aus Draft/Published und Public/Private | GET /spaces | Nur PUBLISHED + PUBLIC erscheinen | ok |
| 3 | GET /spaces – mehrere Spaces | 3 veröffentlichte Spaces | GET /spaces | Alle 3 im Response | ok |
| 4 | GET /spaces/{id} – 200 | Space vorhanden | GET /spaces/{id} | HTTP 200, korrekte Daten | ok |
| 5 | GET /spaces/{id} – 404 | Unbekannte ID | GET /spaces/{id} | HTTP 404 | ok |
| 6 | GET /spaces/{id} – privater Space direkt abrufbar | PRIVATE Space | GET /spaces/{id} | HTTP 200 (ID-Lookup ignoriert Sichtbarkeit) | ok |
| 7 | POST /spaces – 201 | Gültiger Payload | POST /spaces | HTTP 201, Space in DB | ok |
| 8 | POST /spaces – 409 Duplikat | Space mit gleichem Slug | POST /spaces | HTTP 409 Conflict | ok |

---

#### 1.3  tests/test_creator_api.py – 13 Tests

| # | Was wird getestet | Voraussetzungen | Vorgehen | Erwartetes Ergebnis | Testergebnis |
|---|---|---|---|---|---|
| 1 | POST /creator/spaces – Erstellen | Eingeloggt als creator | POST /creator/spaces | HTTP 201 | ok |
| 2 | POST /creator/spaces – Duplikat | Space mit gleichem Slug existiert | POST /creator/spaces | HTTP 409 | ok |
| 3 | GET /creator/spaces – leer | Keine eigenen Spaces | GET /creator/spaces | [] | ok |
| 4 | GET /creator/spaces – eigene Spaces | 2 eigene Spaces | GET /creator/spaces | Beide im Response | ok |
| 5 | PATCH /creator/spaces/{id} – 200 | Eigener Space | PATCH mit neuem Namen | HTTP 200, Name aktualisiert | ok |
| 6 | PATCH /creator/spaces/{id} – 404 | Unbekannte ID | PATCH | HTTP 404 | ok |
| 7 | PATCH /creator/spaces/{id} – 403 | Fremder Space | PATCH als anderer User | HTTP 403 | ok |
| 8 | POST /creator/spaces/{id}/validate – gültig | Gültige Config | Validate | HTTP 200, valid: true | ok |
| 9 | POST /creator/spaces/{id}/validate – ungültig | Fehlerhafte Config | Validate | HTTP 200, Fehlerliste | ok |
| 10 | POST /creator/spaces/{id}/validate – 404 | Unbekannte ID | Validate | HTTP 404 | ok |
| 11 | POST /creator/spaces/{id}/validate – 403 | Fremder Space | Validate als anderer User | HTTP 403 | ok |
| 12 | POST /creator/spaces – end_user geblockt | User hat Rolle end_user | POST /creator/spaces | HTTP 403 | ok |
| 13 | GET /creator/spaces – end_user geblockt | User hat Rolle end_user | GET /creator/spaces | HTTP 403 | ok |

---

#### 1.4  tests/test_admin_api.py – 13 Tests

| # | Was wird getestet | Voraussetzungen | Vorgehen | Erwartetes Ergebnis | Testergebnis |
|---|---|---|---|---|---|
| 1 | GET /admin/spaces – leer | Keine Spaces | GET /admin/spaces | [] | ok |
| 2 | GET /admin/spaces – alle Spaces | Mix verschiedener Spaces | GET /admin/spaces | Alle sichtbar (inkl. Private) | ok |
| 3 | PATCH /admin/spaces/{id} – Status ändern | Space vorhanden | PATCH mit neuem Status | HTTP 200 | ok |
| 4 | PATCH /admin/spaces/{id} – Visibility ändern | Space vorhanden | PATCH mit neuer Visibility | HTTP 200 | ok |
| 5 | PATCH /admin/spaces/{id} – 404 | Unbekannte ID | PATCH | HTTP 404 | ok |
| 6 | PATCH /admin/spaces/{id} – 403 non-admin | User ist kein Admin | PATCH | HTTP 403 | ok |
| 7 | DELETE /admin/spaces/{id} – 204 | Space vorhanden | DELETE | HTTP 204 | ok |
| 8 | DELETE /admin/spaces/{id} – 404 | Unbekannte ID | DELETE | HTTP 404 | ok |
| 9 | DELETE /admin/spaces/{id} – 403 non-admin | User ist kein Admin | DELETE | HTTP 403 | ok |
| 10 | GET /admin/users – leer | Keine User in DB | GET /admin/users | [] | ok |
| 11 | GET /admin/users – enthält Seeded-User | User in DB | GET /admin/users | User im Response | ok |
| 12 | GET /admin/users – 403 non-admin | User ist kein Admin | GET /admin/users | HTTP 403 | ok |
| 13 | Admin sieht alle Spaces inkl. fremder | Spaces verschiedener Owner | GET /admin/spaces | Alle gelistet | ok |

---

#### 1.5  tests/test_users_service.py – 8 Tests

| # | Was wird getestet | Voraussetzungen | Vorgehen | Erwartetes Ergebnis | Testergebnis |
|---|---|---|---|---|---|
| 1 | list_users() – leer | Keine User | list_users() | [] | ok |
| 2 | list_users() – alle | 2 User in DB | list_users() | Beide zurückgegeben | ok |
| 3 | get_by_subject() – gefunden | User in DB | get_by_subject(subject, idp) | User-Objekt | ok |
| 4 | get_by_subject() – nicht gefunden | Kein passender User | get_by_subject() | None | ok |
| 5 | get_by_subject() – falscher IDP | User mit anderem IDP | get_by_subject() | None | ok |
| 6 | get_or_create() – neuer User | User existiert nicht | get_or_create() | Neues User-Objekt | ok |
| 7 | get_or_create() – existierender User | User bereits in DB | get_or_create() | Bestehenden User zurückgegeben | ok |
| 8 | get_or_create() – Race Condition | IntegrityError beim Insert (Mock) | get_or_create() | Fallback auf SELECT, kein Fehler | ok |

---

#### 1.6  Weitere Testmodule

| Modul | Tests | Inhalt |
|---|---|---|
| tests/test_jobs_api.py | 13 | Job-CRUD: Erstellen, Status-Übergänge, Cancel, interne Endpunkte |
| tests/test_job_state_transitions.py | 36 | Zustandsmaschine: alle erlaubten/verbotenen Statusübergänge |
| tests/test_job_transitions.py | 13 | Orchestrator-Übergänge (STARTING→RUNNING→SUCCEEDED/FAILED) |
| tests/test_history.py | 9 | /me/history – Liste, Delete 204, 403 für fremde Jobs, 404 |
| tests/test_artifacts.py | 5 | Artefakt-Upload, -Download, Content-Type-Handling |
| tests/test_auth.py | 12 | DevAuthProvider, OIDC-Token-Parsing, Rollen-Extraktion |
| tests/test_fake_runner.py | 2 | Fake-Runner SDK-Roundtrip (DEV_MODE) |
| tests/test_maintenance.py | 4 | Cleanup-Job: veraltete Jobs abschließen |
| tests/integration/test_job_flow.py | 16 | End-to-End: Job anlegen → Runner → Artefakt → succeed |

---

## 2  Frontend Unit-/UI-Tests (Vitest)

Werkzeug: Vitest + @testing-library/react + jsdom
Mocks: API-Module gemockt via vi.mock('../api/api'), OIDC via vi.mock('react-oidc-context')

Ausführung:
```
cd apps/frontend
npm run test
```

Ergebnis:
```
Test Files  5 passed (5)
Tests       24 passed (24)
Duration    6,36 s
```

### Testsuiten und Testfälle

#### 2.1  History.test.tsx – 9 Tests (Seite: /history)

| # | Was wird getestet | Voraussetzungen | Vorgehen | Erwartetes Ergebnis | Testergebnis |
|---|---|---|---|---|---|
| 1 | Ladezustand → Jobs gerendert | fetchMyHistory gibt Jobs zurück | Seite mounten | Zuerst Spinner, dann Job-Liste | ok |
| 2 | Plural-Label bei mehreren Jobs | 2 Jobs im Mock | Seite mounten | "2 jobs in your history" | ok |
| 3 | Fehlermeldung bei API-Fehler | fetchMyHistory wirft Fehler | Seite mounten | Fehlermeldung sichtbar | ok |
| 4 | Empty State | fetchMyHistory gibt [] zurück | Seite mounten | "No jobs in your history yet" | ok |
| 5 | Status-Pill für fehlgeschlagenen Job | Job mit status: FAILED | Seite mounten | Rote Status-Pill | ok |
| 6 | Sortierung: neueste zuerst | 2 Jobs mit verschiedenen Zeitstempeln | Seite mounten | Neuerer Job oben | ok |
| 7 | Delete bestätigt → Job verschwindet | Confirm-Dialog akzeptiert | Delete-Button klicken | Job nicht mehr sichtbar | ok |
| 8 | Delete abgebrochen → Job bleibt | Confirm-Dialog abgelehnt | Delete-Button klicken, Cancel | Job bleibt sichtbar | ok |
| 9 | Delete fehlgeschlagen → Alert | deleteMyHistory wirft Fehler | Delete-Button klicken | Fehlermeldung erscheint | ok |

---

#### 2.2  Spaces.test.tsx – 5 Tests (Seite: /spaces, Submit-Fluss)

| # | Was wird getestet | Voraussetzungen | Vorgehen | Erwartetes Ergebnis | Testergebnis |
|---|---|---|---|---|---|
| 1 | Ladezustand → Space-Liste | fetchSpaces gibt 2 Spaces zurück | Seite mounten | Spinner dann Karten | ok |
| 2 | Suche nach Space-Name | 2 Spaces, Suchbegriff eingeben | Suchfeld befüllen | Nur passende Spaces gezeigt | ok |
| 3 | Filter nach Task-Type | Spaces mit verschiedenen Task-Types | Task-Type-Chip klicken | Nur Spaces mit diesem Typ | ok |
| 4 | Fehlerzustand | fetchSpaces wirft Fehler | Seite mounten | Fehlermeldung sichtbar | ok |
| 5 | Formular abschicken → JobDetail | Eingabe befüllt, Submit | Submit-Button klicken | Navigation zu /jobs/{id} | ok |

---

#### 2.3  SpaceEditor.test.tsx – 4 Tests (Seite: /creator/spaces)

| # | Was wird getestet | Voraussetzungen | Vorgehen | Erwartetes Ergebnis | Testergebnis |
|---|---|---|---|---|---|
| 1 | Slug aus Name auto-generiert | Neues Space-Formular | Name eingeben | Slug wird automatisch befüllt | ok |
| 2 | "Save as Draft" sendet korrekten Payload | Formular befüllt | Save-Button klicken | createSpace() mit erwarteten Daten aufgerufen | ok |
| 3 | Ungültiges runner_config JSON | runner_config-Feld mit "not json" | Save klicken | Fehlermeldung, kein API-Aufruf | ok |
| 4 | Publish-Validierungsfehler → DRAFT | Validate gibt Fehler zurück | Publish klicken | Status bleibt DRAFT, Fehler gezeigt | ok |

---

#### 2.4  JobDetail.test.tsx – 4 Tests (Seite: /jobs/{id})

| # | Was wird getestet | Voraussetzungen | Vorgehen | Erwartetes Ergebnis | Testergebnis |
|---|---|---|---|---|---|
| 1 | Warteschlangen-Position angezeigt | Job mit status: QUEUED, Position 3 | Seite mounten | "Queue position: 3" sichtbar | ok |
| 2 | Polling während RUNNING | Job wechselt QUEUED→RUNNING→SUCCEEDED | Seite mounten, Timers voranschreiten | Fortschrittsbalken → Ergebnis | ok |
| 3 | Ergebnis nach SUCCEEDED | Job mit Artefakten | Seite mounten nach Erfolg | Artefakte downloadbar gelistet | ok |
| 4 | Job abbrechen | Laufender Job | Cancel-Button klicken | cancelJob() aufgerufen, Bestätigung | ok |

---

#### 2.5  Home.test.tsx – 2 Tests (Startseite /)

| # | Was wird getestet | Voraussetzungen | Vorgehen | Erwartetes Ergebnis | Testergebnis |
|---|---|---|---|---|---|
| 1 | Validierung: Pflichtfeld leer | Space mit required input | Submit ohne Eingabe | Fehlermeldung, kein Job | ok |
| 2 | Erfolgreiche Eingabe → Navigation | Felder befüllt | Submit | submitJob() aufgerufen, Weiterleitung | ok |

---

## 3  Last-Test (Load Test)

Werkzeug: scripts/loadtest.py – httpx ASGI-Transport gegen In-Memory-SQLite (kein echter Netzwerk-Hop)
Konfiguration: 2.000 Requests, 50 gleichzeitige Verbindungen
Seeded Daten: 5 veröffentlichte Public-Spaces

Ausführung:
```
cd apps/backend
python -m scripts.loadtest
```

### LT-01 – GET /health (Health-Check-Endpunkt)

| Was wird getestet | Voraussetzungen | Vorgehen | Erwartetes Ergebnis | Testergebnis |
|---|---|---|---|---|
| Durchsatz des Health-Endpunkts bei 50 gleichzeitigen Clients | Backend ASGI in-process, SQLite In-Memory | 2.000 GET /health Requests mit Concurrency 50 | Durchsatz > 500 req/s, 0 Fehler, p99 < 10 ms | ok |

Messwerte (2026-07-05):

| Metrik | Wert |
|---|---|
| Requests gesamt | 2.000 |
| Durchsatz | 1.894 req/s |
| Fehler | 0 |
| Latenz p50 | 0,5 ms |
| Latenz p95 | 0,6 ms |
| Latenz p99 | 0,7 ms |
| Latenz min / mean / max | 0,5 / 0,5 / 26,9 ms |

---

### LT-02 – GET /spaces (Spaces-Liste mit DB-Abfrage)

| Was wird getestet | Voraussetzungen | Vorgehen | Erwartetes Ergebnis | Testergebnis |
|---|---|---|---|---|
| Durchsatz des Spaces-Endpunkts (ORM-Abfrage + JSON-Serialisierung) bei 50 gleichzeitigen Clients | 5 Spaces in In-Memory-SQLite | 2.000 GET /spaces Requests mit Concurrency 50 | Durchsatz > 100 req/s, 0 Fehler | ok |

Messwerte (2026-07-05):

| Metrik | Wert |
|---|---|
| Requests gesamt | 2.000 |
| Durchsatz | 517 req/s |
| Fehler | 0 |
| Latenz p50 | 88,6 ms |
| Latenz p95 | 116,9 ms |
| Latenz p99 | 125,9 ms |
| Latenz min / mean / max | 38,3 / 88,6 / 130,1 ms |

Die höhere Latenz bei /spaces im Vergleich zu /health kommt von der SQLAlchemy ORM-Abfrage mit Visibility-Filter und anschließender JSON-Serialisierung. Unter echter PostgreSQL mit Netzwerk-Hop sind die Werte produkionsrelevanter.

---

## 4  Manuelle Tests (Manuelles Durchklicken)

Testumgebung:
- Backend: uvicorn app.main:app auf Port 8000, AUTH_PROVIDER=dev
- Frontend: npm run dev auf Port 5173
- Datenbank: PostgreSQL via Docker (docker compose up -d postgres)
- Für Rollen-Tests: Keycloak (docker compose up -d keycloak), Testuser admin/admin123
- Datum der Durchführung: 2026-06-23 / 2026-07-05

---

### 4.1  Space anlegen und als Draft speichern

#### TF-01 (Positiv) – Space als Entwurf speichern

| Feld | Inhalt |
|---|---|
| Was wird getestet | Anlegen eines neuen Space und Speichern als Draft (Creator) |
| Voraussetzungen | Angemeldet als space_creator oder admin; auf /creator → "New Space" |
| Vorgehen | Name "Image Magic" eingeben (Slug wird automatisch zu image-magic), Container-Image ghcr.io/org/model:latest eingeben, mindestens ein Input-Feld definieren, "Save as Draft" klicken |
| Erwartetes Ergebnis | HTTP 201; Weiterleitung auf die Edit-Seite; Status-Badge zeigt DRAFT; Space taucht in "My Spaces" auf |
| Testergebnis | ok |

#### TF-02 (Fehlerfall) – Pflichtfeld leer

| Feld | Inhalt |
|---|---|
| Was wird getestet | Speichern mit leerem Pflichtfeld (z. B. Container-Image oder Name) |
| Voraussetzungen | Wie TF-01, "New Space" geöffnet |
| Vorgehen | Name leer lassen (oder Container-Image leer), "Save as Draft" klicken |
| Erwartetes Ergebnis | Es wird kein gültiger Space angelegt; die fehlenden Pflichtangaben fallen spätestens beim Publish-Validate auf (TF-04). Die Anwendung zeigt einen Fehler; kein 500er |
| Testergebnis | ok |

---

### 4.2  Space mit ungültiger Config publizieren

#### TF-03 (Positiv) – Gültige Config publizieren

| Feld | Inhalt |
|---|---|
| Was wird getestet | Veröffentlichen eines Space mit gültiger ui_config/runner_config |
| Voraussetzungen | Draft-Space mit gültigem Input-Feld (Name passt zu ^[A-Za-z_][A-Za-z0-9_]*$, Typ, Label), gültigem Container-Image und runner_config {} |
| Vorgehen | Auf der Edit-Seite "Publish" klicken |
| Erwartetes Ergebnis | Validierung meldet "Configuration is valid"; Status wechselt auf PUBLISHED; Space erscheint im öffentlichen Space-Hub |
| Testergebnis | ok |

#### TF-04 (Fehlerfall) – Ungültige Config publizieren

| Feld | Inhalt |
|---|---|
| Was wird getestet | Publish mit ungültiger Konfiguration (z. B. kein Input-Feld, ungültiger Feldname 1abc, select ohne Options, oder leeres Container-Image) |
| Voraussetzungen | Draft-Space mit absichtlich fehlerhafter Config |
| Vorgehen | "Publish" klicken |
| Erwartetes Ergebnis | Validierungsfehler wird angezeigt (Liste der field/message-Einträge); Space bleibt im Status DRAFT; pro betroffenem Feld erscheint eine Fehlermarkierung |
| Testergebnis | ok |

#### TF-05 (Fehlerfall) – Ungültiges runner_config-JSON

| Feld | Inhalt |
|---|---|
| Was wird getestet | runner_config-Textfeld mit ungültigem JSON |
| Voraussetzungen | Edit-Seite eines Space geöffnet |
| Vorgehen | In runner_config ungültigen Text (z. B. not json) eingeben, "Save as Draft"/"Publish" klicken |
| Erwartetes Ergebnis | Meldung "runner_config must be a valid JSON object"; es wird keine API-Anfrage gesendet |
| Testergebnis | ok |

---

### 4.3  Job absenden und Ergebnis abrufen

#### TF-06 (Positiv) – Job absenden und Ergebnis sehen

| Feld | Inhalt |
|---|---|
| Was wird getestet | Absenden eines Jobs für einen veröffentlichten Space und Abruf des Ergebnisses |
| Voraussetzungen | Veröffentlichter, öffentlicher Space mit mind. einem Input; angemeldeter Nutzer |
| Vorgehen | Space im Hub öffnen, Eingabefelder ausfüllen, "Submit" klicken; auf der Job-Seite den Status verfolgen bis SUCCEEDED; Artefakte ansehen/herunterladen |
| Erwartetes Ergebnis | HTTP 201 mit status=QUEUED und Queue-Position; Job durchläuft STARTING→RUNNING→SUCCEEDED; Ausgabe-Artefakte werden gelistet und sind als Preview/Download abrufbar |
| Testergebnis | ok |

#### TF-07 (Fehlerfall) – Leere/ungültige Eingabe

| Feld | Inhalt |
|---|---|
| Was wird getestet | Absenden ohne Pflichteingabe |
| Voraussetzungen | Space mit einem als required markierten Input |
| Vorgehen | Pflichtfeld leer lassen, "Submit" klicken |
| Erwartetes Ergebnis | Validierungshinweis (z. B. "… is required"); es wird kein Job angelegt |
| Testergebnis | ok |

---

### 4.4  Job abbrechen

#### TF-08 (Positiv) – Job in der Warteschlange abbrechen

| Feld | Inhalt |
|---|---|
| Was wird getestet | Abbrechen eines QUEUED-Jobs (sofortiger Abbruch) |
| Voraussetzungen | Eigener Job im Status QUEUED |
| Vorgehen | Auf der Job-Seite "Cancel" klicken |
| Erwartetes Ergebnis | HTTP 200; Status wechselt direkt auf CANCELLED |
| Testergebnis | ok |

#### TF-09 (Positiv) – Laufenden Job abbrechen

| Feld | Inhalt |
|---|---|
| Was wird getestet | Abbrechen eines STARTING/RUNNING-Jobs (zweistufig) |
| Voraussetzungen | Eigener Job im Status RUNNING |
| Vorgehen | "Cancel" klicken; Orchestrator beendet den Worker |
| Erwartetes Ergebnis | Status wechselt zunächst auf CANCELLING; nach Bestätigung durch den Orchestrator auf CANCELLED mit gesetztem finished_at |
| Testergebnis | ok |

#### TF-10 (Fehlerfall) – Abbruch eines abgeschlossenen Jobs

| Feld | Inhalt |
|---|---|
| Was wird getestet | Abbrechen eines bereits terminalen Jobs (SUCCEEDED/FAILED/CANCELLED) |
| Voraussetzungen | Eigener Job in einem terminalen Status |
| Vorgehen | "Cancel" erneut auslösen |
| Erwartetes Ergebnis | HTTP 409 (Conflict), keine Statusänderung, kein 500er |
| Testergebnis | ok |

---

### 4.5  Job aus History löschen

#### TF-11 (Positiv) – Eigenen Job aus History löschen

| Feld | Inhalt |
|---|---|
| Was wird getestet | Entfernen eines Jobs aus der eigenen History |
| Voraussetzungen | Angemeldet; mind. ein eigener Job in /me/history |
| Vorgehen | In der History "Löschen" beim Job klicken |
| Erwartetes Ergebnis | HTTP 204; Job und zugehörige Artefakt-Zeilen verschwinden aus der History |
| Testergebnis | ok |

#### TF-12 (Fehlerfall) – Fremden Job löschen

| Feld | Inhalt |
|---|---|
| Was wird getestet | Löschversuch für einen Job, der einem anderen Nutzer gehört |
| Voraussetzungen | Zwei Nutzer A und B; Job gehört A; angemeldet als B |
| Vorgehen | DELETE auf /me/history/{public_id} des fremden Jobs (z. B. via API) |
| Erwartetes Ergebnis | HTTP 403 (Forbidden); Job bleibt erhalten. Nicht existierende ID → HTTP 404 |
| Testergebnis | ok |

---

### 4.6  Rollen / Zugriffsschutz

#### TF-13 (Positiv) – Creator/Admin sehen ihre Bereiche

| Feld | Inhalt |
|---|---|
| Was wird getestet | Sichtbarkeit der Creator-/Admin-Bereiche für berechtigte Rollen |
| Voraussetzungen | auth_provider=oidc; Keycloak mit Accounts space_creator und admin |
| Vorgehen | Als space_creator /creator öffnen; als admin /admin öffnen |
| Erwartetes Ergebnis | Berechtigte sehen ihre Bereiche und können die jeweiligen Endpunkte nutzen |
| Testergebnis | ok |

#### TF-14 (Fehlerfall) – end_user hat keinen Zugriff

| Feld | Inhalt |
|---|---|
| Was wird getestet | end_user sieht keine Creator-/Admin-Seiten und wird serverseitig abgewiesen |
| Voraussetzungen | auth_provider=oidc; Account mit Rolle end_user |
| Vorgehen | Als end_user einloggen; Navigation prüfen; direkt /creator/spaces bzw. /admin/spaces per API aufrufen |
| Erwartetes Ergebnis | Creator-/Admin-Navigation ist ausgeblendet; direkte API-Aufrufe liefern HTTP 403 |
| Testergebnis | ok |

---

### 4.7  Layout / Robustheit

#### TF-15 – Kurze und lange Eingaben

| Feld | Inhalt |
|---|---|
| Was wird getestet | Layout-Verhalten bei sehr kurzen und sehr langen Eingaben |
| Voraussetzungen | Edit-Seite eines Space; Space-Hub |
| Vorgehen | Name/Beschreibung einmal sehr kurz (1 Zeichen) und einmal sehr lang (mehrere hundert Zeichen) eingeben; Darstellung in Karten, Editor und Job-Seite prüfen |
| Erwartetes Ergebnis | Kein Überlaufen/Abschneiden, das die Bedienung blockiert; Texte werden umgebrochen oder sinnvoll gekürzt |
| Testergebnis | ok |

---

## 5  Integrationstest: SAM 3D Objects

### IT-01 – End-to-End Image-to-3D Pipeline (Dev-Mode)

| Feld | Inhalt |
|---|---|
| Was wird getestet | Gesamte Pipeline: Bild hochladen → Runner erzeugt GLB-Datei → Artefakt im System abrufbar |
| Voraussetzungen | Space "3D Generator – SAM 3D Objects" veröffentlicht; DEV_MODE=1 (kein GPU nötig); Backend + Frontend lokal gestartet |
| Vorgehen | Space im Hub öffnen; JPEG/PNG hochladen; Job absenden; Status bis SUCCEEDED verfolgen; GLB-Download testen |
| Erwartetes Ergebnis | Job erreicht SUCCEEDED; .glb-Datei (blauer Demo-Würfel) wird als Download angeboten; Datei öffnet sich in einem 3D-Viewer |
| Testergebnis | ok |

---

## Anhang: Coverage-Report

```
Backend Branch-Coverage: 80 %
  Statements  : 1193 total, 204 not covered
  Branches    : 182 total,   20 partially covered

Testlauf:
  228 passed, 7 skipped
  Laufzeit: 4,02 s
```

```
Frontend Tests: 24 passed (5 Test-Dateien)
  Laufzeit: 6,36 s
```

```
Load-Test (2026-07-05, 2.000 req, concurrency 50):
  GET /health  → 1.894 req/s, 0 Fehler, p99 = 0,7 ms
  GET /spaces  →   517 req/s, 0 Fehler, p99 = 125,9 ms
```
