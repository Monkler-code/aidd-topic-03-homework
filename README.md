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
```

Run periodic price updates with Celery Beat and a worker:

```sh
celery -A config beat
celery -A config worker -l info
```

Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, and `DJANGO_ALLOWED_HOSTS` before deployment. With `DJANGO_DEBUG=false`, HTTPS redirects, secure cookies, and one-year HSTS are enabled by default; only use that mode behind HTTPS. If `DATABASE_URL` is unset, the app uses the local SQLite database.
