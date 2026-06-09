# Real-Time Market Intelligence Platform

An end-to-end market data platform that:

- pulls live stock prices with `yfinance`
- streams events through Kafka
- lands raw events in S3-compatible object storage
- writes operational events into PostgreSQL
- transforms warehouse data with dbt
- exposes analytics and live lookups through FastAPI
- renders the user-facing experience in a React dashboard

## Architecture

### Data flow

1. `producers/stock_producer.py` fetches live prices for the configured ticker list.
2. The producer publishes JSON events to the Kafka topic in `MARKET_KAFKA_TOPIC`.
3. `consumers/postgres_consumer.py` consumes those events into `public.stock_prices`.
4. `consumers/s3_consumer.py` writes the same raw events into the S3 bucket path `raw/stocks/date=.../ticker=.../`.
5. dbt reads `public.stock_prices` and builds analytics models, including `analytics.daily_stock_summary`.
6. `api/` serves:
   - warehouse summaries from dbt models
   - live ticker data from Yahoo Finance
   - ticker news from NewsAPI
   - enriched news analysis with source quality, entity extraction, clustering, and impact scoring
   - local news summaries using a Hugging Face summarization model
   - analytics endpoints for movers, volatility, sentiment-over-time, ticker correlation, and intraday rollups
   - persisted watchlists and watchlist alert history scoped to the active API principal
   - an observability metrics snapshot for API cache/auth/request behavior
   - route handlers from `api/routes/`
   - business logic from `api/services/`
   - persistence access from `api/repositories/`
7. `dashboard/` calls the API and displays health, warehouse summaries, live ticker data, and news sentiment.
   The dashboard now uses a TanStack Query data layer for polling, stale/fresh state, retries, and cross-view cache reuse.

### Repo layout

- `api/`: FastAPI backend
- `dashboard/`: React + Vite frontend
- `producers/`: Kafka event producer
- `consumers/`: PostgreSQL and S3 consumers
- `dbt/market_analytics/`: dbt project for warehouse transformations
- `airflow/dags/`: Airflow data quality DAG
- `postgres/init/`: PostgreSQL init SQL
- `aws/`: AWS deployment notes

## Prerequisites

Install these locally:

- Docker Desktop with Compose
- Python `3.11`
- Node.js `20+`
- `dbt-postgres` CLI

Optional but recommended:

- `psql`
- an S3 client such as the MinIO web console

## Local Quickstart

### 1. Create local environment variables

```bash
cp .env.example .env
```

Important variables:

- `MARKET_ENV`, `MARKET_DEBUG`, `LOG_LEVEL`: environment selection and runtime verbosity. Use `local`, `dev`, or `prod`.
- `MARKET_DB_*`: PostgreSQL connection
- `MARKET_KAFKA_*`: Kafka connection and topic
- `MARKET_S3_*`: MinIO/S3 connection and bucket
- `MARKET_PRODUCER_POLL_SECONDS`, `MARKET_PRODUCER_MAX_RETRIES`, `MARKET_PRODUCER_BACKOFF_SECONDS`: producer polling and retry behavior
- `MARKET_ENABLE_HISTORY_BACKFILL`, `MARKET_HISTORY_PERIOD`, `MARKET_HISTORY_INTERVAL`, `MARKET_HISTORY_LOOKBACK_DAYS`: producer-driven historical backfill and intraday bar settings
- `MARKET_CONSUMER_MAX_RETRIES`, `MARKET_CONSUMER_BACKOFF_SECONDS`: consumer retry and commit behavior
- `MARKET_DQ_MAX_EVENT_AGE_MINUTES`, `MARKET_DQ_MAX_SUMMARY_AGE_HOURS`: Airflow freshness thresholds
- `NEWS_API_KEY`: required for `/stocks/{ticker}/news` and `/stocks/{ticker}/news/summary`
- `NEWS_API_KEY_FILE`: optional file-based secret source for shared/dev/prod deployments
- `MARKET_API_KEY`: optional shared API key for protecting non-health API routes
- `MARKET_API_KEY_FILE`: optional file-based secret source for shared/dev/prod deployments
- `MARKET_DB_PASSWORD_FILE`: optional file-based secret source for shared/dev/prod deployments
- `MARKET_RATE_LIMIT_MAX_REQUESTS`, `MARKET_RATE_LIMIT_WINDOW_SECONDS`: in-memory per-client API rate limits
- `MARKET_LIVE_CACHE_TTL_MINUTES`, `MARKET_NEWS_CACHE_TTL_MINUTES`, `MARKET_NEWS_SUMMARY_CACHE_TTL_MINUTES`: explicit cache freshness windows for live quotes, raw news, and summarized news
- `MARKET_ALLOW_STALE_CACHE_FALLBACK`: whether stale cached data may be served when upstream refresh fails
- `MARKET_STARTUP_CHECK_MODE`: `off`, `warn`, or `strict` startup readiness behavior
- `VITE_API_BASE_URL`: frontend API base URL
- `VITE_API_KEY`: frontend API key header value when `MARKET_API_KEY` is enabled
- `ALLOWED_ORIGINS`, `ALLOWED_ORIGIN_REGEX`, `ALLOWED_METHODS`, `ALLOWED_HEADERS`, `CORS_ALLOW_CREDENTIALS`: backend CORS

Environment guidance:

- `local`: permissive defaults for local development
- `dev`: non-production shared environment
- `prod`: validates stronger requirements, including non-default DB credentials, configured API auth, configured news API key, and non-localhost CORS origins

Environment-specific runbooks:

- local: [docs/environments/local.md](/Users/saikrishnabommavaram/Downloads/real-time-market-intelligence-platform/docs/environments/local.md)
- dev: [docs/environments/dev.md](/Users/saikrishnabommavaram/Downloads/real-time-market-intelligence-platform/docs/environments/dev.md)
- prod: [docs/environments/prod.md](/Users/saikrishnabommavaram/Downloads/real-time-market-intelligence-platform/docs/environments/prod.md)

### 2. Start the infrastructure stack

```bash
docker compose up -d
```

If you created the Postgres volume before the `airflow` database init script existed, recreate it once:

```bash
docker compose down -v
docker compose up -d
```

The same applies to schema changes in `postgres/init/01-create-databases.sql`.
For an existing local volume, either recreate the volume or apply the init SQL
manually:

```bash
psql "postgresql://postgres:postgres@localhost:55432/market_data" -f postgres/init/01-create-databases.sql
```

Default host ports:

- PostgreSQL: `55432`
- ZooKeeper: `52181`
- Kafka: `59092`
- MinIO API: `59000`
- MinIO console: `59001`
- Airflow webserver: `58080`

### 3. Create the MinIO bucket

The S3 consumer assumes the bucket already exists. Create it before running `consumers/s3_consumer.py`.

- Open `http://localhost:59001`
- Log in with `MARKET_MINIO_ROOT_USER` / `MARKET_MINIO_ROOT_PASSWORD`
- Create the bucket named by `MARKET_S3_BUCKET` (default: `market-data-lake`)

### 4. Initialize Airflow once

The compose file starts the webserver and scheduler, but Airflow still needs its metadata DB initialized and a user created.

```bash
docker compose run --rm airflow-webserver airflow db migrate
docker compose run --rm airflow-webserver airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@example.com --password admin
```

Then open `http://localhost:58080`.

The DAG `market_data_quality_check` now validates:

- raw row presence in `public.stock_prices`
- raw event freshness
- duplicate raw events grouped by `ticker`, `event_time`, and `source`
- freshness of `analytics.daily_stock_summary`

### 5. Install application dependencies

Backend:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Frontend:

```bash
cd dashboard
npm ci
cd ..
```

### 6. Configure the dbt profile

This repo does not commit `~/.dbt/profiles.yml`. Create one locally so dbt writes to the `analytics` schema that the API expects.

```yaml
market_analytics:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      port: 55432
      user: postgres
      password: postgres
      dbname: market_data
      schema: analytics
      threads: 4
```

Validate it:

```bash
cd dbt/market_analytics
dbt debug
cd ../..
```

### 7. Start the pipeline processes

Use separate terminals.

Producer:

```bash
source .venv/bin/activate
python producers/stock_producer.py
```

The producer now batches sends per polling cycle, retries transient Yahoo/Kafka failures, emits structured JSON logs, and can backfill recent historical bars before live polling starts.

PostgreSQL consumer:

```bash
source .venv/bin/activate
python consumers/postgres_consumer.py
```

The PostgreSQL consumer now commits Kafka offsets only after a successful insert or an explicit invalid-event skip.

S3 consumer:

```bash
source .venv/bin/activate
python consumers/s3_consumer.py
```

The S3 consumer now retries uploads, commits offsets only after a successful upload or explicit skip, and emits structured JSON logs.

### 8. Build warehouse models with dbt

After the producer and PostgreSQL consumer have created some rows:

```bash
cd dbt/market_analytics
dbt source freshness
dbt run
dbt test
cd ../..
```

The dbt project now includes:

- explicit staging and mart model configs
- source freshness rules for `public.stock_prices`
- stronger schema tests for source, staging, and mart models
- singular tests for duplicate raw events and invalid summary price bounds
- hourly intraday rollups in `analytics.intraday_stock_rollup`
- daily anomaly fields such as `price_change_pct`, `volume_vs_avg_ratio`, and `anomaly_flag`
- drawdown and recovery analytics in `analytics.stock_drawdown_recovery`
- rolling volatility and Sharpe-like indicators in `analytics.stock_risk_indicators`
- sector-level daily aggregates in `analytics.sector_daily_summary`
- anomaly history records in `analytics.stock_anomaly_history`

### 9. Start the API

```bash
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

API docs and health checks:

- `http://localhost:8000/`
- `http://localhost:8000/health`
- `http://localhost:8000/ready`
- `http://localhost:8000/docs`

Additional analytics routes:

- `/analytics/intraday/movers`
- `/analytics/intraday/{ticker}`
- `/analytics/movers`
- `/analytics/volatility`
- `/analytics/sentiment/{ticker}`
- `/analytics/correlations/{ticker}`
- `/analytics/drawdowns`
- `/analytics/risk`
- `/analytics/sectors`
- `/analytics/anomalies`

Watchlist and observability routes:

- `GET /watchlist`
- `POST /watchlist`
- `DELETE /watchlist/{ticker}`
- `GET /watchlist/alerts`
- `GET /observability/metrics`

The watchlist routes are scoped to the current request principal. When `MARKET_API_KEY` is enabled, the backend derives a stable profile key from the presented API key and persists watchlist thresholds in PostgreSQL instead of relying only on browser local storage.

The observability endpoint reports API request counts/latency, auth and rate-limit events, cache hit vs stale fallback counters, and news-provider/summarizer counters. Producer and consumer processes now also emit periodic structured metric snapshots in their own logs.

Cache-backed endpoints now return cache freshness metadata such as `state`, `is_stale`, `expires_at`, and `updated_at` so callers can distinguish fresh values from stale fallback responses.

The API now separates liveness from readiness:

- `/health`: process liveness only
- `/ready`: PostgreSQL connectivity and cache-table readiness

In shared and production environments, prefer mounted secret files or platform secret managers over committed `.env` files. `MARKET_DB_PASSWORD_FILE`, `MARKET_API_KEY_FILE`, and `NEWS_API_KEY_FILE` are supported for that path.

### 10. Start the frontend

```bash
cd dashboard
npm install
npm run dev
```

Then open the Vite URL, usually `http://localhost:5173`.

## End-to-End Run Order

If you want the shortest path to a working demo, use this order:

1. `cp .env.example .env`
2. `docker compose up -d`
3. create the MinIO bucket
4. initialize Airflow
5. install Python and Node dependencies
6. create `~/.dbt/profiles.yml`
7. run the producer
8. run both consumers
9. run `dbt run`
10. start FastAPI
11. start the React dashboard

If `/market/summary` is empty, the usual cause is that dbt has not run yet or the dbt profile schema is not `analytics`.

## API Surface

### `GET /`

Returns the API status message and the main endpoint list.

### `GET /health`

Reports API liveness without dependency checks.

### `GET /ready`

Reports startup readiness, including PostgreSQL connectivity and required cache-table availability.

### `GET /market/summary`

Reads up to 100 rows from `analytics.daily_stock_summary`.

### `GET /stocks/{ticker}/summary`

Returns warehouse summary history for one ticker from `analytics.daily_stock_summary`.

### `GET /stocks/{ticker}/live`

Returns live price and volume from Yahoo Finance. The API caches successful lookups for the current UTC day in `stock_search_cache` and falls back to that cache if the provider later fails.

### `GET /stocks/{ticker}/news`

Fetches up to 5 recent articles from NewsAPI, scores sentiment with VADER, caches the results by ticker and day, and returns the article list.

### `GET /stocks/{ticker}/news/summary`

Builds a 2-step local summary:

1. summarize each article into a short note
2. summarize the combined ticker narrative

The default model is `sshleifer/distilbart-cnn-12-6`. On the first request, the model may need to download locally. If summarization fails, the API returns a deterministic fallback summary instead of a hard error.

## Backend Layout

- `api/main.py`: app assembly and CORS middleware
- `api/config.py`: environment-backed settings
- `api/routes/`: FastAPI route handlers
- `api/services/`: market, news, and summarization logic
- `api/repositories/`: database and cache access

## Data Stores

### PostgreSQL

Operational tables:

- `public.stock_prices`: raw streamed stock events
- `public.stock_search_cache`: cached live-price and news responses created by the API

Analytics schema:

- `analytics.daily_stock_summary`: dbt mart used by the dashboard and summary endpoints

### S3 / MinIO

Raw event layout:

```text
raw/stocks/date=YYYY-MM-DD/ticker=SYMBOL/event_<timestamp>.json
```

## Airflow

`airflow/dags/market_data_quality_dag.py` runs an hourly quality check against PostgreSQL and validates raw row presence, raw freshness, duplicate raw events, and mart freshness.

Notes:

- The DAG validates both raw ingestion and the freshness of the dbt mart.
- The default DAG `start_date` is `2026-01-01`.

## Frontend Deployment on Netlify

This repo includes `netlify.toml` for deploying `dashboard/`.

Set:

```bash
VITE_API_BASE_URL=https://<your-public-api-domain>
```

Example:

```bash
VITE_API_BASE_URL=https://real-time-market-intelligence-api.onrender.com
```

The dashboard uses TanStack Query. After pulling these changes, refresh frontend dependencies with `npm install` before rebuilding.

## Backend Deployment on Render

This repo includes `render.yaml` for the FastAPI service.

Required backend environment variables:

- `MARKET_ENV=prod`
- `ALLOWED_ORIGINS`
- `ALLOWED_ORIGIN_REGEX` if you need dynamic preview domains
- `ALLOWED_METHODS`
- `ALLOWED_HEADERS`
- `CORS_ALLOW_CREDENTIALS`
- `MARKET_STARTUP_CHECK_MODE=strict`
- `MARKET_PRODUCER_POLL_SECONDS`
- `MARKET_PRODUCER_MAX_RETRIES`
- `MARKET_PRODUCER_BACKOFF_SECONDS`
- `MARKET_CONSUMER_MAX_RETRIES`
- `MARKET_CONSUMER_BACKOFF_SECONDS`
- `MARKET_DQ_MAX_EVENT_AGE_MINUTES`
- `MARKET_DQ_MAX_SUMMARY_AGE_HOURS`
- `NEWS_API_KEY`
- `NEWS_API_KEY_FILE` as an alternative to `NEWS_API_KEY`
- `MARKET_DB_HOST`
- `MARKET_DB_PORT`
- `MARKET_DB_NAME`
- `MARKET_DB_USER`
- `MARKET_DB_PASSWORD`
- `MARKET_DB_PASSWORD_FILE` as an alternative to `MARKET_DB_PASSWORD`
- `MARKET_API_KEY` or `MARKET_API_KEY_FILE`

Start command:

```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

Health checks should target `/ready` so traffic is only sent once the database and cache table are ready.

## AWS Deployment Baseline

The AWS split deployment path in this repo is:

- frontend: Amplify Hosting
- backend: Elastic Beanstalk
- database: Amazon RDS for PostgreSQL
- object storage: Amazon S3

Details: [aws/README.md](/Users/saikrishnabommavaram/Downloads/real-time-market-intelligence-platform/aws/README.md)

## Troubleshooting steps:

### `dbt run` succeeds but the API still fails on `/market/summary`

Check that your dbt profile schema is `analytics`. The API queries `analytics.daily_stock_summary` directly.

### `/stocks/{ticker}/news` returns `NEWS_API_KEY is not configured`

Set `NEWS_API_KEY` or `NEWS_API_KEY_FILE` and restart the API.

### The first news summary request is slow

That is expected if the local Hugging Face model has not been downloaded yet.

### The S3 consumer fails with `NoSuchBucket`

Create the MinIO bucket first. The consumer does not create it automatically.

### Consumer or producer logs look different after the pipeline changes

That is expected. The producer and consumers now emit structured JSON logs to make retries, offsets, and sink failures easier to trace.

### Airflow is up but login or metadata tables are broken

Run the Airflow initialization commands in the quickstart section, then restart the compose stack if needed.
