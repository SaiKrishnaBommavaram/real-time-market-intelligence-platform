# Dashboard

This directory contains the React + Vite frontend for the market intelligence platform.

## What it shows

- API health from `GET /health`
- warehouse summary rows from `GET /market/summary`
- live ticker data from `GET /stocks/{ticker}/live`
- recent news articles from `GET /stocks/{ticker}/news`
- local or fallback news summaries from `GET /stocks/{ticker}/news/summary`
- watchlists with client-side alert thresholds for price moves and volume spikes
- top movers and anomaly flags derived from warehouse summaries

## Local development

Install dependencies:

```bash
npm ci
```

Start the dev server:

```bash
npm run dev
```

The frontend expects `VITE_API_BASE_URL` to point to the FastAPI backend. For local development, it defaults to `http://localhost:8000` when opened from `localhost` if the env var is not set.

If the backend is configured with `MARKET_API_KEY`, set the matching frontend key:

```bash
VITE_API_KEY=<same value as MARKET_API_KEY>
```

Recommended explicit value:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Build

```bash
npm run build
```

## Deployment

### Netlify

`../netlify.toml` is already configured to:

- use `dashboard/` as the base directory
- run `npm run build`
- publish `dashboard/dist`

Set this environment variable in Netlify:

```bash
VITE_API_BASE_URL=https://<your-public-api-domain>
VITE_API_KEY=<same value as MARKET_API_KEY>
```

### AWS Amplify

`../amplify.yml` builds this app from the repository root and publishes `dashboard/dist`.
