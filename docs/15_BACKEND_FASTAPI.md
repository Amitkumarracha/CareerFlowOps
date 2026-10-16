# Backend API

Reconstructed from the user-provided implementation brief; original file was absent.

Health: /health and /ready; metrics: /metrics. /api/jobs and /api/jobs/{id}; /api/jobs/recommended declared before dynamic route. /api/profile GET/PUT; /api/resumes POST/GET/DELETE; /api/saved GET/POST/DELETE; /api/applications GET/POST/PATCH; /api/tpo; /api/mlops; /api/admin/ingestion/run and status; /api/admin/dedup. Pydantic request/response schemas, bounded pagination, safe exceptions, sessions per request. Token authentication for candidate and admin operations; never accept candidate ID headers as authentication.
