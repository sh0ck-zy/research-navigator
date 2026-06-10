# ── Stage 1: build the frontend (Vite → frontend/dist) ───────────────────────
FROM node:20-slim AS web
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime (FastAPI serves API + build + data) ──────────────
FROM python:3.11-slim

# Non-root user (Hugging Face Spaces convention: uid 1000, writable $HOME)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface

WORKDIR /app

# CPU-only torch keeps the image small; then the lean runtime deps
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt

# Writable app dir owned by the runtime user (library.db is written here)
RUN mkdir -p /app/data/embeddings /app/data/raw /app/data/clusters /app/frontend/data \
    && chown -R user /app
USER user

# Pre-bake the embedding model so the first search isn't a cold download
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# App code + built frontend
COPY --chown=user:user backend/ ./backend/
COPY --chown=user:user --from=web /app/frontend/dist ./frontend/dist

# Runtime data (gitignored in the main repo — shipped into the image here)
COPY --chown=user:user frontend/data/map_data.json ./frontend/data/map_data.json
COPY --chown=user:user data/embeddings/neuro_10k.npz ./data/embeddings/
COPY --chown=user:user data/raw/neuro_10k.jsonl ./data/raw/
COPY --chown=user:user data/clusters/neuro_10k_leiden.json data/clusters/neuro_10k_names.json ./data/clusters/
COPY --chown=user:user data/active_field.json ./data/

EXPOSE 7860
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "7860"]
