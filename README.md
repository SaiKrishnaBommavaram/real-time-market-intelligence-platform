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
