# Fake runner

Stand-in for a real model container during local development. It sleeps between progress updates, uploads a small text file, and marks the job succeeded. The orchestrator normally starts it for you; you only run this script by hand when debugging.

The job should already be in `STARTING` — the orchestrator calls the start endpoint before spawn.

You need Python 3.14+, a running API, and these environment variables: `JOB_ID`, `API_BASE_URL`, and `INTERNAL_SERVICE_TOKEN`. Set `SIMULATE_FAILURE=true` if you want to test a failed job instead of success.

```powershell
cd apps/fake-runner
pip install -r requirements.txt

$env:JOB_ID = "your-job-uuid"
$env:API_BASE_URL = "http://127.0.0.1:8000"
$env:INTERNAL_SERVICE_TOKEN = "changeme-internal-token"

python fake_runner.py
```

Without the orchestrator you must start the job yourself first:

```powershell
curl.exe -X PATCH "http://127.0.0.1:8000/internal/jobs/JOB_ID/start" -H "X-Service-Token: changeme-internal-token"
```

Then run `python fake_runner.py`.

The script reports 20%, 40%, 60%, and 80% progress with a short pause between each step, uploads `dummy_result.txt`, and calls succeed. With the orchestrator and UI running, you can submit from the website and watch the job page update instead.
