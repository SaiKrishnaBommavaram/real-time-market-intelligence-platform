# Dev Environment

Use environment variables from your deployment platform or secret manager instead of checking secrets into `.env`.

Recommended values:

- `MARKET_ENV=dev`
- `MARKET_STARTUP_CHECK_MODE=strict`
- explicit `ALLOWED_ORIGINS` for the shared frontend domain
- `MARKET_API_KEY` or `MARKET_API_KEY_FILE`
- `NEWS_API_KEY` or `NEWS_API_KEY_FILE`
- `MARKET_DB_PASSWORD` or `MARKET_DB_PASSWORD_FILE`

Dev expectations:

- startup should fail if PostgreSQL is unreachable or `public.stock_search_cache` is missing
- CORS should only allow known dev frontend origins
- `/ready` should be used by deployment health checks before routing traffic
- `.env` should be reserved for local developer machines, not shared environments
