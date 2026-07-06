# ACE-Step 1.5 runner image. Needs CUDA + PyTorch, so it is much larger than the
# orchestrator image — build/push it to the registry the cluster pulls from and
# reference it as the space's container_image.
FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

# ffmpeg is required for mp3/flac/opus/aac encoding of the generated audio.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY runner.py .

# Model weights are mounted here at run time (see runner_config.weights_pvc in
# apps/orchestrator/runner_backends.py). Baking multi-GB weights into the image
# is avoided on purpose.
ENV ACESTEP_CHECKPOINT_DIR=/models

CMD ["python", "runner.py"]
