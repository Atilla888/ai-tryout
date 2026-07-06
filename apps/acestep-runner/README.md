# ACE-Step 1.5 runner

A runner container that adds **ACE-Step 1.5 text-to-music** as a space on the
AI-Spaces platform. It follows the same runner contract as
[`apps/orchestrator/fake_runner.py`](../orchestrator/fake_runner.py): pull the
job input, run the model, upload the result as an `output_audio` artifact (which
the frontend renders with an inline `<audio>` player), and report success.

> **Kubernetes setup:** [DEPLOY.md](DEPLOY.md). **Run on your laptop (no cluster,
> no minikube/kind):** [RUN_LOCAL.md](RUN_LOCAL.md). This README is the overview.

## What's here

| File | Purpose |
| --- | --- |
| `runner.py` | The runner. Contract code up top, ACE-Step call isolated in `generate_audio()`. |
| `Dockerfile` | CUDA + PyTorch + ACE-Step image. |
| `requirements.txt` | `httpx` + `acestep` (pin the version to match `runner.py`'s imports). |
| `space.json` | The space definition — the "drop-in" payload for `POST /spaces`. |
| `k8s/pvc.yaml` | Shared volume for the model weights. |
| `k8s/download-weights-job.yaml` | One-time Job that fills that volume. |
| `DEPLOY.md` | Dummy-proof Kubernetes runbook. |
| `RUN_LOCAL.md` + `run-local.ps1` | Run on a laptop with no cluster (subprocess backend). |

## Is this a drop-in?

**The space is a drop-in; the runner is not.** You must build/push the image and
have a GPU node once. After that, adding the space is a single API call, and new
model variants/output formats are just `runner_config.env` edits — no rebuild.

## 1. Build & push the image

```powershell
cd apps/acestep-runner
docker build -t REGISTRY/acestep-runner:1.5 .
docker push REGISTRY/acestep-runner:1.5
```

Replace `REGISTRY` with the registry your cluster pulls from, and set the same
value in `space.json` → `container_image`.

## 2. Provide the model weights (recommended: mounted volume)

Baking multi-GB weights into the image is slow and re-downloading them per job is
worse. Instead, download them once onto a `ReadOnlyMany` PVC (NFS-backed fits
your storage setup) and let the runner mount it:

- `space.json` → `runner_config.weights_pvc` = the PVC name (`acestep-models`)
- `runner_config.weights_mount` = where it mounts (`/models`)
- `runner_config.env.ACESTEP_CHECKPOINT_DIR` = same path (`/models`)

The orchestrator's `KubernetesRunnerBackend` mounts this PVC and requests
`runner_config.gpu` GPUs (`nvidia.com/gpu`) on the pod — see
[`apps/orchestrator/runner_backends.py`](../orchestrator/runner_backends.py).

Set the model variant/format via `runner_config.env` (already in `space.json`):
`ACESTEP_CONFIG_PATH`, `ACESTEP_LM_MODEL_PATH`, `ACESTEP_AUDIO_FORMAT`,
`ACESTEP_STEPS`. Use the exact config/LM names produced by ACE-Step's
`acestep-download` step.

## 3. Register the space (the drop-in)

Edit `container_image` in `space.json`, then:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/spaces" -H "Content-Type: application/json" -d "@space.json"
```

That's it — the space now shows up in the UI with a prompt/lyrics form and plays
the generated track inline. (You can also create it through the Space Editor UI;
`space.json` just documents the exact fields.)

## Local test without a cluster (subprocess backend)

No Kubernetes/minikube/kind required — the orchestrator's subprocess backend runs
`runner.py` as a plain child process. Full laptop runbook: [RUN_LOCAL.md](RUN_LOCAL.md)
(`run-local.ps1` sets the env and starts it). The standard model needs < 4 GB VRAM;
CPU works but is slow.

## Notes / caveats

- **One job per container.** The platform launches a fresh worker per job, so the
  model loads on every job. That's fine for a demo; a long-lived inference server
  would be the next step if throughput matters.
- **Pin `acestep`.** `runner.py` targets the documented entry points
  (`acestep.handler` / `acestep.llm_inference` / `acestep.inference`). If you pin a
  version whose API differs, adjust `generate_audio()` only — the contract code is
  version-independent.
- **Input field types.** `space.json` uses only `text`/`number` so it passes the
  backend's `validate_space_config`. The frontend also supports `textarea`, but
  that type is rejected by that validator — switch to it only if you skip the
  validate step.
