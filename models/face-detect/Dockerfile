# OpenCV Haar-cascade face-detection runner for AI-Spaces.
# python:3.11 with the SDK copied in (only needs httpx). No torch, no weight
# downloads — the Haar cascade ships inside opencv, so the image stays ~150 MB.
FROM python:3.11-slim

WORKDIR /app

# libglib2.0-0 is needed by opencv-python-headless at import time.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY runner_sdk.py inference.py ./

CMD ["python", "inference.py"]