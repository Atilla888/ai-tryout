# Project Contributions

This document lists the GitLab issues and additional contributions for each team member in the AI-Spaces project (SS 2026, Hof University of Applied Sciences).

---

## Sarah da Anunciacao Santos (ssantos)

### GitLab Tickets

| # | Title |
|---|-------|
| 4 | Landing Page — Space Cards |
| 6 | Space Detail Page — Dynamic Input Form |
| 11 | Unit Tests — Backend Job State Transitions |
| 21 | Artifact Upload and Download Endpoints |
| 23 | Frontend Project Scaffold — React + TypeScript + Vite |
| 38 | E1 — History page |
| 40 | E2 — Space detail sidebar parity with wireframe |
| 42 | E3 — Frontend test suite |
| 43 | G1 — Complete docker-compose for full local stack |
| 44 | G2 — GitLab CI pipeline |

### Additional Contributions (outside ticket system)

- Integrated the ACE-Step 1.5 runner (text-to-music) as a working Space, including a mock mode that outputs a sine-wave WAV file without requiring a GPU
- Integrated the SAM 3D Objects runner (image-to-3D) as a working Space, including a mock mode that outputs a blue cube GLB without requiring a GPU
- Built the interactive 3D viewer in the frontend using @google/model-viewer (WebGL-based, supports rotate and zoom)
- Wrote and structured the complete test results documentation (docs/test-results.md), covering 228 backend tests, 24 frontend tests, 2 load tests, 15 manual tests, and 1 integration test
- Wrote the project documentation: README.md, QUICKSTART.md, docs/implementation-guide.md

---

## Atilla Kenebay (atilla888)

### GitLab Tickets

| # | Title |
|---|-------|
| 10 | Job Progress Page — Polling and Status Display |
| 17 | Orchestrator Stub — Picks Queued Jobs and Spawns Fake Runner |

### Additional Contributions (outside ticket system)

- Designed and set up Kubernetes manifests for all services (Postgres, Keycloak, backend, orchestrator, frontend)
- Created automated cluster setup scripts for Mac/Linux (scripts/mac-linux/up.sh, seed.sh, down.sh) and Windows (scripts/windows/up.ps1, seed.ps1, down.ps1)
- Configured Docker Compose with automatic migration execution, health-gated service startup, and NFS-based artifact storage
- Added Keycloak realm configuration with pre-seeded user accounts (admin, creator, end user)
- Added module and function docstrings across the backend and orchestrator codebase

---

## Jann Hopster (jhopster)

### GitLab Tickets

| # | Title |
|---|-------|
| 8 | Docker Compose for Local Development (Sprint 1) |
| 12 | Result Preview and Download |
| 13 | Database Schema — Spaces, Jobs, Artifacts, Users |
| 14 | Integration Tests — Job Submission and Progress Flow |
| 16 | Fake Model Runner — Simulates Full Job Lifecycle |
| 18 | Spaces CRUD API Endpoints |
| 20 | Private Job History Page |
| 22 | Backend — History and Retention Endpoints |
| 24 | B1 — Implement Creator space CRUD |
| 27 | A3 — Frontend authentication flow |
| 30 | B2 — Space config validation |
| 31 | B3 — Creator UI |
| 32 | D1 — Public catalog filtering |
| 33 | C1 — Implement Admin endpoints |
| 34 | D2 — Real job cancellation |
| 35 | D3 — Job and artifact expiration |
| 36 | D4 — Input artifacts consumed by the runner |
| 37 | C2 — Admin UI |
| 39 | F1 — Real runner contract and template |
| 41 | F2 — Kubernetes orchestrator backend |
| 45 | G3 — Kubernetes manifests and secrets |
| 46 | G4 — Production deployment docs and build pipeline |

### Additional Contributions (outside ticket system)

- Modularized the frontend API layer (split api.ts into domain-specific modules with a shared fetch wrapper)
- Decomposed Spaces.tsx into reusable sub-components
- Added CORS middleware and OpenAPI endpoint descriptions to the backend
- Added backend test coverage tooling and a load test script
- Integrated the ACE-Step 1.5 Space on the frontend side
- Fixed several bugs: admin page crash on integer owner_id, blank select options, navigation header class mismatch
- Implemented artifact file cleanup when a history entry is deleted

---

## Notes

The project was developed as part of the interdisciplinary software engineering course at Hof University of Applied Sciences (SS 2026). All AI Spaces run in mock mode and do not require a GPU.
