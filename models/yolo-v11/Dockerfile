# YOLOv11 model runner for AI-Spaces.
# NOT built FROM ai-spaces-base: that image is python:3.14, and torch/ultralytics
# have no wheels for 3.14. We use python:3.11 and copy the SDK in ourselves —
# the SDK's only dependency is httpx.
FROM python:3.11-slim

WORKDIR /app

# libGL + glib are required by OpenCV, which ultralytics pulls in.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the weights into the image so the runner pod needs no internet at runtime.
RUN python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"

COPY runner_sdk.py inference.py ./

CMD ["python", "inference.py"]