# Production handover and current blockers

Verified locally on **26 October 2026**. This is an execution record and operator guide written before the AWS deployment; the deployment was completed and verified on 27 October 2026 (see [AWS deployment record](03_AWS_DEPLOYMENT.md#11-deployment-record-arjun-reddy-i-fork-27-october-2026)). The current application supports a private single-candidate demonstration. A shared student/TPO service still needs real accounts, scoped roles and institution/cohort isolation.

## What was completed

- `infra/scripts/operations.py` provides verified-model readiness, protected live ingestion, private maintenance backups, checksum verification and a database restore drill. It uses the existing deployment environment, without adding dependencies.
- One host lock prevents overlapping ingestion/backup/restore commands. PostgreSQL's existing advisory lock also prevents concurrent API ingestion runs.
- Backups pause web/API/MLflow, dump PostgreSQL, archive source/private data and MLflow consistently, copy the runtime environment and record Git/DVC/model identity. A failed backup attempts to restart every service it paused. A completion manifest is written only after successful backup and verified model readiness.
- Graceful termination enters cleanup; a host crash, forced kill or failed Docker restart can still leave services stopped and needs operator recovery.
- Restore drills validate the inventory/checksums, restore into a generated disposable database, compare counts and remove only that generated database. They never replace the application database. The file archive is checked for readability; a whole-host file recovery is not claimed.
- Optional user-level systemd units refresh approved public ATS boards every six hours and run a daily maintenance backup. Units are supplied but **not enabled on this workstation**.
- Production startup rejects SQLite, missing model-bundle configuration, weak/shared candidate/admin tokens, unknown environment names and non-HTTPS/non-loopback CORS origins. This protects configuration; it does not turn shared tokens into real user accounts.
- API responses under `/api/` use `Cache-Control: no-store`; reverse proxies deny framing and set basic response security headers.
- Prometheus loads four tested alert rules: unreachable API, repeated readiness failures, sustained server errors and failed/partial ingestion. CI validates configuration and tests both firing and healthy cases. **No email/chat notification receiver is configured.**

## Actual local evidence

- Backup: `ops-private/backups/20261026T083615Z-b887c4e9`.
- Database restore: passed; 1,144 jobs and one existing candidate restored; zero resumes/applications/saved jobs in this snapshot. The temporary database was removed. Existing live data was retained.
- Live ingestion run `fc598a3c-ea80-4a37-bed7-150fc79d41f6`: succeeded; 1,064 fetched/normalized, comprising 721 Greenhouse, 309 Lever and 34 Ashby postings. Existing historical jobs may remain; successful ingestion does not prove that all old postings are still open.
- The current jobs API contains 1,148 canonical records after that refresh. The backup was taken before the refresh, which explains its smaller 1,144-record snapshot.
- Restored bundle identity: `ded4d86e980bff8216b4629df8d2c8106888d9fab4bd78c69c6c9f52058d73e2`; selected algorithm TF-IDF, MLflow version 4.
- Verification: 85 backend tests and 13 frontend tests passed, as did Python/frontend lint/format/type checks, the production frontend build, Prometheus config/rule tests and systemd unit validation with the checkout path substituted.
- Fresh local API/web Docker builds were started successfully. Readiness returned the expected bundle, private/unauthorized API responses had `no-store`, web responses denied framing, and all four Prometheus rules were loaded by the running monitoring service.
- The benchmark remains six fictional queries with agent-authored illustrative labels. Human validation and representative evaluation remain required for real ranking-quality claims.

Backup files contain credentials and candidate data. They remain ignored by Git and the Docker build context. Keep them private and copy them to an encrypted off-host destination with separate permissions. There is no automatic deletion/retention policy yet.

## Workstation commands

Run from the existing project directory:

```bash
cd /home/amitkumar/Music/CareerFlowOps
export DOCKER_HOST=unix:///var/run/docker.sock
export PATH="$PWD/.venv-tools/bin:$PATH"
make production-check
make status
make present
```

These are separate operations; run them sequentially because they share a lock:

```bash
make live-ingest
# Brief maintenance downtime while web/API/MLflow are paused:
make backup
# Replace this path with the completed backup printed above:
make restore-check BACKUP=ops-private/backups/20261026T083615Z-b887c4e9
```

Verification commands used for these changes:

```bash
make test
make lint
npm --prefix apps/web run build
docker run --rm --entrypoint /bin/promtool -v "$PWD/infra/monitoring:/etc/prometheus:ro" prom/prometheus:v3.5.0 check config /etc/prometheus/prometheus.yml
docker run --rm --workdir /etc/prometheus --entrypoint /bin/promtool -v "$PWD/infra/monitoring:/etc/prometheus:ro" prom/prometheus:v3.5.0 test rules alerts.test.yml
git diff --check
```

No model code or runtime dependencies changed. The existing validated DVC bundle can be reused; retraining is not necessary for this operations release.

## Optional EC2 schedules

First complete the existing [AWS deployment guide](03_AWS_DEPLOYMENT.md), including the deployment environment, loopback services and `.env`. These units assume the deployment user owns `~/CareerFlowOps`, has Docker access and has `.venv-deploy` installed with `make cloud-setup`. Adapt the two unit paths before installing if the checkout lives elsewhere. Do not install these rootless units as system-wide root services.

EC2, as the deployment user:

```bash
cd ~/CareerFlowOps
export DOCKER_HOST=unix:///var/run/docker.sock
.venv-deploy/bin/python -m infra.scripts.operations check
mkdir -p ~/.config/systemd/user
cp infra/systemd/careerflowops-* ~/.config/systemd/user/
systemd-analyze --user verify ~/.config/systemd/user/careerflowops-*.service ~/.config/systemd/user/careerflowops-*.timer
systemctl --user daemon-reload
sudo loginctl enable-linger "$USER"
systemctl --user enable --now careerflowops-ingest.timer
systemctl --user list-timers 'careerflowops-*'
```

Run a first scheduled-ingestion smoke test and inspect its actual result:

```bash
systemctl --user start careerflowops-ingest.service
journalctl --user -u careerflowops-ingest.service -n 50 --no-pager
```

Only enable daily backups after accepting the **03:30 UTC / 09:00 IST** maintenance window, allowing for up to five minutes of timer jitter. Adjust `OnCalendar` before installation if this is unsuitable. Backups do not catch up automatically after a missed window; ingestion does. Do not leave training/CLI database writers running during backups.

```bash
systemctl --user enable --now careerflowops-backup.timer
systemctl --user list-timers 'careerflowops-*'
journalctl --user -u careerflowops-backup.service -n 50 --no-pager
```

Pause schedules before deployments or other maintenance; wait for any currently active oneshot service to finish before proceeding. `systemctl stop` on the timer alone does not cancel an already running service. Do not terminate a backup during its restart/recovery section.

```bash
systemctl --user stop careerflowops-ingest.timer careerflowops-backup.timer
systemctl --user is-active careerflowops-ingest.service careerflowops-backup.service
# After completing maintenance, restart only the schedules you enabled:
systemctl --user start careerflowops-ingest.timer careerflowops-backup.timer
```

The CLI fails partial ingestion so the service journal records failure even when the API returned HTTP 200. It does not retry aggressively, remove jobs on source outages or claim to implement verified job closure. Failed scheduled tasks and disk capacity need an operator notification destination and retention policy before unattended operation.

## Load and inspect monitoring rules

On the deployment host, after pulling/building the matching release:

```bash
docker compose -f docker-compose.yml -f infra/aws/compose.production.yml --profile monitoring up -d --no-build prometheus grafana
curl --fail http://127.0.0.1:9090/api/v1/rules
curl --fail http://127.0.0.1:9090/api/v1/alerts
```

View rules through a private tunnel in Prometheus at `/rules`. Alert rules are not delivered notifications. Select an operator channel, then configure a receiver and send a real test notification. Readiness failure alerts depend on the container's periodic `/ready` requests; an unreachable API is covered separately by the scrape alert. There is no node/disk exporter or external uptime monitor yet.

## What is needed to finish live deployment

| Input | Current state | Required action |
| --- | --- | --- |
| GitHub access | Account authenticated; repository synchronization works | Existing access can be reused |
| AWS CLI/profile | CLI 2.38.5 installed with signature verification; `Amit_devil` profile has region/output configured | Complete AWS login locally, then verify STS identity |
| AWS region | Repository default `ap-south-1` | Confirm this region |
| Spending limit | Not provided | Set a monthly budget before provisioning EC2/storage |
| Deployment audience | Not selected | Choose private assessment demo or real shared service |
| Domain/DNS | Not provided | Supply a domain and DNS access for public HTTPS, or use the documented private tunnel |
| Existing resources | None verified | Supply resource IDs if already created; otherwise provision after account/budget selection |
| Identity provider | Not selected | Required for real student accounts and scoped TPO/admin roles |
| Backup destination | Local backup verified | Configure encrypted off-host storage, separate permissions and retention |
| Notifications | Local rule evaluation tested | Choose a destination and validate actual delivery |

Send only non-secret details in chat:

```text
Audience: private demo / shared students and TPO
Expected users:
AWS profile name:
Region:
Monthly budget:
Domain or "no domain":
Existing AWS resource IDs or "none":
Identity provider, if any:
Operator notification destination:
```

Do not paste access keys, passwords, SSH private keys or raw login tokens. Configure credentials on the workstation. For an existing IAM Identity Center account, [AWS documents the local SSO flow](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html):

```bash
export PATH="$HOME/.local/bin:$PATH"
export AWS_PROFILE=Amit_devil
export AWS_REGION=ap-south-1
aws configure sso --profile "$AWS_PROFILE"
aws sso login --profile "$AWS_PROFILE"
aws sts get-caller-identity --profile "$AWS_PROFILE"
```

Use your existing authorized profile instead if the account does not use IAM Identity Center. Once access and scope exist: create/reuse S3/ECR/IAM, push the DVC model, publish both SHA images, deploy to EC2, configure tunnel/HTTPS, run application/restore/notification checks, then enable the optional automatic deployment. Follow [the ordered remaining stages](README.md) and [automatic deployment](../AUTOMATIC_DEPLOYMENT.md).

For a normal IAM/federated AWS console account, `aws login --profile Amit_devil` provides a browser sign-in alternative to SSO. Its permissions and the remaining account setup are described in [AWS access](03_AWS_DEPLOYMENT.md#2-workstation-aws-access). Only local CLI installation/profile defaults were completed; AWS authentication is still pending.

The shared-user service is **not complete** while all candidates still map to `local-candidate`. Do not share the demonstration token among students. No S3 upload, ECR publication or EC2 deployment has been executed in this handover.

## References

- [PostgreSQL 16 dump documentation](https://www.postgresql.org/docs/16/app-pgdump.html) and [restore documentation](https://www.postgresql.org/docs/16/app-pgrestore.html).
- [systemd timer semantics](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html).
- [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) and [rule validation](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/).
