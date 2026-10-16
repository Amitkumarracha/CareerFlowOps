# System architecture

Reconstructed from the user-provided implementation brief; original file was absent.

React/Vite/TypeScript calls FastAPI/Pydantic. SQLAlchemy 2 persists PostgreSQL via Alembic migrations. Public ATS adapters produce RawJob DTOs; ingestion persists raw payloads separately and upserts canonical jobs and source occurrences. Shared ranking code supports TF-IDF, SentenceTransformer and hybrid scoring. DVC orchestrates reproducible stages, MLflow tracks experiments and serves a registered production alias. Prometheus scrapes API metrics; Grafana visualizes them. Docker Compose is the local deployment unit.
