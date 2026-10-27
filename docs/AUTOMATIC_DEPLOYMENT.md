# Optional automatic EC2 deployment after ECR publishing

The code path is implemented and unit-tested. Actual AWS execution requires your account, instance and role configuration. Enabling this is optional; the manual deployment guide remains supported. No cloud resources are created merely by adding these files.

## Preconditions

- The initial [AWS deployment guide](remaining/03_AWS_DEPLOYMENT.md) has been completed, including S3 model objects, ECR repositories, GitHub OIDC and a working EC2 host.
- The host has the repository at `/home/ubuntu/CareerFlowOps` (or your configured directory), protected `.env`, Docker access, Python and `.venv-deploy` with the pinned requirements.
- The non-root deployment user owns the checkout and can pull the repository. Use a read-only deploy key if the repository is private.
- The instance has the `Name=CareerFlowOps` tag used by the scoped SSM policy.
- The deployed application is backed up before upgrades. This remains a single-host deployment with a maintenance window and no automatic database rollback.

## 1. Enable Systems Manager on the existing instance

WORKSTATION — authenticated AWS CLI:

```bash
aws iam attach-role-policy --role-name CareerFlowOpsEC2 --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
```

EC2 — for the Ubuntu 24.04 Snap agent installation:

```bash
sudo snap list amazon-ssm-agent
sudo systemctl enable --now snap.amazon-ssm-agent.amazon-ssm-agent.service
sudo systemctl status snap.amazon-ssm-agent.amazon-ssm-agent.service
```

If the agent is absent, install it using the [official Ubuntu SSM Agent instructions](https://docs.aws.amazon.com/systems-manager/latest/userguide/agent-install-ubuntu-64-snap.html). A non-Snap installation has a different service name. The host needs outbound access to the regional Systems Manager endpoints (or configured VPC endpoints).

WORKSTATION — verify the instance is managed and online:

```bash
export EC2_INSTANCE_ID='<your-careerflowops-instance-id>'
aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$EC2_INSTANCE_ID" --query 'InstanceInformationList[].{id:InstanceId,status:PingStatus}'
```

## 2. Create a separate GitHub deployment role

WORKSTATION — the existing policy renderer now also produces `github-deploy.json`:

```bash
export AWS_REGION=ap-south-1
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export MODEL_BUCKET="careerflowops-models-${AWS_ACCOUNT_ID}-${AWS_REGION}"
python3 infra/aws/policies.py --account "$AWS_ACCOUNT_ID" --region "$AWS_REGION" --bucket "$MODEL_BUCKET"
aws iam create-role --role-name CareerFlowOpsGitHubDeploy --assume-role-policy-document file://.aws-policies/github-trust.json
aws iam put-role-policy --role-name CareerFlowOpsGitHubDeploy --policy-name CareerFlowOpsSSMDeploy --policy-document file://.aws-policies/github-deploy.json
```

Inspect/reuse the role rather than repeating creation if it already exists. Its trust permits this repository's main branch. Sending commands is limited to the AWS shell document and EC2 instances with the project tag. Reading command results uses the regional `ssm:GetCommandInvocation` permission; that action requires a wildcard resource in this policy. Keep main protected because authorized main-branch code can deploy to the tagged host.

## 3. Configure the repository

WORKSTATION — authenticated GitHub CLI:

```bash
export GH_REPO=Arjun-Reddy-I/CareerFlowOps
gh secret set AWS_DEPLOY_ROLE_ARN --repo "$GH_REPO" --body "arn:aws:iam::$AWS_ACCOUNT_ID:role/CareerFlowOpsGitHubDeploy"
gh variable set EC2_INSTANCE_ID --repo "$GH_REPO" --body "$EC2_INSTANCE_ID"
gh variable set DVC_REMOTE_URL --repo "$GH_REPO" --body "s3://$MODEL_BUCKET/careerflowops"
gh variable set EC2_PROJECT_DIR --repo "$GH_REPO" --body /home/ubuntu/CareerFlowOps
gh variable set EC2_DEPLOY_USER --repo "$GH_REPO" --body ubuntu
gh variable set AUTO_DEPLOY --repo "$GH_REPO" --body true
```

Keep the existing `AWS_ROLE_ARN` secret for ECR publishing and `AWS_REGION`, ECR repository names and `VITE_API_BASE_URL` variables. This deployment implementation uses the standard repository names `careerflowops-api` and `careerflowops-web`. Configure the frontend origin correctly before publishing an immutable SHA.

## 4. Release and inspect

```bash
make release DVC_REMOTE=production
gh run list --repo "$GH_REPO" --workflow docker-publish.yml
```

The configured sequence is checks → API/web build → ECR push → SSM deployment. Deployment is serialized. Failed/skipped image publication does not deploy. The SSM script validates inputs, verifies clean tracked source and current remote main before stopping the API/web, checks out the requested SHA, then runs the existing validated deployment script as the non-root owner. It saves the successful image references in protected `.env` for later Compose sessions.

A newer commit arriving before an older deployment starts causes that older request to fail its main-tip guard instead of installing an obsolete release. Inspect the latest run and deploy its current SHA. SSM failure/timeouts fail the GitHub job; they are not reported as success. Inspect the SSM command before retrying a timeout, because a host command can still be running.

## 5. Disable automatic deployment

```bash
gh variable set AUTO_DEPLOY --repo "$GH_REPO" --body false
```

CI and image publication continue. Manual EC2 deployment remains available. Do not replace this setting with an unconditional deployment step or store a long-lived AWS access key in the workflow.
