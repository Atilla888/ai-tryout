# Project Contributions

This document lists the contributions of each team member in the AI-Spaces project (SS 2026, Hof University of Applied Sciences).

---

## Sarah da Anunciacao Santos (ssantos)

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
| — | ACE-Step 1.5 runner integration (text-to-music, mock mode: sine-wave WAV) |
| — | SAM 3D Objects runner integration (image-to-3D, mock mode: blue cube GLB) |
| — | Interactive 3D viewer in the frontend using @google/model-viewer |
| — | Test results documentation (228 backend, 24 frontend, 2 load, 15 manual, 1 integration test) |
| — | Project documentation: README.md, QUICKSTART.md, docs/implementation-guide.md |
| — | Backend refactoring and code quality improvements |

---

## Atilla Kenebay (atilla888)

| # | Title |
|---|-------|
| 10 | Job Progress Page — Polling and Status Display |
| 17 | Orchestrator Stub — Picks Queued Jobs and Spawns Fake Runner |
| — | Kubernetes manifests for all services (Postgres, Keycloak, backend, orchestrator, frontend) |
| — | Cluster setup scripts for Mac/Linux (up.sh, seed.sh, down.sh) and Windows (up.ps1, seed.ps1, down.ps1) |
| — | Docker Compose with automatic migrations, health-gated startup, and NFS-based artifact storage |
| — | Keycloak realm configuration with pre-seeded user accounts (admin, creator, end user) |
| — | Module and function docstrings across backend and orchestrator |

---

## Jann Hopster (jhopster)

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
| — | Frontend API layer modularization (split api.ts into domain-specific modules) |
| — | Spaces.tsx decomposed into reusable sub-components |
| — | CORS middleware and OpenAPI endpoint descriptions |
| — | Backend test coverage tooling and load test script |
| — | ACE-Step 1.5 Space frontend integration |
| — | Bug fixes: admin page crash on integer owner_id, blank select options, nav header class mismatch |
| — | Artifact file cleanup on history delete |

---

## Notes

The project was developed as part of the interdisciplinary software engineering course at Hof University of Applied Sciences (SS 2026). All AI Spaces run in mock mode and do not require a GPU.
