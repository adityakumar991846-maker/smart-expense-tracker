FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN SECRET_KEY=build-only-static-collection-key DEBUG=True \
    python manage.py collectstatic --noinput

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /var/data/media \
    && chown -R appuser:appuser /app /var/data/media

EXPOSE 10000

CMD ["sh", "-c", "mkdir -p \"${MEDIA_ROOT:-/var/data/media}\" && chown appuser:appuser \"${MEDIA_ROOT:-/var/data/media}\" && exec gosu appuser gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-10000} --workers 2 --timeout 120"]
