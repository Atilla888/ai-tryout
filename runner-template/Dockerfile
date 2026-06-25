# Base image for AI-Spaces model runners (ai-spaces-base).
# Space creators build FROM this image, add their model code and dependencies,
# and override CMD to run their own runner. The SDK and reference runner are
# pre-installed so the platform contract is handled for them.
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY runner_sdk.py reference_runner.py ./

# Default to the reference runner; real runners override this.
CMD ["python", "reference_runner.py"]
