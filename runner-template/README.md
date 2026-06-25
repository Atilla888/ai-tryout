# Model runner template & contract

This directory is the **runner contract** plus a copy-me reference implementation
for AI-Spaces model runners (spec §5.4, US-10). A *runner* is the containerized
unit that executes one model: it receives a job, runs inference, reports progress,
uploads artifacts, and reports its final status. The platform core never changes
when a new model is added — only the runner image and the space's JSON config.

Files:

| File | Purpose |
|------|---------|
| `runner_sdk.py` | Client over the internal runner API — handles all platform plumbing |
| `reference_runner.py` | Minimal example runner built on the SDK (the reference image) |
| `Dockerfile` | Base image (`ai-spaces-base`) with the SDK + reference runner pre-installed |
| `space-config.example.json` | Example space configuration (UI + runner config) |
| `requirements.txt` | Runtime dependencies for the base image |

## Execution model

The orchestrator starts one worker per queued job (a Kubernetes Job in
production, a local subprocess in dev). It injects these environment variables:

| Variable | Description |
|----------|-------------|
| `JOB_ID` | Internal job id used in all runner API calls |
| `SPACE_ID` | Internal id of the space being run |
| `BACKEND_API_URL` | Base URL for the backend internal API |
| `RUNNER_TOKEN` | Token sent as the `X-Service-Token` header on every call |
| `INPUT_REFERENCE` | Reference (job id) used to fetch input |

The runner authenticates every call with `X-Service-Token: $RUNNER_TOKEN`.

## Runner API contract

All endpoints are under `BACKEND_API_URL` and require the service token header.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/internal/jobs/{JOB_ID}/runner-input` | Fetch the input payload and the list of uploaded INPUT files |
| GET | `/internal/artifacts/{artifactId}/content` | Download an input file's bytes |
| PATCH | `/internal/jobs/{JOB_ID}/progress` | Report progress (`progress_percent`, `message`); first call flips the job to `RUNNING` |
| POST | `/internal/jobs/{JOB_ID}/artifacts` | Upload a generated output file (multipart: `artifact_type`, `preview_supported`, `file`) |
| PATCH | `/internal/jobs/{JOB_ID}/succeed` | Mark the job `SUCCEEDED` |
| PATCH | `/internal/jobs/{JOB_ID}/fail` | Mark the job `FAILED` (`error_code`, `error_message`) |
| GET | `/internal/jobs/{JOB_ID}` | Read job status (poll for `CANCELLING` to stop early) |

### Lifecycle

1. **Fetch input** — `GET …/runner-input` returns `input_payload` (the form
   values) and `input_artifacts` (uploaded files, each with a `content_url`).
2. **Download inputs** — `GET` each `content_url` to retrieve the uploaded files.
3. **Run inference** and **report progress** periodically.
4. **Upload artifacts** — `POST …/artifacts` for each output file. A job must not
   be marked succeeded until its expected output has been uploaded.
5. **Report final status** — `succeed` on success, `fail` on error, then exit.
6. **Cancellation** — if `GET …/{JOB_ID}` returns `CANCELLING`/`CANCELLED`, stop
   and exit; the orchestrator also terminates the worker and finalizes the job.

### Output format

Artifacts declare an `artifact_type` (e.g. `text`, `image`, `video`, `3d`) and
whether browser preview is supported. Images use JPEG as the baseline (C-13); 3D
output uses GLB/GLTF. Every artifact is linked to exactly one job.

## Writing your own runner

1. Start from `reference_runner.py` and replace `run_inference` with your model.
2. Build an image **FROM** `ai-spaces-base` that adds your model dependencies and
   sets `CMD` to your runner script.
3. Push the image to the registry the cluster can pull from.
4. Register a space whose `container_image` points at your image, with a
   `ui_config`/`runner_config` like `space-config.example.json`.

```python
from runner_sdk import Runner

with Runner.from_env() as runner:
    job = runner.get_input()
    runner.report_progress(50, "working")
    # ... produce output_file ...
    runner.upload_artifact(output_file, "image/jpeg", artifact_type="image", preview_supported=True)
    runner.succeed()
```

## Local test (no cluster)

Point the orchestrator's subprocess backend at a runner script:

```bash
cd apps/orchestrator
export INTERNAL_SERVICE_TOKEN=changeme-internal-token
export RUNNER_SCRIPT=$(pwd)/fake_runner.py   # or runner-template/reference_runner.py
python main.py
```
