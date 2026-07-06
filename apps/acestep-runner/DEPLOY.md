# Deploying ACE-Step 1.5 on Kubernetes — step by step

This is the **one-time** setup that makes ACE-Step available on the platform.
After it's done, anyone adds ACE-Step to the site through the website form with
**no code** (Step 6).

Steps 1–5 need a person with cluster + registry access (that's not something the
app can do for you, because it needs your passwords and your cluster). Each step
is copy-paste. Do them in order.

---

## What you need first (prerequisites)

- `kubectl` pointed at your cluster (`kubectl get nodes` should list machines).
- A **container registry** the cluster can pull from (Docker Hub, GitHub GHCR,
  your uni's registry…). You need push access. Call its address `REGISTRY`.
- At least **one GPU node** in the cluster with the NVIDIA device plugin
  installed. Check: `kubectl get nodes -o json | grep nvidia.com/gpu` should show
  a number > 0. If it shows nothing, you have no GPU — stop here and get one, ACE-
  Step needs a GPU.
- Docker installed on your own machine (to build the image).

---

## Step 1 — Build and push the runner image (once)

From the repo root:

```powershell
cd apps/acestep-runner
docker build -t REGISTRY/acestep-runner:1.5 .
docker push REGISTRY/acestep-runner:1.5
```

Replace `REGISTRY` everywhere with your registry address. Then open `space.json`
and the two files in `k8s/` and replace `REGISTRY/acestep-runner:1.5` with the
exact same string.

> This is a big image (CUDA + PyTorch), so the build takes a while and the push
> uploads a few GB. That's normal — you only do it once.

## Step 2 — Create the shared weights volume (once)

Edit `k8s/pvc.yaml`: set `storageClassName` to your NFS class
(`kubectl get storageclass` lists options), then:

```powershell
kubectl apply -f k8s/pvc.yaml
kubectl get pvc acestep-models          # wait until STATUS says "Bound"
```

## Step 3 — Download the model weights into that volume (once)

Edit `k8s/download-weights-job.yaml` (image ref + confirm the download command),
then:

```powershell
kubectl apply -f k8s/download-weights-job.yaml
kubectl logs -f job/acestep-download-weights   # watch it download
kubectl get job acestep-download-weights        # wait for COMPLETIONS 1/1
```

If it finishes with `1/1`, the weights now live on the shared volume forever.

## Step 4 — Tell the orchestrator to use Kubernetes (once)

The orchestrator must run with these environment variables (instead of the local
subprocess mode):

```
RUNNER_BACKEND=kubernetes
K8S_NAMESPACE=default          # or your namespace
API_BASE_URL=http://<backend-service>:8000
INTERNAL_SERVICE_TOKEN=<your token>
```

Set these on the orchestrator Deployment/pod and restart it. Now, when a job runs,
the orchestrator launches a GPU runner pod that mounts the weights — all of this
is already wired in `apps/orchestrator/runner_backends.py`.

## Step 5 — (only if GPU pods stay "Pending") add scheduling hints

If runner pods get stuck `Pending`, your GPU nodes are probably "tainted." Ask
your cluster admin for the taint, and we can add a matching `nodeSelector` /
`toleration` (small config addition). On most managed clusters the GPU request
alone is enough and you can skip this.

---

## Step 6 — Add the ACE-Step space — **this is the no-code part** ✅

Now ACE-Step is ready. To put it on the site, **no code, no kubectl** — just the
website:

1. Log in, go to **Create / New Space**.
2. Fill the form:
   - **Container image:** `REGISTRY/acestep-runner:1.5`
   - **Inputs:** a text field `prompt`, a text field `lyrics`, number fields
     `duration` and `steps` (exactly the fields in `space.json`).
   - **Output type:** audio.
   - **Runner config:** paste the `runner_config` object from `space.json`
     (gpu / weights_pvc / env).
3. Publish.

`space.json` in this folder is just those same form values written down, so you
(or a grader) can copy them field-for-field — or create the space with one API
call instead of the UI:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/spaces" -H "Content-Type: application/json" -d "@space.json"
```

## Step 7 — Try it

Open the space, type `upbeat electronic with piano, 120bpm`, submit, wait for the
job to go QUEUED → RUNNING → SUCCEEDED, and the result plays inline as audio.

---

## Recap: which steps are "code"?

| Step | Who | Code? |
| --- | --- | --- |
| 1–3 build image + weights | platform team, **once** | one-time packaging (no app-repo changes needed after this branch) |
| 4–5 point orchestrator at K8s | platform team, **once** | config/env only |
| **6 add the ACE-Step space** | **any creator** | **none — website form** |
| 7 run a track | any user | none |

The everyday user experience — adding models and testing them — is 100% no-code.
The container image is the one-time translator between ACE-Step and your job
contract, built once and reused forever.
