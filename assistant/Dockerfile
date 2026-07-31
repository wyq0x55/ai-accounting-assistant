# Multi-stage build: build the Vite frontend, then run Flask via gunicorn.
# Build context is the repository ROOT (see docker-compose.yml).

# ---- Stage 1: frontend ----
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: backend ----
FROM python:3.12-slim AS backend
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ASSISTANT_DATA_DIR=/app/data \
    ASSISTANT_LOG_DIR=/app/logs \
    PORT=5007

COPY assistant/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY assistant/ ./
# Ship the built SPA so Flask can serve it from ./static.
COPY --from=frontend /fe/dist ./static

RUN mkdir -p /app/data /app/logs

EXPOSE 5007
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5007", "--timeout", "60", "wsgi:app"]
