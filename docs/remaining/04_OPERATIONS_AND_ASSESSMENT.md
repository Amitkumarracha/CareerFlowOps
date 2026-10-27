# Verification, operations, recovery and assessment evidence

Use this after the exact release is deployed. These are operator instructions, not claims that AWS checks have already passed. Keep secrets and candidate data out of shared evidence.

## 1. Connect to the correct deployment

EC2 — define a Compose helper for this shell. Persisted image references in `.env` were configured in the deployment guide:

```bash
cd ~/CareerFlowOps
export DOCKER_HOST=unix:///var/run/docker.sock
pc() { docker compose -f docker-compose.yml -f infra/aws/compose.production.yml "$@"; }
pc ps
pc config --quiet
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/ready
```

Recreate the helper after reconnecting. `config --quiet` validates configuration without printing interpolated credentials. Do not put raw `docker compose config`, `.env`, bearer headers or browser session storage into a report.

WORKSTATION — use the private SSH tunnel from the AWS guide, then verify the EC2 API through port 18000:

```bash
curl --fail http://localhost:18000/ready
```

Readiness must contain the bundle ID and model version. The separate local API at port 8000 can still be in development mode; do not confuse these two servers.

## 2. Populate a fresh EC2 database

The Docker image and DVC model do not copy the workstation's live job database. In the EC2 portal, enter EC2 tokens through Workspace access, then use **Source health → Refresh live sources**. For an offline presentation, choose **Load snapshots** and disclose that those are historical real-source snapshots.

Terminal alternative, EC2 — performs real live ingestion using the protected admin API; credentials stay out of command arguments:

```bash
.venv-deploy/bin/python - <<'PY'
import requests
from dotenv import dotenv_values
values = dotenv_values('.env')
response = requests.post(
    'http://127.0.0.1:8000/api/admin/ingestion/run',
    headers={'Authorization': 'Bearer ' + values['ADMIN_API_TOKEN']},
    json={'mode': 'live'}, timeout=180,
)
response.raise_for_status()
run = response.json()
print({'status': run['status'], 'counts': run['counts'], 'errors': run['errors']})
PY
```

An HTTP success can contain a partial/failed source result: inspect `status`, per-source counts and errors. Do not fabricate live counts if a public source is unavailable. Historical mode is `{'mode': 'fixture'}` in the same request.

## 3. Complete the user workflow

Use your actual resume only if appropriate for the deployment. For a presentation, a clearly fictional candidate profile is sufficient; its recommendations still run against real job data.

1. Upload a selectable-text PDF or enter skills/experience in Profile.
2. Review/edit the extracted fields; save and reload to verify persistence.
3. Open For you with Production selected. Verify explanations, actual model version and absence of fallback in bundle mode.
4. View the official source and Apply URL. Opening Apply does not submit an application.
5. Save an opportunity. Verify it remains in Saved jobs after reload.
6. Update its application manually to APPLIED or INTERVIEW, add a note and inspect history.
7. Use the TPO page to check persisted aggregates and its disclosed bounds.
8. Use Model experiments to compare validation/test artifacts and download saved evaluation JSON.
9. Review System & guide for the actual bundle identity and lifecycle.
10. Disconnect workspace access and confirm protected candidate content is no longer displayed.

Do not share the candidate token with other students: it maps to the same server-owned candidate identity.

### Optional terminal-only profile setup for a fresh demo

EC2 — this **writes** a minimal fictional profile only if there is no meaningful existing profile. It aborts rather than replacing an existing person's profile:

```bash
.venv-deploy/bin/python - <<'PY'
import requests
from dotenv import dotenv_values
values = dotenv_values('.env')
headers = {'Authorization': 'Bearer ' + values['CANDIDATE_API_TOKEN']}
url = 'http://127.0.0.1:8000/api/profile'
response = requests.get(url, headers=headers, timeout=30)
response.raise_for_status()
existing = response.json()
if any(existing.get(key) for key in ['name', 'email', 'phone', 'location', 'skills', 'summary', 'education', 'experience', 'projects', 'certifications']) or existing.get('experience_years') is not None:
    raise SystemExit('Existing profile detected. Review it in the UI; no profile was overwritten.')
response = requests.put(url, headers=headers, json={
    'skills': ['python', 'sql', 'docker'],
    'summary': 'Fictional academic demonstration profile: Python backend development',
}, timeout=30)
response.raise_for_status()
print('Saved a fictional demonstration profile. No resume was submitted to an employer.')
PY
```

Verify inference without printing credentials or personal profile fields:

```bash
.venv-deploy/bin/python - <<'PY'
import requests
from dotenv import dotenv_values
values = dotenv_values('.env')
base = 'http://127.0.0.1:8000'
ready = requests.get(base + '/ready', timeout=30)
ready.raise_for_status()
response = requests.get(base + '/api/jobs/recommended?limit=1',
    headers={'Authorization': 'Bearer ' + values['CANDIDATE_API_TOKEN']}, timeout=60)
response.raise_for_status()
rows = response.json()
if not rows:
    raise SystemExit('No jobs returned. Check ingestion and profile before capturing evidence.')
row = rows[0]
assert row['model_version'] == ready.json()['model_version']
assert row['fallback_reason'] is None and row['explanation']
print({'model_version': row['model_version'], 'algorithm': row['algorithm'],
       'bundle_id': ready.json()['bundle_id'], 'explanation_present': True,
       'official_apply_url': row['job']['apply_url']})
PY
```

A 422 from recommendations normally means the profile is absent/insufficient; a 503 in bundle mode requires investigating the model or database. Neither should be disguised with sample predictions.

## 4. Monitoring and restart verification

EC2:

```bash
pc --profile monitoring up -d --no-build prometheus grafana
curl --fail http://127.0.0.1:9090/-/ready
curl --fail 'http://127.0.0.1:9090/api/v1/query?query=up'
curl --fail http://127.0.0.1:3000/api/health
pc logs --tail 100 api
pc logs --tail 100 prometheus
```

Through the tunnel, open Grafana at http://localhost:13000 using `admin` and the EC2-generated Grafana password. Verify the provisioned CareerFlowOps dashboard, request latency, inference/model identity and ingestion counters. CLI-ingestion counters run in another process; API-triggered ingestion is the appropriate source for the API scrape.

Inspect actual restart policies and images without dumping environment variables:

```bash
docker inspect --format '{{.Name}} {{.Config.Image}} {{.HostConfig.RestartPolicy.Name}}' "$(pc ps -q api)" "$(pc ps -q web)" "$(pc ps -q postgres)"
```

During an agreed maintenance/demo window, test API crash recovery. This briefly interrupts API requests. Do **not** use `docker kill` for this test: Docker treats a user-issued kill as a manual stop, so the container stays down (observed on Docker 29.9.2: state `Exited (137)`, restart count 0). Simulate a crash instead by killing the server process inside the container, so the container's main process exits unexpectedly:

```bash
cid="$(pc ps -q api)"
docker exec "$cid" python -c "import glob, os; [os.kill(int(p.split('/')[2]), 9) for p in glob.glob('/proc/[0-9]*/cmdline') if b'/usr/local/bin/uvicorn' in open(p, 'rb').read() and int(p.split('/')[2]) != os.getpid()]"
curl --fail --retry 30 --retry-all-errors --retry-delay 2 http://127.0.0.1:8000/ready
docker inspect --format 'restarts={{.RestartCount}} started={{.State.StartedAt}}' "$cid"
pc ps
```

Expected: `/ready` answers again without any manual start, `restarts` is at least 1 and `started` is newer. If an API container was stopped manually (for example by `docker kill`), bring it back with `pc up -d --no-build --wait api`.

`unless-stopped` restarts an exited container; it does not automatically restart a process that stays alive but unhealthy. A manual `docker compose stop` is intentionally respected. The [Docker restart-policy reference](https://docs.docker.com/engine/containers/start-containers-automatically/) describes these distinctions. A full EC2 reboot test is optional and disruptive; maintain backups, reconnect, recheck IP/DNS and verify readiness afterwards.

## 5. Back up before upgrades

EC2 — maintenance window: pause training/CLI writers and stop API/web/MLflow while taking a coherent project backup. PostgreSQL stays up. The backup contains private data and `.env` credentials; keep permissions restricted.

```bash
umask 077
export BACKUP_NAME="$(date -u +%Y%m%dT%H%M%SZ)"
export BACKUP_DIR="$PWD/ops-private/backups/$BACKUP_NAME"
mkdir -p "$BACKUP_DIR"
pc stop api web mlflow
pc exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$BACKUP_DIR/postgres.dump"
tar -czf "$BACKUP_DIR/data-and-mlflow.tar.gz" data mlflow-data
cp .env "$BACKUP_DIR/runtime.env"
git rev-parse HEAD > "$BACKUP_DIR/git-sha.txt"
cp dvc.lock "$BACKUP_DIR/dvc.lock"
pc up -d --no-build --wait --wait-timeout 240 mlflow api web
curl --fail http://127.0.0.1:8000/ready > "$BACKUP_DIR/readiness.json"
sha256sum "$BACKUP_DIR/postgres.dump" "$BACKUP_DIR/data-and-mlflow.tar.gz" > "$BACKUP_DIR/checksums.sha256"
```

Stop if any backup step fails; ensure services are brought back after fixing the error. Do not copy a live MLflow SQLite file without a consistent backup strategy. The named PostgreSQL volume is not included by the tar; the custom-format database dump is its logical backup. Provisioned Grafana/Prometheus settings remain in Git; metrics history volumes and Caddy certificate volumes require their own backup if you need that historical state.

Verify archive readability:

```bash
pc exec -T postgres pg_restore --list < "$BACKUP_DIR/postgres.dump" > "$BACKUP_DIR/postgres-contents.txt"
tar -tzf "$BACKUP_DIR/data-and-mlflow.tar.gz" > "$BACKUP_DIR/file-list.txt"
sha256sum -c "$BACKUP_DIR/checksums.sha256"
```

See PostgreSQL's [dump](https://www.postgresql.org/docs/16/app-pgdump.html) and [restore](https://www.postgresql.org/docs/16/app-pgrestore.html) references. Archive listing is not a restore test.

### Test recovery in a separate disposable database

EC2 — creates a new restore-check database; does not target the application database:

```bash
export RESTORE_DB="careerflowops_restore_check_$(date -u +%Y%m%d%H%M%S)"
pc exec -T postgres sh -c 'createdb -U "$POSTGRES_USER" "$1"' sh "$RESTORE_DB"
pc exec -T postgres sh -c 'pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$1"' sh "$RESTORE_DB" < "$BACKUP_DIR/postgres.dump"
pc exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -c "SELECT count(*) FROM jobs;"' sh "$RESTORE_DB"
```

Inspect errors and restored counts. Only after the disposable check succeeds, remove that specific test database:

```bash
pc exec -T postgres sh -c 'dropdb -U "$POSTGRES_USER" "$1"' sh "$RESTORE_DB"
```

Keep an off-host backup too. WORKSTATION — set the instance address and the actual backup name printed/recorded on EC2:

```bash
cd /home/amitkumar/Music/CareerFlowOps
umask 077
mkdir -p ops-private/backups
export EC2_HOST='<current-ec2-host>'
export BACKUP_NAME='<backup-directory-name-from-ec2>'
scp -i "$HOME/.ssh/careerflowops-ec2" -r "ubuntu@$EC2_HOST:/home/ubuntu/CareerFlowOps/ops-private/backups/$BACKUP_NAME" ops-private/backups/
```

Do not put this backup in the model DVC remote or Git. A dedicated encrypted backup destination with separate permissions/retention is a future operations improvement. Test recovery into a separate host/database before any real disaster recovery that replaces live candidate data.

## 6. Upgrade and rollback stages

Record the current working release and take the backup above before migrations. The deployment script has no automatic schema rollback and does not provide zero-downtime release switching.

EC2 — for a new already-published release, stop API/web during artifact replacement so an old process cannot read changing semantic-model files from the mounted directory:

```bash
pc stop api web
git fetch origin
export RELEASE_SHA='<new-full-published-git-sha>'
git checkout "$RELEASE_SHA"
export AWS_REGION=ap-south-1
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export MODEL_BUCKET="careerflowops-models-${AWS_ACCOUNT_ID}-${AWS_REGION}"
export DVC_REMOTE_URL="s3://$MODEL_BUCKET/careerflowops"
export API_IMAGE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/careerflowops-api:$RELEASE_SHA"
export WEB_IMAGE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/careerflowops-web:$RELEASE_SHA"
bash infra/aws/deploy.sh
```

After success, persist the image references using the `.env` update block in AWS section 7. Recheck the edge, inference and monitoring. Keep both old/new images and DVC objects until rollback is no longer needed.

**Application/model rollback, only if the current database schema is compatible with the old application:** perform the same maintenance sequence using the previous full SHA. Its Git checkout restores the matching `dvc.lock`, and deployment pulls the older model bundle and image tags. Record the old expected bundle ID and verify it after restart.

**If migrations are incompatible:** do not blindly run Alembic downgrade or start old code against a newer schema. Choose a tested forward fix, or recover the selected backup into a separate replacement database/host and validate it before directing traffic there. Restoring an older database loses changes since that backup; obtain the operator's explicit recovery decision. A fully automated migration-aware rollback is not implemented.

## 7. Troubleshooting

| Symptom | Check and resolution |
| --- | --- |
| Git push asks for Username or fails | `gh auth status`, `gh auth setup-git`, check repository write access; do not put tokens in URLs |
| No Actions run | Confirm `main` push, Actions enabled and workflow present on GitHub; inspect `gh run list`. On a fresh fork, if pushes create no run while manual dispatch works, set the Actions permission explicitly (see [AWS deployment record](03_AWS_DEPLOYMENT.md#11-deployment-record-arjun-reddy-i-fork-27-october-2026), item 7) |
| `Could not assume role with OIDC` | The token subject must match the role trust. Check `gh api repos/<owner>/<repo>/actions/oidc/customization/sub`; new repositories can use the immutable `owner@id/repo@id` format |
| API container restarts, log says `Production CORS origins must be HTTPS` | Production rejects plain HTTP origins. Use an HTTPS origin in `CORS_ORIGINS`, `PUBLIC_DOMAIN` and the `VITE_API_BASE_URL` variable, then publish a new commit |
| Green build but no ECR images | Check OIDC role secret, role trust, repository variables and whether publish steps were skipped |
| ECR tag already exists | Immutable tags are working; review configuration and publish a new commit SHA |
| AWS AccessDenied | `aws sts get-caller-identity`; identify provisioning/training/publish/EC2 role; grant only its needed actions |
| DVC missing objects | Confirm bucket/prefix/region, run workstation `dvc push -r production`, verify the selected Git/DVC pointer |
| S3 plugin missing | Install `requirements-deploy.lock` into `.venv-deploy`; use that DVC executable |
| `make reproduce` cannot find MLflow run | Existing cached run IDs target a different/empty tracking backend; rerun training pipeline deliberately on the training workstation |
| Model checksum/compatibility failure | Deploy the matching model/image/code revision; do not delete manifest entries or enable fallback to hide it |
| `/ready` has null model fields on EC2 | Include `infra/aws/compose.production.yml`; inspect the configured model mode and recreate API |
| Browser calls localhost on a public domain | Frontend was built with the wrong GitHub API-origin variable; publish a new image SHA |
| Browser CORS error | CORS must equal the frontend browser origin, including tunnel port or HTTPS scheme; restart API after editing |
| Protected pages show 401 | Use EC2 tokens in the EC2 portal tab; saving a token is not successful authentication by itself |
| Recommendations 422 | Add meaningful profile skills/summary; verify selected algorithm is allowed in bundle mode |
| Empty jobs on new EC2 | DVC models do not seed the live SQL job database; run actual ingestion or disclosed snapshots |
| EC2 MLflow UI empty | Workstation run history is not automatically replicated; bundle inference still uses the evaluated release |
| API/MLflow permission denied | Inspect UID 1000 access to project bind mounts; fix only the relevant directories |
| Docker Desktop socket fails locally | Export `DOCKER_HOST=unix:///var/run/docker.sock` for the running system daemon |
| DNS/TLS failure | Correct A/AAAA records, current instance IP, edge security-group ports and Caddy logs |
| Host is out of memory/disk | Inspect `free -h`, `df -h`, `docker stats --no-stream`; resize or remove only reviewed expendable data |

Useful EC2 diagnostics:

```bash
df -h
free -h
docker stats --no-stream
pc logs --tail 100 api mlflow postgres web
```

Avoid global `docker system prune --volumes`, removing database volumes, deleting model caches or sharing raw secret-bearing configuration as a generic fix.

## 8. Assessment checklist: match the supplied diagrams

| Diagram requirement | Actual implementation | Evidence to collect |
| --- | --- | --- |
| Raw data versioned remotely | Public source snapshots, DVC cache and S3 remote | `dvc.lock`, S3 objects and fresh model/data pull as appropriate |
| Preprocessing stage | DVC preprocessing/normalization | Pipeline graph and command/stage output |
| Multiple tracked experiments | Actual MLflow runs for three rankers | Training server's run comparison with dataset/git metadata |
| Best model selected from metrics | Validation selection and deterministic tie-break | Saved evaluation and disclosed benchmark limitations |
| Registry/model remote | MLflow alias plus DVC deployment bundle | Saved registry identity, model export manifest and remote pull |
| CI/CD builds image | GitHub CI then Docker build | Successful hosted run for the deployed SHA |
| Container registry stores image | ECR API and web repositories | SHA-tagged image digests for both repositories |
| EC2 pulls image and model | Operator deployment script | EC2 deploy log, Git SHA and DVC pull/validation result |
| API serves predictions | FastAPI explanation contract and bundle identity | `/ready` and a real recommendation without fallback |
| Restart policy keeps service available | `unless-stopped` Compose policies | Inspect output and controlled exited-process recovery check |
| Client request and prediction | React For you view and API | Candidate workflow demonstration with fictional or consented data |
| Monitoring | Prometheus and Grafana | Healthy target, real request/model metrics and provisioned dashboard |

Use a clearly labeled demo candidate. Redact bearer tokens, `.env`, keys and unrelated private data. Do not edit scores or counts to improve screenshots. Validation ties selected TF-IDF on a tiny illustrative benchmark; do not claim a human-validated high-accuracy model or fully automatic application submission.

## 9. Finish the session and control resource usage

Close the workstation SSH tunnel with Ctrl-C. To stop the EC2 demo containers while preserving volumes:

```bash
pc --profile monitoring stop
```

If public Caddy was started, stop that service separately using the edge file (the saved domain must still be in `.env`):

```bash
docker compose -f docker-compose.yml -f infra/aws/compose.production.yml -f infra/aws/compose.edge.yml stop edge
```

Stopping containers does not stop EC2 compute. WORKSTATION — only when the instance can be taken offline:

```bash
export AWS_REGION=ap-south-1
export INSTANCE_ID='<careerflowops-instance-id>'
aws ec2 stop-instances --instance-ids "$INSTANCE_ID"
aws ec2 wait instance-stopped --instance-ids "$INSTANCE_ID"
```

To resume later:

```bash
aws ec2 start-instances --instance-ids "$INSTANCE_ID"
aws ec2 wait instance-status-ok --instance-ids "$INSTANCE_ID"
aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
```

Reconnect, update DNS/tunnel target if the IP changed, recreate `pc`, and start the services you intentionally stopped. EBS/S3/ECR and some networking allocations can remain billable while compute is stopped; inspect your account. See the [EC2 stop reference](https://docs.aws.amazon.com/cli/latest/reference/ec2/stop-instances.html). Final resource deletion is a separate, destructive decision after off-host backup and retention review; this guide does not include an automatic delete-all command.
