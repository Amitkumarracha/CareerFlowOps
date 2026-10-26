# AWS deployment: S3, ECR, IAM, EC2 and HTTPS

Update on 26 October 2026: production configuration now fails closed for missing model bundles, SQLite, weak/shared access tokens and unsafe CORS. Read [production handover](06_PRODUCTION_HANDOVER.md) for tested backup/restore commands, optional ingestion/backup schedules and the account details still needed. Shared student accounts are not implemented by these configuration checks.

Reviewed against official references on **17 October 2026**. These commands are prepared for you to run. No AWS resources were created by this documentation task. Use a standard commercial AWS account and `ap-south-1` unless you deliberately adapt all region-specific inputs.

## 1. Choose the demonstration mode

| Mode | GitHub `VITE_API_BASE_URL` | EC2 `.env` CORS origin | Browser URL | Public inbound ports |
| --- | --- | --- | --- | --- |
| Private SSH demo | `http://localhost:18000` | `http://localhost:15173` | `http://localhost:15173` while tunnel is open | SSH 22 from your IP only |
| Public HTTPS | `https://<your-domain>` | `https://<your-domain>` | Your HTTPS domain | 80/443 plus restricted SSH |

The private mode uses different local ports so your running local development stack can stay online. It still serves requests on EC2 and pulls images/models from AWS. A domain is optional for that demonstration. Changing the browser API URL requires a new frontend image; editing only the server `.env` does not change compiled JavaScript.

Keep PostgreSQL, API, web, MLflow, Prometheus and Grafana loopback bindings as configured. Do not open 5432/8000/5173/5000/9090/3000 to the internet. Public access uses Caddy on 80/443.

EC2, disks, public IPv4, image storage and S3 may incur charges. Check your account's current regional prices, budget and quotas in the AWS console before creation. No free-tier eligibility or fixed cost is assumed here. The resource size below is an initial full-stack capacity choice, not a measured minimum or cost quotation.

## 2. Workstation AWS access

Workstation update, 26 October 2026: AWS CLI **2.38.5** was installed for the current user at `~/.local/bin/aws`, with package PGP signature and AWS signing-key fingerprint verified. The user-selected local profile `Amit_devil` now has region `ap-south-1` and JSON output configured, but has **not authenticated**. Installation and local profile configuration created no AWS resources. Add `~/.local/bin` to this terminal's PATH before continuing.

If you sign in through the normal AWS console with an IAM/federated identity, use the [official browser-based local login](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html):

```bash
export PATH="$HOME/.local/bin:$PATH"
export AWS_PROFILE=Amit_devil
aws login --profile "$AWS_PROFILE"
aws sts get-caller-identity --profile "$AWS_PROFILE"
```

Complete the browser sign-in yourself. The IAM identity needs AWS's `SignInLocalDevelopmentAccess` permission for this flow; it does not grant deployment permissions. For an IAM Identity Center account, use the SSO flow below instead. Do not paste authorization codes or credentials into chat. The installation block below remains for a new workstation; skip it on this one.

WORKSTATION — AWS CLI v2 is required. If absent on your x86-64 Arch workstation, use the official installer in a temporary directory:

```bash
cd /home/amitkumar/Music/CareerFlowOps
sudo pacman -S --needed curl unzip
export AWS_CLI_TMP="$(mktemp -d -t careerflowops-awscli-XXXXXX)"
curl --fail --location https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip --output "$AWS_CLI_TMP/awscliv2.zip"
unzip -q "$AWS_CLI_TMP/awscliv2.zip" -d "$AWS_CLI_TMP"
sudo "$AWS_CLI_TMP/aws/install"
aws --version
```

If already installed, inspect its version instead of reinstalling; an update uses the installer's `--update` option. Publisher verification and platform alternatives are in the [official CLI installation guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).

Prefer an existing SSO profile. If your organization/account uses IAM Identity Center:

```bash
export AWS_PROFILE=Amit_devil
aws configure sso --profile "$AWS_PROFILE"
aws sso login --profile "$AWS_PROFILE"
export AWS_REGION=ap-south-1
export AWS_DEFAULT_REGION="$AWS_REGION"
aws sts get-caller-identity
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export MODEL_BUCKET="careerflowops-models-${AWS_ACCOUNT_ID}-${AWS_REGION}"
export DVC_REMOTE_URL="s3://$MODEL_BUCKET/careerflowops"
python3 infra/aws/policies.py --account "$AWS_ACCOUNT_ID" --region "$AWS_REGION" --bucket "$MODEL_BUCKET"
```

If you already use another authorized local profile, select it with `AWS_PROFILE` instead. SSO cannot be configured without the account's SSO details. If you must use account-provided access keys, configure them locally with AWS CLI; never put values into these files or chat. The provisioning identity needs the necessary S3/ECR/IAM/EC2 permissions, including permission to pass the EC2 role. Have the account administrator grant the required scope if denied.

The generated `.aws-policies/` directory is ignored by Git. It contains account-specific policy documents, not credentials. Inspect them before applying them.

## 3. Create storage and image repositories

WORKSTATION — inspect existing resources first:

```bash
aws s3api head-bucket --bucket "$MODEL_BUCKET"
aws ecr describe-repositories --repository-names careerflowops-api careerflowops-web
```

On a first setup, expected not-found errors mean you need the matching create command. A permission error is not proof that a resource is absent. Create only missing resources:

```bash
aws s3api create-bucket --bucket "$MODEL_BUCKET" --region "$AWS_REGION" --create-bucket-configuration "LocationConstraint=$AWS_REGION"
aws s3api put-public-access-block --bucket "$MODEL_BUCKET" --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket "$MODEL_BUCKET" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$MODEL_BUCKET" --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws ecr create-repository --repository-name careerflowops-api --image-tag-mutability IMMUTABLE --image-scanning-configuration scanOnPush=true
aws ecr create-repository --repository-name careerflowops-web --image-tag-mutability IMMUTABLE --image-scanning-configuration scanOnPush=true
```

For `us-east-1`, omit the bucket `--create-bucket-configuration` argument. Existing repositories should be checked for immutable tags and scanning settings. Keep prior release images/model versions needed for rollback; avoid unconditional age-based deletion of active releases.

Storage encryption and permissions must match: these commands use S3-managed encryption. A custom KMS key would also require appropriate KMS permissions, which the current policy templates do not grant.

## 4. Configure GitHub OIDC and EC2 roles

WORKSTATION — inspect the account first:

```bash
aws iam list-open-id-connect-providers
aws iam get-role --role-name CareerFlowOpsGitHubPublish
aws iam get-role --role-name CareerFlowOpsEC2
aws iam get-instance-profile --instance-profile-name CareerFlowOpsEC2
```

If the GitHub provider is absent, create it once:

```bash
aws iam create-open-id-connect-provider --url https://token.actions.githubusercontent.com --client-id-list sts.amazonaws.com
```

Reuse an existing compatible provider instead of creating a duplicate. The AWS API supports discovering the provider certificate thumbprint when omitted; see the [provider command reference](https://docs.aws.amazon.com/cli/latest/reference/iam/create-open-id-connect-provider.html).

Create only missing roles/profiles, then apply the rendered policies:

```bash
aws iam create-role --role-name CareerFlowOpsGitHubPublish --assume-role-policy-document file://.aws-policies/github-trust.json
aws iam put-role-policy --role-name CareerFlowOpsGitHubPublish --policy-name CareerFlowOpsECR --policy-document file://.aws-policies/github-ecr.json
aws iam create-role --role-name CareerFlowOpsEC2 --assume-role-policy-document file://.aws-policies/ec2-trust.json
aws iam put-role-policy --role-name CareerFlowOpsEC2 --policy-name CareerFlowOpsPull --policy-document file://.aws-policies/ec2-pull.json
aws iam create-instance-profile --instance-profile-name CareerFlowOpsEC2
aws iam add-role-to-instance-profile --instance-profile-name CareerFlowOpsEC2 --role-name CareerFlowOpsEC2
```

If a role exists, review its trust document before reusing it; do not overwrite another project's role. IAM changes can take time to propagate. Retry inspection after propagation, not by creating a second role.

| Identity | Permission scope |
| --- | --- |
| Workstation/training identity | Needs S3 read/write for `careerflowops/*`; rendered `trainer-storage.json` describes the required storage scope |
| `CareerFlowOpsGitHubPublish` | Two ECR repositories; OIDC trust restricted to this repository's `main` branch |
| `CareerFlowOpsEC2` | Pull images from those repositories, list the project S3 prefix and get its objects; cannot publish |

Do not attach broad administrator access to EC2. The current EC2 policy does not enable Systems Manager sessions; add the appropriate SSM setup separately if you choose that access method.

**Return now to [Git/DVC sections 4–7](02_GIT_DVC_RELEASE.md#4-configure-production-dvc-storage): upload and validate the model, configure GitHub variables for the chosen mode, push the release, and verify both ECR tags. Then continue below.**

## 5. Create an EC2 instance

WORKSTATION — you can use the AWS console with the same settings, or use these CLI commands. This section creates paid resources. Reuse a suitable existing instance instead of launching duplicates.

Use **Ubuntu 24.04 x86-64**, because the current CI image build targets x86-64 and Ubuntu supplies Python 3.12. Start with an instance offering about 8 GB RAM, such as `t3.large`, and a 60 GiB gp3 root disk to allow room for the OS, images, models and a previous release. Measure load afterwards. An ARM instance requires separately built compatible images. The [AWS T3 specification](https://aws.amazon.com/ec2/instance-types/t3/) lists the hardware and burstable-CPU model; account for sustained workload/credit behavior when choosing capacity.

Discover a current Canonical AMI rather than hard-coding an aging AMI ID:

```bash
export AMI_ID="$(aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id --query Parameter.Value --output text)"
aws ec2 describe-images --image-ids "$AMI_ID" --query 'Images[0].{id:ImageId,name:Name,owner:OwnerId,architecture:Architecture}'
export ROOT_DEVICE="$(aws ec2 describe-images --image-ids "$AMI_ID" --query 'Images[0].RootDeviceName' --output text)"
```

This uses Canonical's [published AMI discovery method](https://ubuntu.com/aws/docs/aws-how-to/instances/find-ubuntu-images/). Confirm the returned architecture and owner before launching.

Select the default VPC/public subnet, or substitute your existing approved public subnet:

```bash
export VPC_ID="$(aws ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text)"
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[].{id:SubnetId,zone:AvailabilityZone,default:DefaultForAz}'
export SUBNET_ID='<chosen-public-subnet-id>'
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC_ID" --query 'RouteTables[].Routes'
export SSH_CIDR='<your-current-public-ip>/32'
```

If there is no default VPC, stop and select/create the appropriate VPC/subnet through your account's network setup. The subnet needs a route to an internet gateway for this direct SSH example. `SSH_CIDR` is your public IP, not a private `192.168.*` address or the EC2 address. Update the SSH rule if your network IP changes.

Create a project security group once:

```bash
export SECURITY_GROUP_ID="$(aws ec2 create-security-group --group-name careerflowops-ec2 --description 'CareerFlowOps restricted EC2 access' --vpc-id "$VPC_ID" --query GroupId --output text)"
aws ec2 authorize-security-group-ingress --group-id "$SECURITY_GROUP_ID" --protocol tcp --port 22 --cidr "$SSH_CIDR"
```

For an existing group, obtain its ID with `describe-security-groups` and inspect current rules; do not repeat creation. Leave normal outbound access available for ECR, S3, Docker Hub, package installs and optional live ATS ingestion.

Create a local SSH key only if absent and import its **public** key into AWS once:

```bash
install -d -m 700 "$HOME/.ssh"
test -f "$HOME/.ssh/careerflowops-ec2" || ssh-keygen -t ed25519 -f "$HOME/.ssh/careerflowops-ec2" -C careerflowops-ec2
aws ec2 import-key-pair --key-name careerflowops-ec2 --public-key-material "fileb://$HOME/.ssh/careerflowops-ec2.pub"
```

Keep the private key outside the repository. If the AWS key name already exists, verify it corresponds to your local key or deliberately choose another name.

Launch once, then wait and inspect:

```bash
export INSTANCE_ID="$(aws ec2 run-instances \
  --image-id "$AMI_ID" \
  --instance-type t3.large \
  --count 1 \
  --key-name careerflowops-ec2 \
  --subnet-id "$SUBNET_ID" \
  --security-group-ids "$SECURITY_GROUP_ID" \
  --associate-public-ip-address \
  --iam-instance-profile Name=CareerFlowOpsEC2 \
  --metadata-options HttpTokens=required,HttpPutResponseHopLimit=1 \
  --block-device-mappings "[{\"DeviceName\":\"$ROOT_DEVICE\",\"Ebs\":{\"VolumeSize\":60,\"VolumeType\":\"gp3\",\"Encrypted\":true,\"DeleteOnTermination\":true}}]" \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=CareerFlowOps}]' \
  --client-token careerflowops-initial-ec2-20261017 \
  --query 'Instances[0].InstanceId' \
  --output text)"
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
aws ec2 wait instance-status-ok --instance-ids "$INSTANCE_ID"
export EC2_HOST="$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"
aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].{id:InstanceId,state:State.Name,ip:PublicIpAddress,profile:IamInstanceProfile.Arn}'
ssh -i "$HOME/.ssh/careerflowops-ec2" "ubuntu@$EC2_HOST"
```

The client token makes an identical retry idempotent; do not reuse it with changed launch parameters or change it merely to bypass an error. Compare the SSH host-key fingerprint with the account/instance information before trusting a new host. Launch options are documented in the [EC2 CLI reference](https://docs.aws.amazon.com/cli/latest/reference/ec2/run-instances.html).

Retain `INSTANCE_ID`, `EC2_HOST`, `SECURITY_GROUP_ID`, region, bucket and the published `RELEASE_SHA` in your operator notes. Public IPs may change after stop/start unless you configure a stable address; update tunnels and DNS accordingly.

## 6. Install the EC2 host tools

EC2 — Ubuntu 24.04 shell. Install Git, Python/venv, curl, unzip and Docker's signed repository:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git unzip python3 python3-venv
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF_DOCKER
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF_DOCKER
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out and reconnect for group membership to apply. These commands assume a fresh host without conflicting Docker packages; follow [Docker's Ubuntu installation guide](https://docs.docker.com/engine/install/ubuntu/) if adapting an existing server. Docker-group access grants substantial host privileges; restrict who receives it.

EC2 — after reconnecting, install AWS CLI v2 and verify tools:

```bash
export AWS_CLI_TMP="$(mktemp -d -t careerflowops-awscli-XXXXXX)"
curl --fail --location https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip --output "$AWS_CLI_TMP/awscliv2.zip"
unzip -q "$AWS_CLI_TMP/awscliv2.zip" -d "$AWS_CLI_TMP"
sudo "$AWS_CLI_TMP/aws/install"
export DOCKER_HOST=unix:///var/run/docker.sock
export AWS_REGION=ap-south-1
export AWS_DEFAULT_REGION="$AWS_REGION"
docker version
docker compose version
python3 --version
aws --version
aws sts get-caller-identity
```

The EC2 AWS identity should be the attached `CareerFlowOpsEC2` role. Do not run `aws configure` with long-lived keys on EC2. DVC/S3 access is performed by the host, so IMDSv2 with a one-hop limit is compatible with this deployment. Node/npm, training environments and GPU drivers are not needed on EC2; it pulls built images.

## 7. Deploy the exact release

EC2 — obtain the full published SHA from workstation stage 7, then clone/check out that version:

```bash
git clone https://github.com/Amitkumarracha/CareerFlowOps.git
cd CareerFlowOps
export RELEASE_SHA='<full-40-character-published-git-sha>'
git checkout "$RELEASE_SHA"
python3 infra/scripts/configure.py
chmod 600 .env
nano .env
```

If the repository is private, configure a read-only repository deploy key/approved Git access on this host; do not embed a token in its clone URL. On subsequent releases, use the existing checkout and fetch the intended SHA instead of recloning over it.

The setup script generates distinct local secrets for this host. Review `.env` locally:

| Setting | Value/action |
| --- | --- |
| `APP_ENV` | `production` |
| `POSTGRES_PASSWORD` and `DATABASE_URL` | Keep the same generated password in both; database host remains `postgres` |
| `CANDIDATE_API_TOKEN`, `ADMIN_API_TOKEN`, `GRAFANA_ADMIN_PASSWORD` | Keep distinct generated values; do not expose them in screenshots |
| `CORS_ORIGINS` | `http://localhost:15173` for the private mode, or your HTTPS origin |
| `MLFLOW_TRACKING_URI` | Keep Compose service URI; bundle inference does not depend on a populated EC2 registry |
| `API_PORT`, `WEB_PORT` | Keep `8000`, `5173` for this guide |
| AWS static access-key variables | Leave blank; use the instance role |

Do not copy your workstation's database password or candidate data to the new host just to make startup pass. The production Compose overlay sets `MODEL_BUNDLE_PATH=/app/ml/artifacts/production`.

EC2 — install the small model-delivery environment, export image/model locations and deploy:

```bash
python3 -m venv .venv-deploy
.venv-deploy/bin/pip install -r requirements-deploy.lock
export AWS_REGION=ap-south-1
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export MODEL_BUCKET="careerflowops-models-${AWS_ACCOUNT_ID}-${AWS_REGION}"
export DVC_REMOTE_URL="s3://$MODEL_BUCKET/careerflowops"
export API_IMAGE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/careerflowops-api:$RELEASE_SHA"
export WEB_IMAGE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/careerflowops-web:$RELEASE_SHA"
bash infra/aws/deploy.sh
```

If file ownership differs from the image's UID 1000, inspect `id` and the ownership of `data/` and `mlflow-data/`. Grant UID 1000 write access to those project directories only. The model directory needs read/traverse access. Do not change ownership recursively across your home directory or the whole checkout merely to fix one mount.

After successful deployment, persist the two image references in protected `.env` so later Compose monitoring/inspection commands resolve the same images even after reconnecting:

```bash
.venv-deploy/bin/python - <<'PY'
import os
from dotenv import set_key
for name in ['API_IMAGE', 'WEB_IMAGE']:
    set_key('.env', name, os.environ[name])
PY
chmod 600 .env
docker compose -f docker-compose.yml -f infra/aws/compose.production.yml ps
curl --fail http://127.0.0.1:8000/ready
```

**Exit check:** readiness contains `status=ready`, a non-null `bundle_id`, `algorithm` and `model_version`. The script checks the running bundle ID against the downloaded manifest. Missing/corrupt/incompatible releases fail before service startup; the production API cannot silently use a local alternative.

The new EC2 MLflow service starts with its own backend. It will not automatically contain the workstation's experiment history or version 3 alias. The deployed MLOps page reads the evaluated training/registry metadata shipped inside the verified release. For experiment tracking evidence, use the actual training MLflow server; shared remote MLflow hosting is a separate improvement.

## 8. Private demonstration with SSH tunnels

WORKSTATION — use your actual EC2 address and key. Keep this terminal open:

```bash
export EC2_HOST='<current-ec2-public-ip-or-dns>'
ssh -i "$HOME/.ssh/careerflowops-ec2" -N -o ExitOnForwardFailure=yes -L 15173:127.0.0.1:5173 -L 18000:127.0.0.1:8000 -L 15000:127.0.0.1:5000 -L 13000:127.0.0.1:3000 -L 19090:127.0.0.1:9090 "ubuntu@$EC2_HOST"
```

Open the EC2 portal at http://localhost:15173 and API docs at http://localhost:18000/docs. EC2 monitoring is http://localhost:13000 and http://localhost:19090 after the monitoring profile starts. EC2 MLflow is http://localhost:15000; the training workstation's MLflow remains separately at port 5000.

Use EC2-generated access tokens in that browser tab's Workspace access form. They differ from workstation tokens. If the frontend calls port 8000 rather than 18000, the published frontend origin is wrong: set the GitHub variable to port 18000, build/publish a **new SHA**, then deploy it.

## 9. Optional public domain and HTTPS

WORKSTATION — choose your domain, set `VITE_API_BASE_URL=https://<your-domain>` in GitHub, publish a new SHA and deploy it. On EC2 set `CORS_ORIGINS` to the same origin. Point the domain's A record to the instance address; configure an AAAA record only if IPv6 access is correctly set up.

WORKSTATION — open edge ports on the project security group only:

```bash
export SECURITY_GROUP_ID='<careerflowops-security-group-id>'
aws ec2 authorize-security-group-ingress --group-id "$SECURITY_GROUP_ID" --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id "$SECURITY_GROUP_ID" --protocol tcp --port 443 --cidr 0.0.0.0/0
```

EC2 — after DNS resolves, keep the domain in protected `.env` for later Compose sessions, then start Caddy:

```bash
cd ~/CareerFlowOps
export PUBLIC_DOMAIN='<your-domain-without-https-prefix>'
.venv-deploy/bin/python - <<'PY'
import os
from dotenv import set_key
set_key('.env', 'PUBLIC_DOMAIN', os.environ['PUBLIC_DOMAIN'])
PY
docker compose -f docker-compose.yml -f infra/aws/compose.production.yml -f infra/aws/compose.edge.yml up -d edge
curl --fail "https://$PUBLIC_DOMAIN/ready"
```

Keep monitoring and database ports private. The current single-candidate token system is suitable for a controlled demonstration, not a shared campus-wide account service. Do not distribute one candidate token to unrelated students.

## 10. Start monitoring and complete verification

EC2:

```bash
docker compose -f docker-compose.yml -f infra/aws/compose.production.yml --profile monitoring up -d --no-build prometheus grafana
docker compose -f docker-compose.yml -f infra/aws/compose.production.yml ps
curl --fail http://127.0.0.1:9090/-/ready
curl --fail http://127.0.0.1:3000/api/health
```

Continue to [operations and assessment](04_OPERATIONS_AND_ASSESSMENT.md). Retain the deployed SHA, ECR digests, DVC bundle ID, successful hosted run and actual inference evidence. Runtime containers use restart policies; they do not yet provide automatic high availability, model retraining or database migration rollback.
