FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MLFLOW_DISABLE_AGENT_HINT=1 OMP_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
WORKDIR /app
COPY pyproject.toml requirements-runtime.lock ./
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-runtime.lock
COPY apps ./apps
COPY ingestion ./ingestion
COPY ml ./ml
COPY pipelines ./pipelines
COPY params.yaml sources.yaml ./
RUN useradd --create-home app && mkdir -p data mlflow-data && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
