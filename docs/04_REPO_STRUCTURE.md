# Repository structure

Reconstructed from the user-provided implementation brief; original file was absent.

apps/api/app contains config, db, models, schemas, routes, services and dependencies; apps/api/tests contains API tests. apps/web holds the strict TypeScript React portal. ingestion holds ATS adapters and normalization. ml contains features, inference, evaluation and registry. pipelines contains six DVC commands. data separates raw, interim, processed and samples. infra contains Docker, AWS, monitoring and scripts. .github/workflows contains CI and image publishing.
