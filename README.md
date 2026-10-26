# Investing Demo

Install the Python dependencies and run the app locally with SQLite:

```sh
python3 -m pip install -r requirements.txt
export DJANGO_DEBUG=true
python3 manage.py migrate
python3 manage.py runserver
```

For PostgreSQL and Redis, start the development services:

```sh
export POSTGRES_PASSWORD=choose-a-local-password
docker compose up -d db redis
export DJANGO_DEBUG=true
export DATABASE_URL="postgresql://postgres:${POSTGRES_PASSWORD}@127.0.0.1:5432/investing"
export CELERY_BROKER_URL=redis://127.0.0.1:6379/0
python3 manage.py migrate
```

Set `TINKOFF_TOKEN` in the environment to enable market data, then load the share catalog:

```sh
export TINKOFF_TOKEN=your-token
python3 manage.py add_shares
python3 manage.py sync_market_history
```

Run periodic price updates with Celery Beat and a worker. Price updates run once
per minute by default; set `PRICE_UPDATE_INTERVAL_SECONDS` to change the
interval. Stale queued updates expire, and a Redis lock prevents overlapping
copies of the same scheduled task.

```sh
celery -A config beat
celery -A config worker -l info
```

The application also provides owner-scoped watchlists and price alerts, virtual
portfolios with average-cost accounting, persisted daily price history, and a
single-share daily-close strategy backtester. Their requirements and calculation
rules are documented in `docs/NEW_FEATURES_REQUIREMENTS.md`. REST endpoints live
under `/api/v1/`; the server-rendered screens are linked from the authenticated
navigation. Run `DJANGO_DEBUG=true python3 manage.py test` to execute the test suite.

Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, and `DJANGO_ALLOWED_HOSTS` before deployment. Django generates a temporary key only in explicit debug mode and refuses to start without a configured key when debug is disabled. With `DJANGO_DEBUG=false`, HTTPS redirects, secure cookies, and one-year HSTS are enabled by default; only use that mode behind HTTPS. The shared login and registration rate limit uses `DJANGO_CACHE_URL` or a Redis `CELERY_BROKER_URL`; configure `DJANGO_CACHE_URL` when the Celery broker is not Redis. By default, throttling keys use the direct peer address; behind a reverse proxy, set `DJANGO_AUTH_RATE_LIMIT_IP_HEADER` to a header the proxy overwrites with the client address. If `DATABASE_URL` is unset, the app uses the local SQLite database.

When HTTPS terminates at a reverse proxy, set `DJANGO_TRUST_X_FORWARDED_PROTO=true` only if that trusted proxy removes any client-supplied `X-Forwarded-Proto` header and writes its own value. The API limits page sizes to 500 rows, applies anonymous and authenticated request throttles, and limits strategy runs to 20 per hour per user. Authentication requests return 503 while their shared rate-limit cache is unavailable, so a cache outage cannot disable the login throttle.
