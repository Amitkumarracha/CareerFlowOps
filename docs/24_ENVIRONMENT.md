# Environment

Reconstructed from the user-provided implementation brief; original file was absent.

Python 3.12 is the supported runtime; Node 22 LTS, PostgreSQL 16, Docker/Compose. Copy .env.example; replace password consistently in DB URL. Docker service DNS: postgres and mlflow; direct host processes use localhost. Secrets are runtime environment only. Optional SentenceTransformer requires a one-time download and CPU PyTorch. Use system Docker socket if Desktop context is unavailable. No existing remote repository was supplied.
