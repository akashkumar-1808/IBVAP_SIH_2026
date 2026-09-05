# ==============================================================================
# IBVAP — Production Dockerfile for Hugging Face Docker Spaces
# Multi-stage build: React Frontend Builder + Python 3.11 Computer Vision Runtime
# ==============================================================================

# Stage 1: Compile React Operator Console
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Stage 2: Python 3.11 Computer Vision & FastAPI Backend Runtime
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOST=0.0.0.0 \
    ENVIRONMENT=production \
    APP_NAME=IBVAP-Console

# Install required system libraries for FFmpeg and OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up non-root user for Hugging Face Spaces security (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install Python dependencies
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# Copy built React frontend bundle from stage 1
COPY --chown=user:user --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy repository application source files
COPY --chown=user:user . .

# Ensure storage directories and model paths exist with write permissions
RUN mkdir -p storage/uploads storage/samples storage/evidence results/live_runs models/detector && \
    if [ -f yolov8n.pt ] && [ ! -f models/detector/yolov8n.pt ]; then \
        cp yolov8n.pt models/detector/yolov8n.pt; \
    fi

# Hugging Face Spaces default HTTP port
EXPOSE 7860

# Launch Uvicorn production server on 0.0.0.0:7860
CMD ["python", "start.py"]
