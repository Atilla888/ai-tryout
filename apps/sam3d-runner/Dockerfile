FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-dev python3-pip \
    git wget curl \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3.11 /usr/bin/python

WORKDIR /app

# Platform runner SDK
COPY runner_sdk.py .

# Runner dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# SAM 3D Objects repository
RUN git clone https://github.com/facebookresearch/sam-3d-objects.git /opt/sam-3d-objects

# Install SAM 3D Objects dependencies (without conda — pip-compatible subset)
RUN pip install --no-cache-dir \
    torch torchvision --index-url https://download.pytorch.org/whl/cu124 \
    && pip install --no-cache-dir \
    hydra-core omegaconf \
    segment-anything \
    open3d \
    trimesh \
    huggingface_hub

# Runner script
COPY runner.py .

# Model checkpoints are mounted at runtime (do not bake tokens into the image)
# docker run -v /path/to/checkpoints:/checkpoints/hf ai-spaces-sam3d:latest
ENV CHECKPOINT_DIR=/checkpoints/hf
ENV SAM3D_PYTHON=/usr/bin/python
ENV SAM3D_REPO=/opt/sam-3d-objects

CMD ["python", "runner.py"]
