# Production Environment

Production should not rely on `.env` files baked into the image.

Required controls:

- `MARKET_ENV=prod`
- `MARKET_STARTUP_CHECK_MODE=strict`
- non-default `MARKET_DB_PASSWORD` or `MARKET_DB_PASSWORD_FILE`
- `MARKET_API_KEY` or `MARKET_API_KEY_FILE`
- `NEWS_API_KEY` or `NEWS_API_KEY_FILE`
- explicit non-localhost `ALLOWED_ORIGINS` or `ALLOWED_ORIGIN_REGEX`

Production guidance:

- source secrets from the platform secret manager or mounted secret files
- point container health checks at `/ready`
- keep `/health` for liveness-only checks
- avoid wildcard CORS origins, especially when credentials are enabled
- treat startup failures as configuration or dependency issues, not warnings
