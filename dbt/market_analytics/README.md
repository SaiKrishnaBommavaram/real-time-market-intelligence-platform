# dbt Market Analytics

This dbt project transforms raw streamed stock events from PostgreSQL into analytics models used by the API and dashboard.

## Source and target

- source table: `public.stock_prices`
- source definition: `models/staging/sources.yml`
- primary mart expected by the API: `analytics.daily_stock_summary`

## Models

### `models/staging/stg_stock_prices.sql`

Staging model over `public.stock_prices` with normalized ticker casing, typed fields, source cleanup, and a dbt `source()` reference.

### `models/marts/daily_stock_summary.sql`

Daily per-ticker aggregate with:

- `event_count`
- `avg_price`
- `min_price`
- `max_price`
- `total_volume`
- `last_updated_at`

## Quality coverage

Source and schema tests now cover:

- null and uniqueness checks on source and staging keys
- null checks on core price, volume, timestamp, and source fields
- uniqueness of `(ticker, trade_date)` in the mart

Singular tests now cover:

- duplicate raw event groups in `stg_stock_prices`
- invalid summary price ordering where `min_price > avg_price` or `avg_price > max_price`

Source freshness for `public.stock_prices`:

- warn after 2 hours
- error after 6 hours

## Required profile

Create `~/.dbt/profiles.yml` with the `market_analytics` profile. The `schema` should be `analytics`, because the API queries `analytics.daily_stock_summary` directly.

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
dbt source freshness
dbt run
dbt test
```

## Dependency on ingestion

dbt only becomes useful after `consumers/postgres_consumer.py` has inserted rows into `public.stock_prices`.

## Materialization and schemas

- staging models materialize as views in schema `staging`
- mart models materialize as tables in schema `analytics`
