# 📝 Multi-Tenant AI Assistant with RAG

AI assistant platform with multi-tenant RAG, Postgres/PgVector, and analytics. Uses local embeddings, Pgvector, and Celery background tasks to process and query uploaded documents.

**Quick Links**
- **App entry:** [app/main.py](app/main.py)
- **Celery tasks:** [app/workers/celery_task.py](app/workers/celery_task.py)
- **RAG service:** [app/services/rag_service.py](app/services/rag_service.py)

**Features**
- Multi-tenant architecture (separate data per tenant)
- Document upload and processing (embedding, chunking)
- Vector store using Pgvector
- Search and answer (RAG) endpoints
- Background processing via Celery
- Supports streaming responses via WebSocket
- Async FastAPI backend with PostgreSQL + Redis

**Prerequisites**
- Python 3.13+ (project uses `pyproject.toml` for dependencies)
- Redis (for Celery broker & cache)
- Pgvector (local or Docker)
- local embedding, re-ranker models placed under `ai_models/embeddings`, `ai_models/rerank`

**Quickstart (local)**
1. Create a Python virtualenv and install dependencies (see `pyproject.toml`):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. Start Redis (example using Docker):

```bash
docker run -d -p 6379:6379 redis:alpine
```

3. Start Pgvector in Docker if you use a standalone service:

- Run this command for pull and run pgvector.
```bash
docker run -d --name pgdb -e POSTGRES_USER=myuser -e POSTGRES_PASSWORD=myser1234 -e POSTGRES_DB=bbotdb -p 5432:5432 pgvector/pgvector:pg17
```

- Connect to the database
```bash
docker exec -it pgdb psql -U myuser -d bbotdb
```

- Enable the vector extension:
```bash
CREATE EXTENSION IF NOT EXISTS vector;
```

- Initialize Alembic migrations. Before that update this sqlalchemy.url in alembic.ini file.
```bash
alembic upgrade head
```

- Run following command for seed the role permissions and create super admin with new password.
```bash
python -m scripts.seed_roles_and_premissions
python -m scripts.create_super_admin
```

4. Create copy of .env.example like .env and update following:
- `ASYNC_DATABASE_URL`, `SYNC_DATABASE_URL`, `REDIS_URL`, `EMBEDDING_MODEL`, `RERANK_MODEL`, 
  `LLM_MODEL`

5. Start the API (examples taken from workspace):

```bash
# using uv (as in workspace terminals)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 1 --loop=asyncio

# or directly with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 1  --loop=asyncio
```

5. Start Celery worker and monitoring (from repo root):

```bash
uv run celery -A app.workers.celery_task.celery_app worker --loglevel=info --concurrency=2 -P gevent
uv run celery -A app.workers.celery_task.celery_app flower --port=5555
```

**API examples**
- Upload a document (multipart/form-data):

```bash
curl -X POST "http://localhost:8001/api/v1/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/leave_policy.pdf" \
  -F "category=leave_policy"
```

- List a document

```bash
curl --request GET \
  --url http://localhost:8001/api/v1/documents \
  --header 'Authorization: Bearer token'
```

- Query the index:

```bash
curl -X POST "http://localhost:8001/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "question": "How many annual leaves am I entitled to?",
    "filters": {"category": "leave_policy"},
    "top_k": 5
  }'
```

- Chat with chatbot

```bash
npm install -g wscat
wscat -c "ws://localhost:8001/api/v1/ws/chat?agen_id=-1&token=asdfsdfsdfsdfsddsf"
```

- Delete document

```bash
curl --request DELETE \
  --url http://localhost:8001/api/v1/documents/42d509bc-015c-47d2-be69-26804504f48d \
  --header 'Authorization: Bearer token'
```

**Useful paths**
- [app/main.py](app/main.py) — FastAPI app and main route
- [app/api/router.py](app/api/router.py) — routes and enpoints with version
- [app/ai/retrieval/pgvector_manager.py](app/ai/retrieval/pgvector_manager.py) — Pgvector helper
- [app/ai/embeddings/embedding_manager.py](app/ai/embeddings/embedding_manager.py) — Embedding model loader
- [app/ai/llm/llm_manager.py](app/ai/llm/llm_manager.py) — LLM / generation wrapper
- [app/services/rag_service.py](app/services/rag_service.py) — RAG orchestration
- [app/workers/process_doc.py](app/tasks/process_doc.py) — document processing pipeline
- [ai_models/embeddings](ai_models/embeddings/) — local embedding model artifacts
- [ai_models/rerank](ai_models/rerank/) — local rerank model artifacts
- [app/db/models](app/db/models) — db related models an config
- [data/uploads](data/uploads/) — incoming uploaded files

**Maintenance & utilities**
- Reset Redis (careful):

```bash
redis-cli flushdb   # clear current DB
redis-cli flushall  # clear all DBs
```

**Docker Compose**

A `docker-compose.yml` is provided to run Redis, Postgres, the web API, a Celery worker and Flower for local development.

Quick commands:

```bash
# build and start all services in background
docker compose up --build -d

# follow logs for the web service
docker compose logs -f web

# stop and remove containers, networks and anonymous volumes
docker compose down -v
```

Ports exposed by the compose setup:
- Web API: `8001`
- Pgvector: `5432`
- Redis: `6379`
- Flower: `5555`

Notes:
- The compose `web`, `celery` and `flower` services mount the project directory and run `pip install -e .` at startup. For faster iterative development, activate a local virtualenv and install the package locally instead of relying on container installs.
- Execute the script `scripts/get_embedding_model.py` to download the embedding model, re-rank model, and then copy the path to the .env file.`

**TODOs**
- Implement JWT.
- DB integration for audit trails.
- Monitoring.
- etc.