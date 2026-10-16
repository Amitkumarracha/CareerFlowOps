# Security and privacy

Reconstructed from the user-provided implementation brief; original file was absent.

Single-candidate local MVP uses environment bearer tokens for candidate/admin access; no self-service account system is implied. Candidate token maps to a server-owned candidate ID. Keep tokens in memory/session storage only and mask entry. Production requires proper per-user identity and role-based authorization before multi-user use. Bind DB/MLflow/Grafana to loopback. Restrict CORS, bound uploads and queries, do not log PII, allow deleting candidate data. Never accept arbitrary ingestion URLs or execute remote content.
