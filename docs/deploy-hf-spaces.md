# Deploy to Hugging Face Spaces (Docker)

The app is one FastAPI server that serves the API, the built galaxy, and the
data. It needs ~150 MB RAM + the embedding model (baked into the image at build).

**You do the HF login/creation** (I can't create accounts). Everything else is ready:
`Dockerfile`, `requirements-runtime.txt`, and the runtime data files.

## One-time: create the Space

1. Log in at https://huggingface.co, then create a new Space:
   **New → Space → SDK: Docker → Blank**. Name it e.g. `observatory`.
2. It gives you a git remote like `https://huggingface.co/spaces/<you>/observatory`.

## What the Space needs

A Space's `README.md` must start with this frontmatter (HF reads it to set the
container port). Put this at the **top of the README in the Space repo**:

```yaml
---
title: The Observatory
emoji: 🔭
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---
```

## Push the app + data to the Space

The data files (`map_data.json`, the `.npz`, the `.jsonl`, cluster JSONs,
`active_field.json`) are **gitignored in this repo**, so they must be force-added
when pushing to the Space. From the repo root:

```bash
# point a remote at your Space (uses git-lfs for the big files)
git remote add space https://huggingface.co/spaces/<you>/observatory
git lfs install
git lfs track "*.npz" "*.jsonl" "galaxy/data/map_data.json"

# force-add the runtime data the Dockerfile COPYs (overrides .gitignore)
git add -f \
  galaxy/data/map_data.json \
  data/embeddings/neuro_10k.npz \
  data/raw/neuro_10k.jsonl \
  data/clusters/neuro_10k_leiden.json \
  data/clusters/neuro_10k_names.json \
  data/active_field.json \
  .gitattributes
git add Dockerfile requirements-runtime.txt .dockerignore
git commit -m "Ship Observatory to HF Spaces"

# add the Space frontmatter to README, commit, then push
git push space observatory-mvp:main
```

HF builds the Docker image and serves it. First build is slow (torch + model
bake). When it's live, the Space URL is the single link to send to Rabanadas.

## Notes / caveats

- **Library persistence:** `data/library.db` lives on the container's ephemeral
  disk. A Space rebuild/restart resets saved papers. Fine for a feedback demo.
  To make it durable later: enable HF persistent storage and point `LIBRARY_DB`
  at the mounted path.
- **Memory:** free CPU Spaces have ample RAM (16 GB) for torch+faiss+MiniLM.
- **Updating:** re-push to `space` after changes; HF rebuilds automatically.

## Verify the image locally first (optional)

```bash
docker build -t observatory .
docker run -p 7860:7860 observatory
# open http://localhost:7860 — search, save a paper, export .bib
```
