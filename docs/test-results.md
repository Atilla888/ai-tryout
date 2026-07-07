# Test Results – AI-Spaces

Project: AI-Spaces · Interdisciplinary Software Engineering Project · Hof University of Applied Sciences · SS 2026
Date: 2026-07-05
Schema: Slide set 08 (What is tested / Prerequisites / Steps / Expected result / Test result)

---

## Overview

| Test category | Tool | Number of tests | Result |
|---|---|---|---|
| Backend unit tests | pytest 8.x | 237 passed, 7 skipped | 80% branch coverage |
| Frontend unit/UI tests | Vitest + @testing-library/react | 24 passed | all green |
| Load test | scripts/loadtest.py (httpx ASGI) | 2 x 2,000 requests | 0 errors |
| Manual tests | Manual walkthrough | 15 test cases (TF-01 to TF-15) | all ok |

---

## 1  Backend Unit Tests (pytest)

Tool: pytest 8.x + pytest-asyncio + pytest-cov
Database: SQLite in-memory (JSONB -> JSON shim), no running server required
Auth: DevAuthProvider (no Keycloak required), roles are overridden via app.dependency_overrides

Run:
```
cd apps/backend
python -m pytest tests/ --cov=app --cov-branch -q
```

Result:
```
237 passed, 7 skipped  (4.42 s)
Branch coverage total: 80%  (statements missed 204/1193, branches missed 20/182)
```

### Test modules and test cases

#### 1.1  tests/test_validation.py – 30 tests

| # | What is tested | Prerequisites | Steps | Expected result | Test result |
|---|---|---|---|---|---|
| 1 | Valid minimal config | Space object with one text input and container image | Call validate_space_config() | valid=True, errors=[] | ok |
| 2 | Missing inputs key | ui_config without inputs | Validation | Error: 'inputs' key is required | ok |
| 3 | inputs not a list | inputs: "string" | Validation | Error: 'inputs' must be a list | ok |
| 4 | Empty inputs array | inputs: [] | Validation | Error: At least one input is required | ok |
| 5 | Invalid field name (1abc) | Input with name 1abc | Validation | Error: name must start with a letter or underscore | ok |
| 6 | Duplicate field name | Two inputs with the same name | Validation | Error: Duplicate input name | ok |
| 7 | Unknown type | type: "unknown" | Validation | Error: type must be one of … | ok |
| 8 | select without options | type: "select" without options | Validation | Error: options is required | ok |
| 9 | select with empty options array | options: [] | Validation | Error: options must be non-empty | ok |
| 10 | select with invalid entry | options: [""] | Validation | Error: entries must be non-empty strings | ok |
| 11 | Missing label | Input without label | Validation | Error: label is required | ok |
| 12 | required not a boolean | required: "yes" | Validation | Error: required must be a boolean | ok |
| 13 | Missing container image | container_image: "" | Validation | Error: container_image must not be empty | ok |
| 14 | timeout_seconds not an integer | timeout_seconds: "300" | Validation | Error: must be an integer | ok |
| 15 | timeout_seconds out of range | timeout_seconds: 0 | Validation | Error: must be between 1 and 86400 | ok |
| 16 | memory_mb not an integer | memory_mb: "512" | Validation | Error: must be an integer | ok |
| 17 | memory_mb out of range | memory_mb: 63 | Validation | Error: must be between 64 and 65536 | ok |
| 18–30 | Further edge cases | Valid types text, image_upload, audio_upload, number, select | Validation | valid=True or targeted error message | ok |

---

#### 1.2  tests/test_spaces_api.py – 8 tests

| # | What is tested | Prerequisites | Steps | Expected result | Test result |
|---|---|---|---|---|---|
| 1 | GET /spaces – empty | No spaces in DB | GET /spaces | [] | ok |
| 2 | GET /spaces – only published public | Mix of draft/published and public/private | GET /spaces | Only PUBLISHED + PUBLIC appear | ok |
| 3 | GET /spaces – multiple spaces | 3 published spaces | GET /spaces | All 3 in response | ok |
| 4 | GET /spaces/{id} – 200 | Space exists | GET /spaces/{id} | HTTP 200, correct data | ok |
| 5 | GET /spaces/{id} – 404 | Unknown ID | GET /spaces/{id} | HTTP 404 | ok |
| 6 | GET /spaces/{id} – private space accessible by ID | PRIVATE space | GET /spaces/{id} | HTTP 200 (ID lookup ignores visibility) | ok |
| 7 | POST /spaces – 201 | Valid payload | POST /spaces | HTTP 201, space in DB | ok |
| 8 | POST /spaces – 409 duplicate | Space with same slug | POST /spaces | HTTP 409 Conflict | ok |

---

#### 1.3  tests/test_creator_api.py – 13 tests

| # | What is tested | Prerequisites | Steps | Expected result | Test result |
|---|---|---|---|---|---|
| 1 | POST /creator/spaces – create | Logged in as creator | POST /creator/spaces | HTTP 201 | ok |
| 2 | POST /creator/spaces – duplicate | Space with same slug exists | POST /creator/spaces | HTTP 409 | ok |
| 3 | GET /creator/spaces – empty | No own spaces | GET /creator/spaces | [] | ok |
| 4 | GET /creator/spaces – own spaces | 2 own spaces | GET /creator/spaces | Both in response | ok |
| 5 | PATCH /creator/spaces/{id} – 200 | Own space | PATCH with new name | HTTP 200, name updated | ok |
| 6 | PATCH /creator/spaces/{id} – 404 | Unknown ID | PATCH | HTTP 404 | ok |
| 7 | PATCH /creator/spaces/{id} – 403 | Foreign space | PATCH as different user | HTTP 403 | ok |
| 8 | POST /creator/spaces/{id}/validate – valid | Valid config | Validate | HTTP 200, valid: true | ok |
| 9 | POST /creator/spaces/{id}/validate – invalid | Faulty config | Validate | HTTP 200, error list | ok |
| 10 | POST /creator/spaces/{id}/validate – 404 | Unknown ID | Validate | HTTP 404 | ok |
| 11 | POST /creator/spaces/{id}/validate – 403 | Foreign space | Validate as different user | HTTP 403 | ok |
| 12 | POST /creator/spaces – end_user blocked | User has role end_user | POST /creator/spaces | HTTP 403 | ok |
| 13 | GET /creator/spaces – end_user blocked | User has role end_user | GET /creator/spaces | HTTP 403 | ok |

---

#### 1.4  tests/test_admin_api.py – 13 tests

| # | What is tested | Prerequisites | Steps | Expected result | Test result |
|---|---|---|---|---|---|
| 1 | GET /admin/spaces – empty | No spaces | GET /admin/spaces | [] | ok |
| 2 | GET /admin/spaces – all spaces | Mix of different spaces | GET /admin/spaces | All visible (including private) | ok |
| 3 | PATCH /admin/spaces/{id} – change status | Space exists | PATCH with new status | HTTP 200 | ok |
| 4 | PATCH /admin/spaces/{id} – change visibility | Space exists | PATCH with new visibility | HTTP 200 | ok |
| 5 | PATCH /admin/spaces/{id} – 404 | Unknown ID | PATCH | HTTP 404 | ok |
| 6 | PATCH /admin/spaces/{id} – 403 non-admin | User is not admin | PATCH | HTTP 403 | ok |
| 7 | DELETE /admin/spaces/{id} – 204 | Space exists | DELETE | HTTP 204 | ok |
| 8 | DELETE /admin/spaces/{id} – 404 | Unknown ID | DELETE | HTTP 404 | ok |
| 9 | DELETE /admin/spaces/{id} – 403 non-admin | User is not admin | DELETE | HTTP 403 | ok |
| 10 | GET /admin/users – empty | No users in DB | GET /admin/users | [] | ok |
| 11 | GET /admin/users – contains seeded user | User in DB | GET /admin/users | User in response | ok |
| 12 | GET /admin/users – 403 non-admin | User is not admin | GET /admin/users | HTTP 403 | ok |
| 13 | Admin sees all spaces including foreign ones | Spaces from different owners | GET /admin/spaces | All listed | ok |

---

#### 1.5  tests/test_users_service.py – 8 tests

| # | What is tested | Prerequisites | Steps | Expected result | Test result |
|---|---|---|---|---|---|
| 1 | list_users() – empty | No users | list_users() | [] | ok |
| 2 | list_users() – all | 2 users in DB | list_users() | Both returned | ok |
| 3 | get_by_subject() – found | User in DB | get_by_subject(subject, idp) | User object | ok |
| 4 | get_by_subject() – not found | No matching user | get_by_subject() | None | ok |
| 5 | get_by_subject() – wrong IDP | User with different IDP | get_by_subject() | None | ok |
| 6 | get_or_create() – new user | User does not exist | get_or_create() | New user object | ok |
| 7 | get_or_create() – existing user | User already in DB | get_or_create() | Existing user returned | ok |
| 8 | get_or_create() – race condition | IntegrityError on insert (mock) | get_or_create() | Fallback to SELECT, no error | ok |

---

#### 1.6  Further test modules

| Module | Tests | Content |
|---|---|---|
| tests/test_jobs_api.py | 13 | Job CRUD: create, status transitions, cancel, internal endpoints |
| tests/test_job_state_transitions.py | 36 | State machine: all allowed and forbidden status transitions |
| tests/test_job_transitions.py | 13 | Orchestrator transitions (STARTING -> RUNNING -> SUCCEEDED/FAILED) |
| tests/test_history.py | 9 | /me/history – list, delete 204, 403 for foreign jobs, 404 |
| tests/test_artifacts.py | 5 | Artifact upload, download, content-type handling |
| tests/test_auth.py | 12 | DevAuthProvider, OIDC token parsing, role extraction |
| tests/test_fake_runner.py | 2 | Fake runner SDK roundtrip (DEV_MODE) |
| tests/test_maintenance.py | 4 | Cleanup job: closing stale jobs |
| tests/test_user_identity.py | 9 | Per-user running number, creator ID on spaces, public_id assignment |
| tests/integration/test_job_flow.py | 16 | End-to-end: create job -> runner -> artifact -> succeed |

---

## 2  Frontend Unit/UI Tests (Vitest)

Tool: Vitest + @testing-library/react + jsdom
Mocks: API modules mocked via vi.mock('../api/api'), OIDC via vi.mock('react-oidc-context')

Run:
```
cd apps/frontend
npm run test
```

Result:
```
Test Files  5 passed (5)
Tests       24 passed (24)
Duration    6.36 s
```

### Test suites and test cases

#### 2.1  History.test.tsx – 9 tests (page: /history)

| # | What is tested | Prerequisites | Steps | Expected result | Test result |
|---|---|---|---|---|---|
| 1 | Loading state -> jobs rendered | fetchMyHistory returns jobs | Mount page | Spinner first, then job list | ok |
| 2 | Plural label for multiple jobs | 2 jobs in mock | Mount page | "2 jobs in your history" | ok |
| 3 | Error message on API error | fetchMyHistory throws error | Mount page | Error message visible | ok |
| 4 | Empty state | fetchMyHistory returns [] | Mount page | "No jobs in your history yet" | ok |
| 5 | Status pill for failed job | Job with status: FAILED | Mount page | Red status pill | ok |
| 6 | Sort order: newest first | 2 jobs with different timestamps | Mount page | Newer job on top | ok |
| 7 | Delete confirmed -> job disappears | Confirm dialog accepted | Click delete button | Job no longer visible | ok |
| 8 | Delete cancelled -> job stays | Confirm dialog rejected | Click delete button, cancel | Job still visible | ok |
| 9 | Delete failed -> alert | deleteMyHistory throws error | Click delete button | Error message appears | ok |

---

#### 2.2  Spaces.test.tsx – 5 tests (page: /spaces, submit flow)

| # | What is tested | Prerequisites | Steps | Expected result | Test result |
|---|---|---|---|---|---|
| 1 | Loading state -> space list | fetchSpaces returns 2 spaces | Mount page | Spinner then cards | ok |
| 2 | Search by space name | 2 spaces, enter search term | Fill search field | Only matching spaces shown | ok |
| 3 | Filter by task type | Spaces with different task types | Click task type chip | Only spaces with that type | ok |
| 4 | Error state | fetchSpaces throws error | Mount page | Error message visible | ok |
| 5 | Submit form -> JobDetail | Input filled, submit | Click submit button | Navigation to /jobs/{id} | ok |

---

#### 2.3  SpaceEditor.test.tsx – 4 tests (page: /creator/spaces)

| # | What is tested | Prerequisites | Steps | Expected result | Test result |
|---|---|---|---|---|---|
| 1 | Slug auto-generated from name | New space form | Enter name | Slug is filled automatically | ok |
| 2 | "Save as Draft" sends correct payload | Form filled | Click save button | createSpace() called with expected data | ok |
| 3 | Invalid runner_config JSON | runner_config field with "not json" | Click save | Error message, no API call | ok |
| 4 | Publish validation error -> stays DRAFT | Validate returns errors | Click publish | Status stays DRAFT, errors shown | ok |

---

#### 2.4  JobDetail.test.tsx – 4 tests (page: /jobs/{id})

| # | What is tested | Prerequisites | Steps | Expected result | Test result |
|---|---|---|---|---|---|
| 1 | Queue position shown | Job with status: QUEUED, position 3 | Mount page | "Queue position: 3" visible | ok |
| 2 | Polling while RUNNING | Job transitions QUEUED->RUNNING->SUCCEEDED | Mount page, advance timers | Progress bar -> result | ok |
| 3 | Result after SUCCEEDED | Job with artifacts | Mount page after success | Artifacts listed and downloadable | ok |
| 4 | Cancel job | Running job | Click cancel button | cancelJob() called, confirmation | ok |

---

#### 2.5  Home.test.tsx – 2 tests (page: /)

| # | What is tested | Prerequisites | Steps | Expected result | Test result |
|---|---|---|---|---|---|
| 1 | Validation: required field empty | Space with a required input | Submit without input | Error message, no job created | ok |
| 2 | Successful input -> navigation | Fields filled | Submit | submitJob() called, redirect | ok |

---

## 3  Load Test

Tool: scripts/loadtest.py – httpx ASGI transport against in-memory SQLite (no real network hop)
Configuration: 2,000 requests, 50 concurrent connections
Seeded data: 5 published public spaces

Run:
```
cd apps/backend
python -m scripts.loadtest
```

### LT-01 – GET /health (health check endpoint)

| What is tested | Prerequisites | Steps | Expected result | Test result |
|---|---|---|---|---|
| Throughput of the health endpoint with 50 concurrent clients | Backend ASGI in-process, SQLite in-memory | 2,000 GET /health requests with concurrency 50 | Throughput > 500 req/s, 0 errors, p99 < 10 ms | ok |

Results (2026-07-05):

| Metric | Value |
|---|---|
| Total requests | 2,000 |
| Throughput | 1,894 req/s |
| Errors | 0 |
| Latency p50 | 0.5 ms |
| Latency p95 | 0.6 ms |
| Latency p99 | 0.7 ms |
| Latency min / mean / max | 0.5 / 0.5 / 26.9 ms |

---

### LT-02 – GET /spaces (space list with DB query)

| What is tested | Prerequisites | Steps | Expected result | Test result |
|---|---|---|---|---|
| Throughput of the spaces endpoint (ORM query + JSON serialization) with 50 concurrent clients | 5 spaces in in-memory SQLite | 2,000 GET /spaces requests with concurrency 50 | Throughput > 100 req/s, 0 errors | ok |

Results (2026-07-05):

| Metric | Value |
|---|---|
| Total requests | 2,000 |
| Throughput | 517 req/s |
| Errors | 0 |
| Latency p50 | 88.6 ms |
| Latency p95 | 116.9 ms |
| Latency p99 | 125.9 ms |
| Latency min / mean / max | 38.3 / 88.6 / 130.1 ms |

The higher latency for /spaces compared to /health comes from the SQLAlchemy ORM query with visibility filter and subsequent JSON serialization. With a real PostgreSQL instance and network overhead the values would be more representative of a production environment.

---

## 4  Manual Tests

Test environment:
- Backend: uvicorn app.main:app on port 8000, AUTH_PROVIDER=dev
- Frontend: npm run dev on port 5173
- Database: PostgreSQL via Docker (docker compose up -d postgres)
- For role tests: Keycloak (docker compose up -d keycloak), test user admin/admin123
- Date of execution: 2026-06-23 / 2026-07-05

---

### 4.1  Create a Space and save as draft

#### TF-01 (positive) – Save space as draft

| Field | Content |
|---|---|
| What is tested | Creating a new space and saving it as draft (creator) |
| Prerequisites | Logged in as space_creator or admin; on /creator -> "New Space" |
| Steps | Enter name "Image Magic" (slug is auto-filled as image-magic), enter container image ghcr.io/org/model:latest, define at least one input field, click "Save as Draft" |
| Expected result | HTTP 201; redirect to edit page; status badge shows DRAFT; space appears in "My Spaces" |
| Test result | ok |

#### TF-02 (error case) – Required field empty

| Field | Content |
|---|---|
| What is tested | Saving with an empty required field (e.g. container image or name) |
| Prerequisites | Same as TF-01, "New Space" open |
| Steps | Leave name empty (or container image empty), click "Save as Draft" |
| Expected result | No valid space is created; missing required fields are caught at the latest on publish/validate (TF-04). The application shows an error; no 500 |
| Test result | ok |

---

### 4.2  Publish a space with invalid config

#### TF-03 (positive) – Publish with valid config

| Field | Content |
|---|---|
| What is tested | Publishing a space with valid ui_config/runner_config |
| Prerequisites | Draft space with a valid input field (name matches ^[A-Za-z_][A-Za-z0-9_]*$, type, label), valid container image and runner_config {} |
| Steps | Click "Publish" on the edit page |
| Expected result | Validation reports "Configuration is valid"; status changes to PUBLISHED; space appears in the public Space Hub |
| Test result | ok |

#### TF-04 (error case) – Publish with invalid config

| Field | Content |
|---|---|
| What is tested | Publish with invalid configuration (e.g. no input field, invalid field name 1abc, select without options, or empty container image) |
| Prerequisites | Draft space with intentionally faulty config |
| Steps | Click "Publish" |
| Expected result | Validation errors are shown (list of field/message entries); space stays in status DRAFT; an error marker appears for each affected field |
| Test result | ok |

#### TF-05 (error case) – Invalid runner_config JSON

| Field | Content |
|---|---|
| What is tested | runner_config text field with invalid JSON |
| Prerequisites | Space edit page open |
| Steps | Enter invalid text in runner_config (e.g. not json), click "Save as Draft"/"Publish" |
| Expected result | Message "runner_config must be a valid JSON object"; no API request is sent |
| Test result | ok |

---

### 4.3  Submit a job and retrieve the result

#### TF-06 (positive) – Submit a job and see the result

| Field | Content |
|---|---|
| What is tested | Submitting a job for a published space and retrieving the result |
| Prerequisites | Published public space with at least one input; logged-in user |
| Steps | Open space in the hub, fill in input fields, click "Submit"; follow the status on the job page until SUCCEEDED; view/download artifacts |
| Expected result | HTTP 201 with status=QUEUED and queue position; job transitions STARTING->RUNNING->SUCCEEDED; output artifacts are listed and available as preview/download |
| Test result | ok |

#### TF-07 (error case) – Empty/invalid input

| Field | Content |
|---|---|
| What is tested | Submit without required input |
| Prerequisites | Space with a required input field |
| Steps | Leave required field empty, click "Submit" |
| Expected result | Validation hint (e.g. "… is required"); no job is created |
| Test result | ok |

---

### 4.4  Cancel a job

#### TF-08 (positive) – Cancel a queued job

| Field | Content |
|---|---|
| What is tested | Cancelling a QUEUED job (immediate cancellation) |
| Prerequisites | Own job in status QUEUED |
| Steps | Click "Cancel" on the job page |
| Expected result | HTTP 200; status changes directly to CANCELLED |
| Test result | ok |

#### TF-09 (positive) – Cancel a running job

| Field | Content |
|---|---|
| What is tested | Cancelling a STARTING/RUNNING job (two-step) |
| Prerequisites | Own job in status RUNNING |
| Steps | Click "Cancel"; orchestrator stops the worker |
| Expected result | Status changes first to CANCELLING; after confirmation by the orchestrator to CANCELLED with finished_at set |
| Test result | ok |

#### TF-10 (error case) – Cancel a finished job

| Field | Content |
|---|---|
| What is tested | Cancelling an already terminal job (SUCCEEDED/FAILED/CANCELLED) |
| Prerequisites | Own job in a terminal status |
| Steps | Trigger "Cancel" again |
| Expected result | HTTP 409 (Conflict), no status change, no 500 |
| Test result | ok |

---

### 4.5  Delete a job from history

#### TF-11 (positive) – Delete own job from history

| Field | Content |
|---|---|
| What is tested | Removing a job from the own history |
| Prerequisites | Logged in; at least one own job in /me/history |
| Steps | Click "Delete" on a job in the history |
| Expected result | HTTP 204; job and associated artifact rows disappear from the history |
| Test result | ok |

#### TF-12 (error case) – Delete a foreign job

| Field | Content |
|---|---|
| What is tested | Deletion attempt for a job that belongs to another user |
| Prerequisites | Two users A and B; job belongs to A; logged in as B |
| Steps | DELETE on /me/history/{public_id} of the foreign job (e.g. via API) |
| Expected result | HTTP 403 (Forbidden); job is retained. Non-existing ID -> HTTP 404 |
| Test result | ok |

---

### 4.6  Roles / access control

#### TF-13 (positive) – Creator/Admin see their areas

| Field | Content |
|---|---|
| What is tested | Visibility of creator/admin areas for authorized roles |
| Prerequisites | auth_provider=oidc; Keycloak with accounts space_creator and admin |
| Steps | Open /creator as space_creator; open /admin as admin |
| Expected result | Authorized users see their areas and can use the respective endpoints |
| Test result | ok |

#### TF-14 (error case) – end_user has no access

| Field | Content |
|---|---|
| What is tested | end_user does not see creator/admin pages and is rejected server-side |
| Prerequisites | auth_provider=oidc; account with role end_user |
| Steps | Log in as end_user; check navigation; call /creator/spaces and /admin/spaces directly via API |
| Expected result | Creator/admin navigation is hidden; direct API calls return HTTP 403 |
| Test result | ok |

---

### 4.7  Layout / robustness

#### TF-15 – Short and long inputs

| Field | Content |
|---|---|
| What is tested | Layout behavior with very short and very long inputs |
| Prerequisites | Space edit page; Space Hub |
| Steps | Enter name/description once very short (1 character) and once very long (several hundred characters); check display in cards, editor and job page |
| Expected result | No overflow or clipping that blocks usage; texts are wrapped or truncated sensibly |
| Test result | ok |

---

## 5  Integration test: SAM 3D Objects

### IT-01 – End-to-end image-to-3D pipeline (dev mode)

| Field | Content |
|---|---|
| What is tested | Full pipeline: upload image -> runner generates GLB file -> artifact retrievable in the system |
| Prerequisites | Space "3D Generator – SAM 3D Objects" published; DEV_MODE=1 (no GPU required); backend + frontend running locally |
| Steps | Open space in the hub; upload a JPEG/PNG; submit job; follow status until SUCCEEDED; test GLB download |
| Expected result | Job reaches SUCCEEDED; .glb file (blue demo cube) is offered as download; file opens in a 3D viewer |
| Test result | ok |

---

## Appendix: Coverage report

```
Backend branch coverage: 80%
  Statements  : 1193 total, 204 not covered
  Branches    : 182 total,   20 partially covered

Test run:
  237 passed, 7 skipped
  Runtime: 4.42 s
```

```
Frontend tests: 24 passed (5 test files)
  Runtime: 6.36 s
```

```
Load test (2026-07-05, 2,000 req, concurrency 50):
  GET /health  -> 1,894 req/s, 0 errors, p99 = 0.7 ms
  GET /spaces  ->   517 req/s, 0 errors, p99 = 125.9 ms
```
