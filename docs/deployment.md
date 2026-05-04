# Deployment & Local Development

## Quick Start (Local)

### Prerequisites
- Podman 3.4+ with podman-compose
- Git

### Steps
1. Clone the repo: `git clone <repo-url>`
2. Copy env file: `cp .env.example .env`
3. Start the stack: `podman-compose up --build`
4. Backend API: http://localhost:8000
5. API docs (Swagger): http://localhost:8000/docs

## Services
| Service  | Port | Description                  |
|----------|------|------------------------------|
| backend  | 8000 | FastAPI REST API             |
| frontend | 5173 | React SPA (not yet in stack) |
| postgres | 5432 | PostgreSQL database          |

## Notes
- Frontend requires Node.js — pending teammate setup
- Database tables are created in S1-03 (Alembic migration)
- Use podman-compose instead of docker compose on university laptops

## Useful Commands
```bash
podman-compose up --build    # start everything
podman-compose down          # stop everything
podman-compose logs backend  # view backend logs
podman-compose ps            # check service status

