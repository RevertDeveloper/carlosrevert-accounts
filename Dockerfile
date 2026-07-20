FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN addgroup --system django && adduser --system --ingroup django django

COPY requirements/production.txt requirements/base.txt ./requirements/
RUN pip install --upgrade pip && pip install -r requirements/production.txt

COPY --chown=django:django . .
RUN python manage.py collectstatic --noinput

USER django
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=3)"
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
