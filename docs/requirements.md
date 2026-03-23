# Requirements Specification — AI Spaces for University

## 1. Project Overview (One-Pager)

**Project**: #7 — Huggingface Spaces for University

**Problem**: University students and staff who want to experiment with AI models (image detection, video generation, 3D generation) currently face high setup barriers — installing dependencies, configuring GPU drivers, managing Python environments. There is no shared, lightweight way to try models from a browser.

**Solution**: A self-hosted platform that provides simple browser UIs for AI models, backed by on-demand container startup in Kubernetes. Users select a model, upload input, and receive results — with progress feedback, in-browser preview, and download — without any local setup.

**Target models for demonstration**:

| Model | Task | Output type |
|---|---|---|
| YOLO v11 | Object detection | Annotated image |
| LTX 2.3 | Video generation | Video file |
| SAM 3D Objects | 3D object generation | GLTF 3D file |

**Key capabilities**: on-demand container startup via Kubernetes, progress reporting, in-browser result preview, result download, optional gallery of past results, and browser notifications on completion.

**Tech direction**: React frontend, FastAPI backend, PostgreSQL for request tracking, MinIO for file storage, Kubernetes for on-demand model container orchestration.

**Team size**: 3 people, working collaboratively on all features.

**Timeline**: two sprints within one semester.

---

## 2. Stakeholders and Users

| Role | Description |
|---|---|
| **End user** | University student or staff member who wants to run an AI model from a browser without local setup. No ML expertise assumed. |
| **Platform operator** | Project team deploys and maintains the platform and its Kubernetes cluster. |
| **Lecturer / examiner** | Evaluates the project on functionality, code quality, architecture, documentation, and process adherence. |

The primary user for all user stories below is the **end user** unless stated otherwise.

---

## 3. Scope — MVP vs. Stretch

### 3.1 Infrastructure reality

The university does **not** provide GPU hardware or a Kubernetes cluster. However, cloud platforms offer on-demand GPU access that the team can use for heavy model execution:

| Platform | What it offers | Cost |
|---|---|---|
| Hugging Face Inference API | Hosted models callable via simple HTTP requests | Free tier available |
| Replicate | On-demand model execution with GPU, hosts many popular models | Pay-per-use, free starter credits |
| Modal | Serverless GPU functions the team can deploy custom code to | Free tier available |
| Google Cloud / AWS / Azure | Full cloud VMs with GPUs; student credit programs | $100–300 free via student programs |

The resulting setup:

- **Platform services** (frontend, backend, PostgreSQL, MinIO) run in Docker Compose on the team's own machines during development and can be deployed to a cloud VM or university server for the demo.
- **Lightweight models** like YOLO v11 run on CPU (no GPU needed). They still run as Kubernetes Jobs on the cluster's nodes — not on anyone's personal machine. The cluster provides the compute power and scales to handle multiple users.
- **Heavy models** like LTX 2.3 (video) and SAM 3D (3D objects) run on a cloud GPU service and are called from within the model container via API. This is how production AI platforms work — it is a realistic architecture, not a workaround.
- **On-demand containers via Kubernetes**: when a user submits a request, the backend creates a Kubernetes Job — a short-lived container that runs the model, returns the result, and shuts down. Each user gets their own container. Kubernetes orchestrates this scaling.
- **Kubernetes is used from day one**, not just in production. Docker Desktop includes a built-in single-node Kubernetes cluster (enabled in settings), giving the team a real cluster on their own machines. The same code and manifests work locally and on a multi-node production cluster.
- **File storage via MinIO**: uploaded inputs and generated results are stored in MinIO (an S3-compatible storage service running as a Docker container). Every container in the system accesses files through MinIO over the network, which is what makes the architecture work across multiple Kubernetes nodes.

### 3.2 MVP (Sprint 1 target)

The MVP demonstrates the core workflow end-to-end: a user picks a model, uploads input, waits while the model processes it, then previews and downloads the result — for **one model** (YOLO v11, chosen because it runs on a normal CPU and has simple input/output: image in, annotated image out).

| Area | What we deliver in Sprint 1 |
|---|---|
| Frontend | Landing page with model cards, and a model page per model (description, file input, generate button, progress indicator, result preview and download — all on one page) |
| Backend / API | Server endpoints for submitting a request, checking its status, and retrieving the result |
| Model execution | When a user submits a request, the backend creates a Kubernetes Job for YOLO v11. The container runs, produces the result, and shuts down. The frontend checks the backend for status updates until the result is ready. |
| Model integration | YOLO v11 running on CPU as a Kubernetes Job |
| File storage | MinIO stores uploaded inputs and generated results; all containers access files through MinIO over the network |
| Infrastructure | Docker Compose for platform services (frontend, backend, PostgreSQL, MinIO). Kubernetes (Docker Desktop or minikube) for on-demand model containers. |
| Testing | Unit tests for backend logic, one end-to-end test for the submit-to-result flow |

### 3.3 Sprint 2 enhancements

| Area | What we add in Sprint 2 |
|---|---|
| Additional models | LTX 2.3 (video generation) and/or SAM 3D Objects — accessed via external AI service APIs since they require GPU hardware the team does not own |
| 3D viewer | Built-in browser viewer for 3D model files (GLTF/GLB format) so users can rotate and inspect results |
| Live progress updates | Replace periodic status checks with a persistent connection so the browser receives updates instantly |
| Notifications | Browser notifications to alert the user when their job finishes, even if they switched tabs |
| Gallery | Optional page where users can browse results generated by others |
| Resource limits | If the platform reaches its maximum number of concurrent containers (e.g., due to cloud API limits), new requests are held and the user is shown an estimated wait time |
| Infrastructure | Full Kubernetes deployment (platform services also running in K8s, not just model containers); multi-node deployment if a cluster is available |
| Testing | More unit and integration tests, basic automated checks for the UI |

### 3.4 Out of scope

- User login or accounts (not required by the project brief; jobs are identified by temporary session IDs)
- Model training or fine-tuning
- Letting users upload their own custom AI models
- Mobile app

---

## 4. Functional Requirements — User Stories

Each story follows the format: *As a [role], I want [goal], so that [benefit].*

### 4.1 Core flow (MVP)

---

**US-01 — Browse available models**

*As an end user, I want to see a list of available AI models with a short description of each, so that I can choose which one to try.*

Acceptance criteria:

1. The landing page displays all registered models as cards or list items.
2. Each entry shows model name, task type, expected input type, and expected output type.
3. The user can click/tap a model to navigate to that model's page.

---

**US-02 — Submit a request**

*As an end user, I want to upload my input file and submit it to the selected model, so that the model processes it for me.*

Acceptance criteria:

1. The model page shows the model description and which input types are accepted (e.g., "JPEG or PNG image, max 10 MB").
2. The user can select a file from their device and click a generate button.
3. Invalid files (wrong type, too large) are rejected with a clear error message before submission.
4. On successful submission, a Kubernetes Job starts for this request and progress appears on the same page below the input area.

---

**US-03 — Track processing progress**

*As an end user, I want to see the current status and progress of my request, so that I know how long to wait.*

Acceptance criteria:

1. The model page shows the current status: starting (Kubernetes Job is being created), processing, completed, or failed.
2. While processing, a progress indicator (percentage or step description) is displayed and updated on the same page.
3. In the MVP, the browser automatically checks the backend for updates every few seconds.

---

**US-04 — Preview result in browser**

*As an end user, I want to see the result directly in the browser once processing is complete, so that I do not have to download it first.*

Acceptance criteria:

1. When processing completes, the result appears on the same model page below the progress area.
2. Images are displayed inline.
3. Videos are playable in an HTML5 video player. The model container is responsible for producing a browser-compatible format (MP4 with H.264 codec or WebM).
4. 3D GLTF/GLB files are rendered in an interactive 3D viewer (Sprint 2; MVP only requires image preview for YOLO).

---

**US-05 — Download result**

*As an end user, I want to download the generated result file to my computer, so that I can use it outside the platform.*

Acceptance criteria:

1. A download button is visible alongside the result preview on the model page.
2. Clicking it initiates a browser download of the result file with a meaningful filename.
3. The download works for all supported output types (image, video, GLTF).

---

### 4.2 Enhanced experience (Sprint 2)

---

**US-06 — Real-time progress updates**

*As an end user, I want progress updates pushed to my browser in real time, so that I see changes instantly without the page having to check repeatedly.*

Acceptance criteria:

1. After submission, a persistent connection is established between the browser and the backend.
2. Progress messages (percentage, step label) arrive without page refresh.
3. Falls back to periodic checking if the persistent connection fails.

---

**US-07 — Browser notification on completion**

*As an end user, I want to receive a browser notification when my model finishes processing, so that I can do something else while waiting.*

Acceptance criteria:

1. The application requests notification permission on first use.
2. When processing finishes (success or failure), a browser notification is shown (if permission was granted).
3. Clicking the notification brings the user to the model page with the completed result.

---

**US-08 — View 3D result in GLTF viewer**

*As an end user, I want to interact with a 3D result (rotate, zoom, pan) in the browser, so that I can inspect the generated object.*

Acceptance criteria:

1. GLTF/GLB results are rendered using an embedded 3D viewer (e.g., `<model-viewer>` or Three.js-based).
2. The viewer supports rotation, zoom, and pan.
3. A download button remains available alongside the viewer.

---

**US-09 — Browse result gallery**

*As an end user, I want to browse results generated by other users, so that I can see what the models can do before trying them myself.*

Acceptance criteria:

1. A gallery page shows recent results as thumbnails (images/videos) or 3D previews.
2. Each entry shows which model was used and when it was created.
3. Users can opt out of sharing their result to the gallery at submission time.

---

**US-10 — Handle resource limits gracefully**

*As an end user, I want to be informed if the platform cannot start my request immediately (e.g., because the maximum number of concurrent containers is reached), so that I know why I am waiting and how long it might take.*

Acceptance criteria:

1. If the platform cannot start a new container due to a resource limit, the user sees a clear message explaining the situation (e.g., "All processing slots are currently in use. Your request will start automatically — estimated wait: ~2 minutes.").
2. The request starts automatically once a slot becomes available, without the user having to resubmit.

---

### 4.3 Operator stories

---

**US-11 — Add a new model to the platform**

*As a platform operator, I want to register a new AI model by providing a container image and I/O specification, so that it becomes available to users without changing the core platform code.*

Acceptance criteria:

1. A model is defined by a configuration entry (container image, input type, output type, resource requirements).
2. Adding a new configuration entry makes the model appear on the landing page after a redeploy/restart.
3. The model container conforms to a standardized interface: it receives MinIO credentials and file locations as environment variables, downloads input from MinIO, uploads results to MinIO, and reports progress via a JSON file in MinIO. Output files must be in browser-compatible formats (JPEG/PNG for images, MP4 H.264 or WebM for video, GLTF for 3D).

---

## 5. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Usability | A first-time user must be able to submit a request and view the result without any instructions beyond the UI itself. |
| NFR-02 | Performance | When the browser checks the status of a request, the backend must respond within 500 ms. |
| NFR-03 | Scalability | The architecture must support running multiple model containers concurrently (one per user request). Kubernetes handles scaling; the MVP may limit concurrency to one container at a time. |
| NFR-04 | Reliability | A failed model container must not crash the platform; the request is marked as failed and the user is informed with a clear error message. |
| NFR-05 | Portability | The platform must run on any machine with Docker and Kubernetes (Docker Desktop with K8s enabled, or minikube). `docker compose up` starts platform services; model containers run as Kubernetes Jobs. |
| NFR-06 | Maintainability | Adding a new model type must not require changes to the frontend or backend core logic (configuration-driven). |
| NFR-07 | Security | Uploaded files must be validated (type, size) before processing. No arbitrary code execution from user input. |
| NFR-08 | Observability | Backend logs must include request ID, timestamps, and status transitions for debugging. |

---

## 6. Definition of Done (DoD)

A user story is considered **done** when all of the following are satisfied:

1. All acceptance criteria are met and demonstrable.
2. Code is reviewed by at least one other team member.
3. Unit tests cover the new backend logic; UI changes are manually verified against criteria.
4. No regressions in existing tests.
5. Code is merged to the main branch via pull request.
6. Relevant documentation (API docs, Quick Start, inline comments) is updated if affected.

---

## 7. Risks and Mitigations

| # | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| R1 | No university-provided GPU hardware — the team relies on cloud GPU services for heavy models | If the chosen cloud service has an outage or the free tier runs out, heavy models cannot be demonstrated | Medium | Choose a cloud platform with a reliable free tier (e.g., Hugging Face Inference API). Keep YOLO v11 as a local fallback that always works on CPU. Test cloud API reliability early and have a recorded demo as backup. |
| R2 | External AI service APIs have rate limits, costs, or downtime | Demo may fail or produce slow results if the external service is unavailable | Medium | Test API reliability early. Prepare a recorded demo video as backup. Use free-tier APIs and stay within their limits during development. |
| R3 | Docker containers are large and slow to start on student laptops | Long wait times during development and during the live demo | Medium | Keep container images small. Pre-download all images before the demo. Test the full startup sequence on the demo machine in advance. |
| R4 | Integrating LTX 2.3 or SAM 3D turns out to be more complex than expected | Sprint 2 goals are not fully completed | High | These models are Sprint 2 stretch goals, not MVP. If integration proves too difficult, the team demonstrates the platform architecture with YOLO and documents what would be needed for the other models. |
| R5 | Team members have no prior experience with Kubernetes | Kubernetes configuration takes longer than expected and blocks other work | Medium | Use Docker Desktop's built-in single-node Kubernetes cluster, which requires minimal setup (one checkbox). Start with a single Job manifest template and build from there. Assign Kubernetes learning as an early task, not a last-minute addition. |
| R6 | The team focuses on coding and neglects documentation, testing, or the learning diary | Lower grade despite a working application — grading covers more than just the demo | Medium | Treat documentation and tests as deliverables in every sprint, not as last-minute tasks. Review the grading criteria checklist before each sprint ends. |
| R7 | Scope creep — the team tries to add extra features (gallery, authentication, extra models) before the core flow works | The core submit-process-preview-download flow is incomplete or buggy | Medium | Finish the MVP end-to-end before starting any Sprint 2 features. Every enhancement must be agreed on in sprint planning, not added spontaneously. |

---

## 8. Assumptions

1. The university does **not** provide GPU hardware or a Kubernetes cluster. The team uses cloud GPU services (e.g., Hugging Face Inference API, Replicate) for heavy model execution and personal machines for platform development.
2. Lightweight models like YOLO v11 run locally on CPU. Heavy models (video, 3D) run on cloud GPU platforms and are called from the backend via API.
3. No user authentication is required for the MVP; requests are identified by temporary session IDs.
4. Results are stored temporarily (hours to days), not permanently.
5. The platform runs on the team's own machines or a cloud VM; internet access is needed for calling cloud GPU services.
6. The team has 2 sprints of roughly equal length within the semester.

---

## 9. Open Questions

1. Does the lecturer expect a multi-node Kubernetes cluster, or is a single-node local cluster (Docker Desktop / minikube) acceptable for the final presentation?
2. Are free-tier external AI APIs (Hugging Face, Replicate) acceptable for running the heavier models, or must all models run locally?
3. Should the gallery be opt-in or opt-out by default?
4. Are there data privacy constraints on uploaded files (e.g., GDPR considerations for images of people)?
