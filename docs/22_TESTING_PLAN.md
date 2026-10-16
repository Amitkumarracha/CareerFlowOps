# Testing plan

Reconstructed from the user-provided implementation brief; original file was absent.

Unit tests cover all adapters with frozen responses, invalid data, dedup and re-ingestion, source provenance, raw payload history, resume evidence/invalid uploads, match components/metrics, application history, ownership/auth and validation errors. Integration tests run migrations against PostgreSQL and exercise real API/frontend servers. Frontend tests verify loading/error/empty states and key interactions. CI builds both Docker images. Do not claim unavailable checks passed.
