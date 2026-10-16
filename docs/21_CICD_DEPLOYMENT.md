# CI/CD and deployment

Reconstructed from the user-provided implementation brief; original file was absent.

Pull requests run Python format/lint/tests and frontend type/lint/tests/build with no AWS dependency. Main builds SHA-tagged images after CI. Optional ECR publishing uses GitHub OIDC role and configured region/repository. EC2 deployment uses Docker Compose with environment secrets on host; public TLS/reverse proxy and access control are required before internet exposure. Health-check verification must fail deployment on unhealthy API. No remote deployment without user authorization.
