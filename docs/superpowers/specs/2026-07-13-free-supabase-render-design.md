# Free Supabase + Render Deployment Design

**Goal:** Deploy 知微智学 without a paid Render persistent disk while retaining durable business data, knowledge files, and retrieval data.

## Architecture

- **Vercel (free):** serves the Vue/Vite frontend. `VITE_API_BASE_URL` points to the Render API.
- **Render free Web Service:** runs FastAPI and SSE as a stateless service. It must never treat its filesystem as persistent storage. It may use a temporary directory only while parsing an upload and must delete it afterwards.
- **Supabase PostgreSQL (free):** stores the current SQLAlchemy application tables and a new tenant-scoped knowledge chunk table. The migration enables the `vector` extension and uses `vector(384)` for the existing multilingual MiniLM embedding dimensionality.
- **Supabase Storage (free):** private `knowledge-uploads` bucket stores original uploaded files. Only the FastAPI service role can read or write objects; browsers continue to call FastAPI rather than Supabase directly.

## Knowledge Retrieval

`SupabaseRAGStore` replaces the production use of `ChromaRAGStore` when `RAG_BACKEND=supabase`.

1. Indexing chunks a document, creates 384-dimensional embeddings with the existing embedding service, and upserts rows keyed by `(document_id, chunk_index)`.
2. Retrieval filters by `user_id` and `course` before ranking.
3. The primary query uses pgvector cosine distance (`<=>`) and returns the same citation shape currently consumed by agents.
4. If embeddings are unavailable, indexing marks vector data unavailable and retrieval falls back to PostgreSQL full-text ranking over the same user/course scope. The response never crosses tenants.
5. Deleting a knowledge document deletes both its Storage object and all chunk rows.

## Runtime and Security

- `DATABASE_URL` uses the Supabase Postgres connection URL with TLS required.
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are Render-only secrets. They are never bundled into Vercel output and never committed.
- `CORS_ORIGINS` contains only the Vercel production domain and any explicitly approved preview domains.
- `SECRET_KEY` is generated and held only by Render.
- Existing LLM credentials stay Render-only. Keys exposed in chat must be rotated before setting them.
- The Supabase bucket is private. RLS remains enabled; application access uses the service role only from Render.

## Free-tier Behavior

- Render may spin down after inactivity. The frontend exposes a reconnect/waking state and retries before presenting a failure.
- No Render disk is configured. All durable content is in Supabase.
- The first request after a cold start may also load the embedding model. Health checks distinguish a running process from a ready retrieval service.
- Supabase and Vercel free-tier quotas can change; alerts or paid upgrades may be needed when public traffic grows.

## Delivery Steps

1. Add failing unit and integration tests for the selected RAG backend, private Storage object lifecycle, pgvector retrieval, lexical fallback, and no-local-persistence configuration.
2. Add the Supabase RAG and Storage adapters, settings, Alembic migration, and dependency wiring until the tests pass.
3. Remove the Render persistent-disk requirement from the Blueprint and add required secret placeholders.
4. Build a Docker image that includes the embedding model needed by the free stateless service, then verify the API starts with only Supabase configuration.
5. Create the Storage bucket and enable `vector` in Supabase through its dashboard/SQL editor.
6. Create the Render free service, enter private environment variables in its dashboard, and deploy.
7. Create the Vercel project, set `VITE_API_BASE_URL`, deploy, then add the final Vercel domain to Render CORS.
8. Run a public smoke test: registration, chat SSE, upload, retrieval, resource generation, path generation, refresh, and cold-start reconnect.

## Acceptance Criteria

- The application restarts on Render without losing users, knowledge documents, or retrieval chunks.
- A private uploaded document persists in Supabase Storage and is retrievable only through its owner/course scope.
- pgvector search returns correctly filtered citations; lexical fallback returns a safe response when embedding generation fails.
- Vercel calls the configured Render URL, and all production CORS requests are restricted to approved origins.
- No public bundle, git history, or log contains database passwords, service-role keys, JWT secrets, or LLM credentials.
