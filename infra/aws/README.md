# AWS deployment guide

The complete operator runbook is now maintained in one place:

- [Remaining stages and execution order](../../docs/remaining/README.md)
- [Current progress and limitations](../../docs/remaining/01_OVERALL_PROGRESS.md)
- [Git, DVC/S3 and image release commands](../../docs/remaining/02_GIT_DVC_RELEASE.md)
- [AWS S3/ECR/IAM/OIDC/EC2 setup and deployment](../../docs/remaining/03_AWS_DEPLOYMENT.md)
- [Verification, monitoring, backup, recovery and assessment](../../docs/remaining/04_OPERATIONS_AND_ASSESSMENT.md)
- [Feature improvement roadmap](../../docs/remaining/05_FEATURE_IMPROVEMENTS.md)

Start with the execution-order index. The AWS guide includes both a private SSH-tunnel demo and optional public HTTPS, full workstation/EC2 commands, instance-role access and exact image/model revision checks. It replaces the shorter preparation-only instructions previously in this file.

The files in this directory implement IAM document rendering, deployment validation and the production/TLS Compose overlays. Preparing these files or documentation does not create resources or prove a successful hosted deployment. AWS resources and publishing are for the operator to configure and execute locally, as requested.
