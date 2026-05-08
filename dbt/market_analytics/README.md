# dbt Market Analytics

This dbt project transforms raw streamed stock events from PostgreSQL into analytics models used by the API and dashboard.

## Source and target

- source table: `public.stock_prices`
- primary mart expected by the API: `analytics.daily_stock_summary`

## Models

### `models/staging/stg_stock_prices.sql`

Light staging model over `public.stock_prices`.

### `models/marts/daily_stock_summary.sql`

Daily per-ticker aggregate with:

- `event_count`
- `avg_price`
- `min_price`
- `max_price`
- `total_volume`
- `last_updated_at`

## Required profile

Create `~/.dbt/profiles.yml` with the `market_analytics` profile. The `schema` should be `analytics`, because `api/main.py` queries `analytics.daily_stock_summary` directly.

Example:

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

## Common commands

From this directory:

```bash
dbt debug
dbt run
dbt test
```

## Dependency on ingestion

dbt only becomes useful after `consumers/postgres_consumer.py` has inserted rows into `public.stock_prices`.
