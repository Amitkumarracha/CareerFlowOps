#!/usr/bin/env bash
# Run on the authorized EC2 host from a checkout matching the image SHA.
set -euo pipefail
: "${API_IMAGE:?Export the immutable ECR API image URI with Git SHA tag}"
: "${WEB_IMAGE:?Export the immutable ECR web image URI with Git SHA tag}"
: "${AWS_REGION:?Set AWS_REGION}"
[[ -f .env ]] || { echo 'Create a protected .env on the EC2 host first.' >&2; exit 1; }
command -v aws >/dev/null
command -v docker >/dev/null
command -v curl >/dev/null
registry="${API_IMAGE%%/*}"
[[ "$registry" == *.dkr.ecr.*.amazonaws.com ]] || { echo 'API_IMAGE must reference your ECR registry.' >&2; exit 1; }
[[ "${WEB_IMAGE%%/*}" == "$registry" ]] || { echo 'Both images must use the same ECR registry.' >&2; exit 1; }
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$registry"
python3 infra/scripts/configure.py
export API_IMAGE WEB_IMAGE
docker compose pull api web mlflow
docker compose up --no-build --wait --wait-timeout 240 postgres mlflow api web
curl --fail --silent --show-error --retry 10 --retry-delay 3 --retry-connrefused "${API_HEALTH_URL:-http://127.0.0.1:8000/ready}"
echo 'Deployment passed API readiness verification.'
