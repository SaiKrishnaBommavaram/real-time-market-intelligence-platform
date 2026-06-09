# Local Environment

Use `.env` for local-only settings and disposable secrets.

Recommended values:

- `MARKET_ENV=local`
- `MARKET_STARTUP_CHECK_MODE=warn`
- `ALLOWED_ORIGINS=http://localhost:5173`
- default local PostgreSQL, Kafka, and MinIO ports from `docker-compose.yml`

Local workflow:

1. `cp .env.example .env`
2. `docker compose up -d`
3. start the producer and consumers
4. run `dbt run`
5. start FastAPI and the Vite dashboard

Local notes:

- `/health` is liveness only.
- `/ready` validates PostgreSQL connectivity and the cache table.
- Keep `MARKET_DB_PASSWORD`, `MARKET_API_KEY`, and `NEWS_API_KEY` in `.env` only for local use.
