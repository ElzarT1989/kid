FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Shell-форма (без []) — Docker сам оборачивает в /bin/sh -c и разворачивает
# $PORT в рантайме контейнера. Явно задаём PORT=8000 переменной окружения
# сервиса на Railway (см. CLAUDE.md) — если Railway ожидает PORT, он найдёт
# то же значение, что и в domain targetPort и в EXPOSE.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
