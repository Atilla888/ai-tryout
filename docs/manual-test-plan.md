# Manuelles Testprotokoll – AI-Spaces

**Projekt:** AI-Spaces · Interdisziplinäres SW-Entwicklungsprojekt · Hochschule Hof · SS 2026
**Stand:** 2026-06-23
**Schema:** Foliensatz 08 (Was wird getestet / Voraussetzungen / Vorgehen / Erwartetes Ergebnis / Testergebnis)

Dieses Protokoll ergänzt die automatisierten Tests (Backend `pytest`, Frontend `vitest`)
um systematische manuelle Tests der wichtigsten End-to-End-Flüsse aus dem Pflichtenheft.
Jeder Fluss hat einen **Positiv-** und einen **Fehlerfall**.

**Hinweise zur Durchführung (Foliensatz 08):**
- Am besten testet jeweils jemand, der den betreffenden Teil **nicht selbst gebaut** hat.
- Felder mit **kurzen UND langen** Eingaben prüfen (Layout/Umbruch) – siehe TF-13.
- Die Spalte **Testergebnis** ist mit „ok" vorbelegt und muss vor der Abgabe von einer
  unabhängigen Testperson real bestätigt (oder korrigiert) werden.

## Allgemeine Voraussetzungen (Testumgebung)

- Backend läuft (`cd apps/backend && uvicorn app.main:app`), Frontend läuft (`cd apps/frontend && npm run dev`).
- Datenbank erreichbar, Migrationen eingespielt.
- Für **Rollen-Tests (TF-11/TF-12)**: `auth_provider=oidc` (Keycloak), da der `DevAuthProvider`
  in der lokalen Entwicklung jeden Nutzer als Admin behandelt. Benötigt werden Test-Accounts
  mit den Rollen `end_user`, `space_creator` und `admin`.
- Für alle übrigen Tests genügt die lokale Dev-Anmeldung.

---

## 1. Space anlegen und als Draft speichern

### TF-01 (Positiv) – Space als Entwurf speichern
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | Anlegen eines neuen Space und Speichern als Draft (Creator) |
| **Voraussetzungen** | Angemeldet als `space_creator` oder `admin`; auf `/creator` → „New Space" |
| **Vorgehen** | Name „Image Magic" eingeben (Slug wird automatisch zu `image-magic`), Container-Image `ghcr.io/org/model:latest` eingeben, mindestens ein Input-Feld definieren, „Save as Draft" klicken |
| **Erwartetes Ergebnis** | HTTP 201; Weiterleitung auf die Edit-Seite; Status-Badge zeigt `DRAFT`; Space taucht in „My Spaces" auf |
| **Testergebnis** | ok |

### TF-02 (Fehlerfall) – Pflichtfeld leer
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | Speichern mit leerem Pflichtfeld (z. B. Container-Image bzw. Name) |
| **Voraussetzungen** | Wie TF-01, „New Space" geöffnet |
| **Vorgehen** | Name leer lassen (bzw. Container-Image leer), „Save as Draft" klicken |
| **Erwartetes Ergebnis** | Es wird kein gültiger Space angelegt; die fehlenden Pflichtangaben fallen spätestens beim Publish-Validate auf (siehe TF-04). Die Anwendung zeigt einen Fehler bzw. verhindert das Veröffentlichen; kein 500er |
| **Testergebnis** | ok |

---

## 2. Space mit ungültiger Config publizieren

### TF-03 (Positiv) – Gültige Config publizieren
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | Veröffentlichen eines Space mit gültiger `ui_config`/`runner_config` |
| **Voraussetzungen** | Draft-Space mit gültigem Input-Feld (Name passt zu `^[A-Za-z_][A-Za-z0-9_]*$`, Typ, Label), gültigem Container-Image und `runner_config` `{}` |
| **Vorgehen** | Auf der Edit-Seite „Publish" klicken |
| **Erwartetes Ergebnis** | Validierung meldet „Configuration is valid"; Status wechselt auf `PUBLISHED`; Space erscheint im öffentlichen Space-Hub |
| **Testergebnis** | ok |

### TF-04 (Fehlerfall) – Ungültige Config publizieren
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | Publish mit ungültiger Konfiguration (z. B. kein Input-Feld, ungültiger Feldname `1abc`, `select` ohne Options, oder leeres Container-Image) |
| **Voraussetzungen** | Draft-Space mit absichtlich fehlerhafter Config |
| **Vorgehen** | „Publish" klicken |
| **Erwartetes Ergebnis** | Validierungsfehler wird angezeigt (Liste der `field`/`message`-Einträge); Space bleibt im Status `DRAFT`; pro betroffenem Feld erscheint eine Fehlermarkierung |
| **Testergebnis** | ok |

### TF-05 (Fehlerfall) – Ungültiges runner_config-JSON
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | `runner_config`-Textfeld mit ungültigem JSON |
| **Voraussetzungen** | Edit-Seite eines Space geöffnet |
| **Vorgehen** | In `runner_config` ungültigen Text (z. B. `not json`) eingeben, „Save as Draft"/„Publish" klicken |
| **Erwartetes Ergebnis** | Meldung „runner_config must be a valid JSON object"; es wird **keine** API-Anfrage gesendet |
| **Testergebnis** | ok |

---

## 3. Job absenden und Ergebnis abrufen

### TF-06 (Positiv) – Job absenden und Ergebnis sehen
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | Absenden eines Jobs für einen veröffentlichten Space und Abruf des Ergebnisses |
| **Voraussetzungen** | Veröffentlichter, öffentlicher Space mit mind. einem Input; angemeldeter Nutzer |
| **Vorgehen** | Space im Hub öffnen, Eingabefelder ausfüllen, „Submit" klicken; auf der Job-Seite den Status verfolgen, bis `SUCCEEDED`; Artefakt(e) ansehen/herunterladen |
| **Erwartetes Ergebnis** | HTTP 201 mit `status=QUEUED` und Queue-Position; Job durchläuft `STARTING`→`RUNNING`→`SUCCEEDED`; Ausgabe-Artefakte werden gelistet und sind als Preview/Download abrufbar |
| **Testergebnis** | ok |

### TF-07 (Fehlerfall) – Leere/ungültige Eingabe
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | Absenden ohne Pflichteingabe bzw. mit ungültiger Eingabe |
| **Voraussetzungen** | Space mit einem als `required` markierten Input |
| **Vorgehen** | Pflichtfeld leer lassen, „Submit" klicken |
| **Erwartetes Ergebnis** | Validierungshinweis (z. B. „… is required"); es wird **kein** Job angelegt (`submitJob` wird nicht aufgerufen) |
| **Testergebnis** | ok |

---

## 4. Job abbrechen

### TF-08 (Positiv) – Job in der Warteschlange abbrechen
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | Abbrechen eines `QUEUED`-Jobs (sofortiger Abbruch) |
| **Voraussetzungen** | Eigener Job im Status `QUEUED` |
| **Vorgehen** | Auf der Job-Seite „Cancel" klicken |
| **Erwartetes Ergebnis** | HTTP 200; Status wechselt direkt auf `CANCELLED`; Job verschwindet aus der QUEUED-Liste |
| **Testergebnis** | ok |

### TF-09 (Positiv) – Laufenden Job abbrechen
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | Abbrechen eines `STARTING`/`RUNNING`-Jobs (zweistufig, D2) |
| **Voraussetzungen** | Eigener Job im Status `RUNNING` |
| **Vorgehen** | „Cancel" klicken; Orchestrator beendet den Worker |
| **Erwartetes Ergebnis** | Status wechselt zunächst auf `CANCELLING`; nach Bestätigung durch den Orchestrator auf `CANCELLED` mit gesetztem `finished_at` |
| **Testergebnis** | ok |

### TF-10 (Fehlerfall) – Abbruch eines abgeschlossenen Jobs
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | Abbrechen eines bereits terminalen Jobs (`SUCCEEDED`/`FAILED`/`CANCELLED`) |
| **Voraussetzungen** | Eigener Job in einem terminalen Status |
| **Vorgehen** | „Cancel" erneut auslösen |
| **Erwartetes Ergebnis** | HTTP 409 (Conflict), keine Statusänderung, kein 500er (idempotentes Verhalten) |
| **Testergebnis** | ok |

---

## 5. Job aus History löschen

### TF-11 (Positiv) – Eigenen Job aus History löschen
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | Entfernen eines Jobs aus der eigenen History |
| **Voraussetzungen** | Angemeldet; mind. ein eigener Job in `/me/history` |
| **Vorgehen** | In der History „Löschen" beim Job klicken |
| **Erwartetes Ergebnis** | HTTP 204; Job (und zugehörige Artefakt-Zeilen) verschwinden aus der History; die Dateien werden spätestens vom Ablauf-Cleanup entfernt |
| **Testergebnis** | ok |

### TF-12 (Fehlerfall) – Fremden Job löschen
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | Löschversuch für einen Job, der einem anderen Nutzer gehört |
| **Voraussetzungen** | Zwei Nutzer A und B; Job gehört A; angemeldet als B |
| **Vorgehen** | DELETE auf `/me/history/{public_id}` des fremden Jobs (z. B. via API) |
| **Erwartetes Ergebnis** | HTTP 403 (Forbidden); Job bleibt erhalten. Nicht existierende ID → HTTP 404 |
| **Testergebnis** | ok |

---

## 6. Rollen / Zugriffsschutz

### TF-13 (Positiv) – Creator/Admin sehen ihre Bereiche
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | Sichtbarkeit der Creator-/Admin-Bereiche für berechtigte Rollen |
| **Voraussetzungen** | `auth_provider=oidc`; Accounts mit Rolle `space_creator` bzw. `admin` |
| **Vorgehen** | Als `space_creator` `/creator` öffnen; als `admin` `/admin` öffnen |
| **Erwartetes Ergebnis** | Berechtigte sehen ihre Bereiche (Creator-Dashboard bzw. Admin-Dashboard) und können die jeweiligen Endpunkte nutzen |
| **Testergebnis** | ok |

### TF-14 (Fehlerfall) – end_user hat keinen Zugriff
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | `end_user` sieht keine Creator-/Admin-Seiten und wird serverseitig abgewiesen |
| **Voraussetzungen** | `auth_provider=oidc`; Account mit Rolle `end_user` |
| **Vorgehen** | Als `end_user` einloggen; Navigation prüfen; direkt `/creator/spaces` bzw. `/admin/spaces` per API aufrufen |
| **Erwartetes Ergebnis** | Creator-/Admin-Navigation ist ausgeblendet; direkte API-Aufrufe liefern HTTP 403 (Forbidden) |
| **Testergebnis** | ok |

---

## 7. Layout / Robustheit (Kür, Foliensatz-Tipp)

### TF-15 – Kurze und lange Eingaben
| Feld | Inhalt |
|---|---|
| **Was wird getestet** | Layout-Verhalten bei sehr kurzen und sehr langen Eingaben |
| **Voraussetzungen** | Edit-Seite eines Space; Space-Hub |
| **Vorgehen** | Name/Beschreibung einmal sehr kurz (1 Zeichen) und einmal sehr lang (mehrere hundert Zeichen) eingeben; Darstellung in Karten, Editor und Job-Seite prüfen |
| **Erwartetes Ergebnis** | Kein Überlaufen/Abschneiden, das die Bedienung blockiert; Texte werden umgebrochen oder sinnvoll gekürzt; keine Layout-Brüche |
| **Testergebnis** | ok |
