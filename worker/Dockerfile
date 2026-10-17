# Build vanuit de repo-root:  docker build -f worker/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
COPY worker/pyproject.toml ./
COPY worker/koersradar ./koersradar
RUN pip install --no-cache-dir ".[aex]"
COPY config /config
ENV KOERSRADAR_CONFIG_DIR=/config
CMD ["python", "-m", "koersradar.ingest.scheduler"]
