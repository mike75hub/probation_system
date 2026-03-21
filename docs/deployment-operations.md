# Deployment & Operations

## Environments
- **Local/dev:** SQLite + Django dev server.
- **Production:** PostgreSQL recommended + WhiteNoise static files + proper secret management.

## Environment variables (examples)
- `DEBUG` (true/false)
- `SECRET_KEY`
- `ALLOWED_HOSTS` (comma-separated)
- `CSRF_TRUSTED_ORIGINS` (comma-separated)
- `TIME_ZONE`

## Local runbook
```bash
./venv/bin/python manage.py migrate
./venv/bin/python manage.py createsuperuser
./venv/bin/python manage.py runserver
```

## Production notes
- Set `DEBUG=False`.
- Run `collectstatic` and serve static files via WhiteNoise.
- Configure a real database (PostgreSQL) and backups.
- Use a process manager (e.g., Gunicorn) behind a reverse proxy (e.g., Nginx).

## Operational KPIs (suggested)
- Active cases per officer (caseload distribution).
- Missed check-ins per week.
- Program enrollment vs completion rate.
- High-risk offenders with overdue check-ins.

