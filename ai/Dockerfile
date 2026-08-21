# Build context is the REPO ROOT — the service reads `shared/` and `data/`.
FROM python:3.12-slim

WORKDIR /app

# FFmpeg is a system binary, not a pip package. Developer 2's video pipeline
# needs it; it is installed here so the container is ready when that lands.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY ai/requirements.txt ./ai/requirements.txt
RUN pip install --no-cache-dir -r ai/requirements.txt

COPY shared ./shared
COPY ai ./ai

WORKDIR /app/ai

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
