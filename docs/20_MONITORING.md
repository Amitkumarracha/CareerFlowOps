# Monitoring

Reconstructed from the user-provided implementation brief; original file was absent.

Prometheus: HTTP count/duration/errors with bounded route labels, ingestion runs/failures/fetched/normalized/duplicates, recommendation count/latency/score distribution and active model identity. Structured JSON logs contain route/status/latency, never credentials or resume text. Provision a Grafana data source and dashboard; use environment-provided admin password.

Prometheus now loads tested rules for API scrape loss, repeated readiness failures, sustained server errors and failed/partial ingestion. CI checks configuration and healthy/firing behavior with `promtool`. Receiver delivery and host/disk monitoring remain unconfigured; rules alone do not notify anyone. See [production handover](remaining/06_PRODUCTION_HANDOVER.md).
