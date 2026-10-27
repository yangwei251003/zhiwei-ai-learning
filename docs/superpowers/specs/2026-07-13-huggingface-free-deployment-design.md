# Hugging Face Free Deployment Design

**Goal:** Replace the Render backend with a no-card deployment using a Hugging Face Docker Space, Vercel frontend, and Supabase persistence.

## Architecture

- Vercel serves `frontend` and receives `VITE_API_BASE_URL` at build time.
- A Hugging Face Docker Space runs the FastAPI application on port `7860`; it is stateless and may sleep when idle.
- Supabase PostgreSQL, pgvector, and private Storage remain the sole durable stores.
- The Space URL becomes the only production API origin allowed by the frontend; Render is removed from deployment documentation.

## Docker Space Contract

- The Space repository contains the backend source, `Dockerfile`, `requirements.txt`, Alembic configuration, and a `README.md` YAML header declaring `sdk: docker` and `app_port: 7860`.
- Docker starts `alembic upgrade head` before Uvicorn listens on `0.0.0.0:7860`.
- Hugging Face Secrets contain `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SECRET_KEY`, and rotated LLM credentials. No secret is committed or sent to Vercel.
- `CORS_ORIGINS` is updated to the final Vercel production URL after the frontend is deployed.

## Free-tier Behavior

- A free CPU Space can cold-start after inactivity. The existing frontend reconnect and loading UI is the user-facing fallback.
- The Space filesystem is not treated as durable; all uploaded documents and retrieval chunks are in Supabase.
- The application keeps lexical retrieval available if the local embedding model is unavailable during a cold start.

## Verification

1. Build the backend Docker image locally.
2. Verify the Space `/health` endpoint.
3. Set Vercel `VITE_API_BASE_URL` to the Space URL and deploy.
4. Set Space `CORS_ORIGINS` to the Vercel URL and restart the Space.
5. Test registration, refresh, chat SSE, knowledge upload/search, resources and learning path against public URLs.

## Security

- Use only freshly rotated platform and model credentials in Hugging Face Secrets.
- The Supabase service role is server-only; the public anon key is not used for backend writes.
- The Space source may be public for free hosting; therefore all configuration must be in Secrets and `.env` remains ignored.
