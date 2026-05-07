# AWS deployment baseline

This repository is currently split into two deployable surfaces:

- `api/`: public FastAPI backend
- `dashboard/`: static Vite frontend

## Recommended first AWS layout

Use managed services that fit the current app shape before moving the full local data stack to AWS:

- Frontend: AWS Amplify Hosting
- Backend: AWS Elastic Beanstalk on the Python platform
- Database: Amazon RDS for PostgreSQL
- Object storage: Amazon S3

This repo includes the initial configuration for that layout:

- `amplify.yml` builds and publishes the React app from `dashboard/`
- `Procfile` starts the FastAPI app for Elastic Beanstalk
- `Dockerfile` packages the API for a future ECS/Fargate or Docker-based Beanstalk path

## Backend deployment notes

Elastic Beanstalk should point at the repository root and use the Python 3.11 platform.

The app entrypoint is:

```text
web: gunicorn -k uvicorn.workers.UvicornWorker api.main:app --bind :8000 --timeout 180
```

Set these Elastic Beanstalk environment properties:

```text
ALLOWED_ORIGINS=https://<your-amplify-domain>
ALLOWED_ORIGIN_REGEX=
NEWS_API_KEY=<your-news-api-key>
MARKET_DB_HOST=<your-rds-endpoint>
MARKET_DB_PORT=5432
MARKET_DB_NAME=market_data
MARKET_DB_USER=<your-db-user>
MARKET_DB_PASSWORD=<your-db-password>
```

If you use an RDS database inside a private VPC, the Beanstalk environment must have network access to that VPC and its security group rules must allow PostgreSQL traffic on `5432`.

## Frontend deployment notes

Amplify Hosting should connect to this repository and use the root-level `amplify.yml`.

Set this Amplify environment variable:

```text
VITE_API_BASE_URL=https://<your-elastic-beanstalk-domain>
```

After the first backend deploy, add the Amplify domain to backend CORS:

```text
ALLOWED_ORIGINS=https://main.<app-id>.amplifyapp.com,https://<your-custom-domain>
```

## Container path for ECS later

The included `Dockerfile` is intended for an ECS/Fargate migration if you want tighter control than Elastic Beanstalk.

Build locally:

```bash
docker build -t market-intelligence-api .
docker run --rm -p 8000:8000 --env-file .env market-intelligence-api
```

## Important service note

AWS App Runner announced that it is no longer open to new customers starting on April 30, 2026. Because the current date is May 6, 2026, this repo does not add new App Runner-specific configuration as the default AWS path.
