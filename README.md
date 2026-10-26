# Investing Demo

Install the Python dependencies and run the app locally with SQLite:

```sh
python3 -m pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

For PostgreSQL and Redis, start the development services:

```sh
docker compose up -d db redis
export DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/investing
export CELERY_BROKER_URL=redis://127.0.0.1:6379/0
python3 manage.py migrate
```

Set `TINKOFF_TOKEN` in the environment to enable market data, then load the share catalog:

```sh
export TINKOFF_TOKEN=your-token
python3 manage.py add_shares
python3 manage.py sync_market_history
```

Run periodic price updates with Celery Beat and a worker:

```sh
celery -A config beat
celery -A config worker -l info
```

The application also provides owner-scoped watchlists and price alerts, virtual
portfolios with average-cost accounting, persisted daily price history, and a
single-share daily-close strategy backtester. Their requirements and calculation
rules are documented in `docs/NEW_FEATURES_REQUIREMENTS.md`. REST endpoints live
under `/api/v1/`; the server-rendered screens are linked from the authenticated
navigation. Run `python3 manage.py test` to execute the test suite.

Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, and `DJANGO_ALLOWED_HOSTS` before deployment. With `DJANGO_DEBUG=false`, HTTPS redirects, secure cookies, and one-year HSTS are enabled by default; only use that mode behind HTTPS. If `DATABASE_URL` is unset, the app uses the local SQLite database.
