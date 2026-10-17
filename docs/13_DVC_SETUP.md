# DVC setup

Reconstructed from the user-provided implementation brief; original file was absent.

Initialize DVC in Git. Default remote storage points to ignored ./dvc-storage. Track snapshots, labels and stage dependencies. dvc repro must work offline with committed small fixtures and cached local models; transformer mode requires its documented one-time model download. Never version private resumes or credentials. dvc push/pull uses the configured local remote, with S3 remote optional after authorization.

The current pipeline also exports a selected production model bundle. Use the [complete Git/DVC release guide](remaining/02_GIT_DVC_RELEASE.md) for reproduction, empty-MLflow-backend handling, S3 remote setup, fresh pull validation and release commits.
