# real-time-market-intelligence-platform
End-to-end real-time data platform that ingests financial and news data via Kafka, stores raw and curated datasets in an S3 data lake, orchestrates pipelines with Airflow, transforms data using dbt, and serves analytics through FastAPI and dashboards.

## Local stack isolation

This repo now defaults to its own host port range so it can run beside other Docker stacks:

- PostgreSQL: `55432`
- Kafka: `59092`
- ZooKeeper: `52181`
- MinIO API: `59000`
- MinIO console: `59001`
- Airflow: `58080`

Create a local env file before starting anything:

```bash
cp .env.example .env
```

Start the stack with:

```bash
docker compose up -d
```

If you already created this compose project's Postgres volume before these changes, recreate it once so the init script can create the separate `airflow` database:

```bash
docker compose down -v
docker compose up -d
```

All local Python services and consumers now read their DB, Kafka, and MinIO settings from `.env`, so they will target this isolated stack by default.

## Netlify frontend + public API

Netlify should deploy the React dashboard from `dashboard/`. The backend should be hosted separately as a public FastAPI service.

### Frontend on Netlify

This repo includes `netlify.toml` so Netlify:

- uses `dashboard/` as the base directory
- runs `npm run build`
- publishes `dashboard/dist`

In the Netlify site settings, add:

- `VITE_API_BASE_URL=https://<your-public-api-domain>`

Example:

```bash
VITE_API_BASE_URL=https://real-time-market-intelligence-api.onrender.com
```

### Backend CORS for Netlify

The FastAPI app now supports:

- `ALLOWED_ORIGINS` for exact origins
- `ALLOWED_ORIGIN_REGEX` for dynamic preview domains

Example backend environment values:

```bash
ALLOWED_ORIGINS=http://localhost:5173,https://<your-netlify-site>.netlify.app
ALLOWED_ORIGIN_REGEX=^https://[a-z0-9-]+--<your-netlify-site>\.netlify\.app$
```

That regex covers Netlify deploy previews and branch deploys such as:

- `https://deploy-preview-12--<your-netlify-site>.netlify.app`
- `https://feature-branch--<your-netlify-site>.netlify.app`

### Public FastAPI deployment

This repo includes `render.yaml` for deploying the FastAPI app to Render.

Start command:

```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

After the backend is live, copy its public URL into the Netlify `VITE_API_BASE_URL` environment variable and redeploy the Netlify site.

## AWS deployment baseline

This repo now includes a first-pass AWS deployment baseline for the current split architecture:

- `amplify.yml` for AWS Amplify Hosting of the React dashboard
- `Procfile` for AWS Elastic Beanstalk running the FastAPI backend
- `Dockerfile` for a future ECS/Fargate or Docker-based AWS deployment path

Recommended managed AWS shape:

- Frontend: Amplify Hosting
- Backend: Elastic Beanstalk
- Database: Amazon RDS for PostgreSQL
- Object storage: Amazon S3

Set `VITE_API_BASE_URL` in Amplify to your backend URL, and set the backend environment variables for `MARKET_DB_*`, `NEWS_API_KEY`, and CORS (`ALLOWED_ORIGINS`, optionally `ALLOWED_ORIGIN_REGEX`).

Detailed AWS notes live in [aws/README.md](/Users/saikrishnabommavaram/Downloads/real-time-market-intelligence-platform/aws/README.md).
