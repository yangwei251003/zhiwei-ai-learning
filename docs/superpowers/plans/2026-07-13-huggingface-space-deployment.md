# Hugging Face Space Deployment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the stateless FastAPI backend to a free Hugging Face Docker Space and connect the Vercel frontend to it.

**Architecture:** A self-contained `hf-space` directory packages the backend for Docker port 7860. Supabase settings are passed only as Space Secrets. Vercel reads the HTTPS Space endpoint from `VITE_API_BASE_URL`.

**Tech Stack:** Docker, Hugging Face Spaces Docker SDK, FastAPI/Uvicorn, Alembic, Vercel, Supabase.

---

### Task 1: Docker Space manifest

**Files:** Create `hf-space/Dockerfile`, `hf-space/README.md`, `hf-space/.dockerignore`; create `backend/tests/test_huggingface_manifest.py`.

- [ ] Write a failing test asserting the Space README has `sdk: docker` and `app_port: 7860`, and the Dockerfile exposes port 7860.
- [ ] Run `python -m pytest tests/test_huggingface_manifest.py -q`; expect failure because the directory does not exist.
- [ ] Implement a Docker image that copies backend source, installs `requirements.txt`, exposes 7860, and runs Alembic plus Uvicorn on `0.0.0.0:7860`.
- [ ] Re-run the test; expect PASS.
- [ ] Commit `feat: package backend for Hugging Face Space`.

### Task 2: Remove Render-specific deployment contract

**Files:** Modify `backend/render.yaml`, `backend/.env.example`, `documents/上线部署说明.md`; create `backend/tests/test_deployment_docs.py`.

- [ ] Write a failing test asserting the deployment guide names Hugging Face rather than Render.
- [ ] Run the test; expect failure because the guide is absent or Render-specific.
- [ ] Document Hugging Face Secrets, port 7860, Supabase settings, Vercel URL and cold-start behavior. Keep `render.yaml` only as an optional non-default artifact or remove it from the release path.
- [ ] Re-run the test; expect PASS.
- [ ] Commit `docs: document Hugging Face free deployment`.

### Task 3: Publish and deploy

**Files:** Modify `documents/测试报告.md`, `documents/上线部署说明.md`.

- [ ] Run full backend and frontend tests plus production build.
- [ ] Create a Hugging Face Space repository using Docker SDK and upload `hf-space` plus the backend source.
- [ ] Add only fresh secrets in Space Settings, verify `/health`, then obtain the HTTPS Space URL.
- [ ] Create/import Vercel project from `frontend`, set `VITE_API_BASE_URL`, deploy, set final Space CORS, and redeploy.
- [ ] Perform public end-to-end tests and record both URLs and free-tier cold-start limitation.
