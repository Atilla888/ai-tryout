# Project Contributions

This document summarizes the main responsibilities and contributions of each team member during the AI-Spaces project.

## Team Members and Responsibilities

### Sarah da Anunciacao Santos — AI Spaces, Testing, Documentation

- Integrated the ACE-Step 1.5 runner (text-to-music) as a working Space with mock mode (sine-wave WAV output, no GPU required)
- Integrated the SAM 3D Objects runner (image-to-3D) as a working Space with mock mode (blue cube GLB, no GPU required)
- Built the interactive 3D viewer in the frontend using model-viewer (WebGL, supports rotate/zoom)
- Wrote the complete backend test suite (228 unit tests, 80% branch coverage) using pytest, pytest-asyncio, and SQLite in-memory
- Added frontend UI tests with Vitest and @testing-library/react (24 tests across 5 test files)
- Ran load tests (2,000 requests, 50 concurrent) for the /health and /spaces endpoints
- Wrote the project documentation: README, QUICKSTART, test results report, implementation guide
- Performed code refactoring and quality improvements across the backend

### Atilla Kenebay — Kubernetes, Infrastructure, DevOps

- Designed and set up Kubernetes manifests for all services (Postgres, Keycloak, backend, orchestrator, frontend)
- Created automated kind cluster setup scripts for Mac/Linux and Windows (up, seed, down)
- Configured Docker Compose with auto-run migrations, health checks, and frontend service on port 5173
- Set up NFS-based artifact storage for the Kubernetes deployment
- Added Keycloak realm with pre-seeded user accounts (admin, creator, end user)
- Worked on backend and orchestrator integration (runner job pods, image pull policy)
- Added module and function docstrings across backend and orchestrator

### Jann Hopster — Backend, Frontend, Testing

- Implemented the Admin dashboard (spaces and user management, endpoints GET/PATCH/DELETE)
- Implemented the Creator dashboard and space editor with validation logic
- Modularized the frontend API layer (split api.ts into domain modules with shared fetch wrapper)
- Decomposed Spaces.tsx into reusable sub-components
- Implemented the full job execution pipeline (catalog, job correctness, real execution)
- Added CORS middleware and OpenAPI endpoint descriptions
- Added unit tests for validation, maintenance, and auth modules
- Added backend test coverage tooling and a load test script
- Integrated the ACE-Step 1.5 Space on the frontend side
- Fixed several bugs: admin page crash on integer owner_id, blank select options, nav header class mismatch
- Implemented artifact file cleanup on history delete

## Shared Contributions

All team members contributed to:

- Project planning and architecture discussions
- Debugging and testing the application end to end
- Reviewing code and resolving integration issues
- Preparing the final presentation and documentation

## Notes

The project was developed as part of the interdisciplinary software engineering course at Hof University of Applied Sciences (SS 2026). All AI Spaces run in mock mode and do not require a GPU.
