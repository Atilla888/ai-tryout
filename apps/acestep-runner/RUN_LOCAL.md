# Running ACE-Step on your laptop — no Kubernetes

You do **not** need Kubernetes, minikube, or kind. The platform's orchestrator has
a **subprocess backend** that runs the runner as a normal Python process on your
machine. That's the whole local story: no Docker, no image, no registry, no
cluster.

How it differs from the cluster path:

| | Cluster (K8s) | Laptop (subprocess) |
| --- | --- | --- |
| Runs the runner as… | a pod from your image | a Python child process |
| Model config comes from… | the space's `runner_config` | **shell environment variables** |
| `container_image` field | used | ignored (any non-empty value is fine) |
| Good for | production / many spaces | testing one model quickly |

---

## The honest caveats (read first)

1. **You need a GPU for it to be usable.** The standard model needs < 4 GB VRAM.
   On CPU it still runs but a song can take many minutes.
2. **You're on Windows, and ACE-Step's default LM backend is `vllm`, which does not
   install cleanly on native Windows.** Two ways around it:
   - **Recommended: use WSL2** (Ubuntu) if you have an NVIDIA GPU. ML tooling is
     Linux-first; everything below works the same inside WSL2.
   - Or try a non-vllm backend on native Windows by setting `ACESTEP_LM_BACKEND`
     (e.g. `hf`) — support depends on the acestep version.
3. This is the same "one runner script for all jobs" limitation as the fake
   runner. Fine for testing ACE-Step on its own.

---

## Steps

### 1. Install ACE-Step into the orchestrator's Python

The subprocess backend launches the runner with the **same** Python that runs the
orchestrator (`..\..\venv`), so ACE-Step must be installed there:

```powershell
..\..\venv\Scripts\pip install -r requirements.txt
# plus the right PyTorch build for your machine — see pytorch.org/get-started
# (a CUDA build if you have an NVIDIA GPU, otherwise the CPU build).
```

### 2. Download the weights to a local folder

Use ACE-Step's downloader (confirm the exact command for your version) into a
folder, e.g. `C:\acestep-models`:

```powershell
$env:ACESTEP_CHECKPOINT_DIR = "C:\acestep-models"
..\..\venv\Scripts\acestep-download   # or the documented download command
```

### 3. Start Postgres + the backend

Exactly as in the repo `README.md` (Docker Postgres, then `uvicorn`). Nothing
ACE-Step-specific here.

### 4. Start the orchestrator with the ACE-Step runner

Open `run-local.ps1`, edit the paths at the top (especially
`ACESTEP_CHECKPOINT_DIR` and `ACESTEP_DEVICE`), then run it:

```powershell
.\run-local.ps1
```

That sets the `ACESTEP_*` variables and launches the orchestrator in subprocess
mode pointed at `runner.py`.

### 5. Create a space and test — still no code

Create the ACE-Step space through the website form (or the curl below). In
subprocess mode the `container_image` is ignored, so any placeholder works:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/spaces" -H "Content-Type: application/json" -d "@space.json"
```

Then open the space, enter a prompt like `upbeat electronic with piano, 120bpm`,
submit, and the finished track plays inline.

> Note: `space.json`'s `runner_config` (gpu / weights_pvc / env) is only used by
> the Kubernetes path. On the laptop those come from `run-local.ps1` instead — the
> space itself is identical either way.
