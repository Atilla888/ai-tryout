# AI-Spaces-Tryout — Project Context for Claude Code

## Project Overview
Browser-based platform for accessing and executing AI models at Hof University of Applied Sciences.
Inspired by Hugging Face Spaces. Built as part of the Interdisciplinary SW-Dev Project SS 2026.

**Team:** Sarah da Anunciacao Santos (Frontend), Jann Hopster, Atilla Kenebay  
**Sprint 1:** 27 April – 11 May 2026 | Sprint Review: 11 May 2026

---

## My Role
I am responsible for the **Frontend** of this project.

---

## Visual Design
- Style: Match the **SARA platform** (sara.ki-awz.iisys.de) visual language
- Branding: **Hochschule Hof** — logo is a 2x2 grid of colored squares: red (top-left), yellow (top-right), yellow (bottom-left), black (bottom-right)
- App name: **SARA** — "System for AI-Research & Assessment"
- Primary accent color: **#F5C030** (yellow/gold)
- Navbar: white background, yellow underline on active tab, 56px height
- Cards: white background, subtle border, hover shows yellow border
- Buttons: yellow background (#F5C030), dark text (#412402)
- All nav items: Projects, Datasets, Models, Leaderboards, Evaluations, **Spaces**, Groups, Trainings
- "Spaces" tab is the one we are building — it should be highlighted as active

---

## Tech Stack (Frontend)
- **Sprint 1:** Pure HTML / CSS / JavaScript (prototype first)
- **Later (Sprint 2):** React + TypeScript + Vite + Tailwind CSS
- Routing: React Router (Sprint 2)
- State: Zustand (Sprint 2)
- API calls: Axios with JWT interceptor
- Forms: react-jsonschema-form (@rjsf/core)
- 3D viewer: @google/model-viewer (GLB/GLTF)
- Video player: react-player
- File upload: react-dropzone
- Icons: Lucide React
- UI components: shadcn/ui + Tailwind CSS
- Testing: Vitest + React Testing Library + Playwright

---

## API Endpoints (Backend — connect via Axios)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/models | List all active AI spaces |
| GET | /api/models/{modelId} | Get one space + JSON UI config |
| POST | /api/jobs | Submit a new job |
| GET | /api/jobs/{jobId} | Get job status + queue position |
| GET | /api/jobs/{jobId}/artifacts | Get result artifacts |
| GET | /api/artifacts/{artifactId}/content | Download/preview result |
| POST | /api/uploads | Upload user input file |
| GET | /api/health | Backend health check |

---

## Pages to Build (Sprint 1)

### 1. Space Hub — Landing Page (US-01) ✅ PRIORITY
- Persistent top navbar (SARA branding)
- Responsive card grid of all AI spaces
- Each card shows: space name, task type, input type, output type, queue status
- Search bar (filter by name, description, task type)
- Category filter chips: All, Audio, Video, 3D, Image, Text
- Clicking a card navigates to Space Detail page
- Empty state if no results match

### 2. Space Detail Page (US-02)
- Page header: space name, owner, task type
- Dynamic input form rendered from JSON config (UIConfigRenderer component)
- Supported input types: text input, image upload dropzone, audio player, video player, image viewer, 3D viewer (GLB/GLTF)
- Input restrictions from config enforced (file type, max size)
- Submit and Cancel buttons
- Queue status indicator: "Position 2 of 5"
- "Last runs" sidebar (recent jobs)
- "About this space" panel

### 3. Job Submit + Queue + Result (US-03)
- Submit button → POST /api/jobs → immediate loading state
- Poll GET /api/jobs/{jobId} every 2-3 seconds
- Show real-time queue position: "Position X of Y"
- When job is DONE: show result preview + download button
- Cancel button available while job is QUEUED or RUNNING

### 4. Sign In Page (US-08)
- Email + password fields
- "Remember me" checkbox
- "Forgot password?" link
- Store JWT in localStorage
- Inject JWT via Axios interceptor on all API calls
- Show/hide creator-only UI elements based on role
- Redirect unauthenticated users with clear message

---

## AI Spaces in the Platform (seed data)
| Name | Task | Input | Output | Owner |
|------|------|-------|--------|-------|
| AceStep 1.5 – Music Generator | Audio | Text | Audio | jann.hopster |
| LTX 2.3 – Video Generator | Video | Text | Video | atilla.kenebay |
| SAM 3D – Object Generator | 3D | Image | 3D | sarah.santos |
| YOLO v11 – Object Detection | Image | Image | Image | atilla.kenebay |
| Text Summarizer | Text | Text | Text | jann.hopster |

---

## Job Lifecycle States
CREATED → QUEUED → RUNNING → DONE  
QUEUED or RUNNING → CANCELLED (user clicks cancel, or 20min timeout)  
RUNNING → FAILED (container error)

---

## Navigation Structure
| Element | Action | Visibility |
|---------|--------|------------|
| Logo / SARA | Navigate to Space Hub | All users |
| Hub | Navigate to Space Hub | All users |
| My History | Personal job history | Authenticated users only |
| Admin | Admin panel | Admin role only |
| Sign in / Avatar | Login or user menu | All users |

---

## Sprint 1 Definition of Done (Frontend)
- [ ] Space Hub page renders all spaces as cards with search + filter
- [ ] Clicking a card navigates to Space Detail page
- [ ] Space Detail page renders input form from JSON config
- [ ] All input types supported: text, image upload, audio, video, 3D viewer
- [ ] Submit button sends POST /api/jobs, UI shows loading state
- [ ] Queue position updates every 2-3 seconds via polling
- [ ] Result shown inline + download link when job is DONE
- [ ] Sign In page working with JWT stored and injected in requests
- [ ] Role-based UI: creator functions hidden from unauthenticated users

---

## Non-Functional Requirements (relevant for Frontend)
- NFR-01: At least 2 of 3 first-time users can submit a job without help
- Desktop browser support only (>= 1024px), no mobile required
- Interface language: English
- 8px base grid spacing
- Responsive card grid (auto-fill columns)

---

## File Structure (Sprint 1 HTML prototype)
```
frontend/
├── CLAUDE.md           ← this file
├── index.html          ← Space Hub (US-01)
├── space-detail.html   ← Space Detail + Dynamic UI (US-02, US-03)
├── signin.html         ← Sign In page (US-08)
├── css/
│   └── styles.css      ← shared styles
└── js/
    ├── api.js          ← Axios calls + JWT interceptor
    ├── spacehub.js     ← Space Hub logic
    ├── spacedetail.js  ← Space Detail + UIConfigRenderer
    └── auth.js         ← Auth logic
```

---

## Important Notes
- Do NOT use gradients or heavy shadows — flat design like SARA
- Always show queue position as: "Position X of Y · ~N s remaining"
- Empty states need illustration + call-to-action button back to Space Hub
- Error handling: inline validation errors under fields, toast for server errors
- File upload: drag-and-drop zone with click-to-browse fallback
- Show accepted file types and size limits inside drop zone
- Web Notifications API for job completion (ask permission on first use)
