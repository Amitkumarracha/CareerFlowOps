FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY apps ./apps
COPY ingestion ./ingestion
COPY ml ./ml
COPY pipelines ./pipelines
COPY params.yaml sources.yaml ./
RUN useradd --create-home app && mkdir -p data && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
