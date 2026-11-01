# STAGE BUILD
FROM python:3.11.16-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential perl-base \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir -r requirements.txt
COPY requirements.txt .

#STAGE RUN
FROM python:3.11.16-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY app.py .

RUN apt-get update && apt-get install -y curl perl-base

RUN useradd -u 8888 flag-service && chown -R flag-service:flag-service /app

USER flag-service

EXPOSE 8002

CMD ["gunicorn", "--bind", "0.0.0.0:8002", "app:app"]