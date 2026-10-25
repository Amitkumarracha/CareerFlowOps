"""Deploy one immutable release through SSM; invoked only by configured CI."""

import argparse
import json
import re
import shlex
import subprocess
import tempfile
import time
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


def parameters(sha: str, account: str, region: str, remote: str, directory: str, user: str) -> dict:
    if not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise ValueError("Use a full lowercase Git SHA")
    if not re.fullmatch(r"[0-9]{12}", account):
        raise ValueError("Invalid AWS account")
    if not re.fullmatch(r"[a-z]{2}-[a-z]+-[0-9]", region):
        raise ValueError("Invalid standard AWS region")
    parsed = urlsplit(remote)
    if (
        parsed.scheme != "s3"
        or not parsed.netloc
        or parsed.path in {"", "/"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Use a credential-free S3 project prefix")
    path = PurePosixPath(directory)
    if not path.is_absolute() or str(path) == "/" or ".." in path.parts:
        raise ValueError("Use an absolute project directory without parent traversal")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]*", user) or user == "root":
        raise ValueError("Use the non-root deployment user")
    registry = f"{account}.dkr.ecr.{region}.amazonaws.com"
    commands = [
        "set -euo pipefail",
        "cd " + shlex.quote(directory),
        "test -f .env",
        'test -z "$(git status --porcelain --untracked-files=no)"',
        "git fetch --no-tags origin main",
        f'test "$(git rev-parse FETCH_HEAD)" = {shlex.quote(sha)}',
        "export DOCKER_HOST=unix:///var/run/docker.sock",
        "docker compose -f docker-compose.yml -f infra/aws/compose.production.yml stop api web",
        "git checkout --detach " + sha,
        "export AWS_REGION=" + shlex.quote(region),
        "export AWS_DEFAULT_REGION=" + shlex.quote(region),
        "export DVC_REMOTE_URL=" + shlex.quote(remote),
        "export API_IMAGE=" + shlex.quote(f"{registry}/careerflowops-api:{sha}"),
        "export WEB_IMAGE=" + shlex.quote(f"{registry}/careerflowops-web:{sha}"),
        "bash infra/aws/deploy.sh",
        ".venv-deploy/bin/python -c "
        + shlex.quote(
            "import os; from dotenv import set_key; "
            "[set_key('.env', key, os.environ[key]) for key in ['API_IMAGE','WEB_IMAGE']]"
        ),
    ]
    # SSM runs as root; project files and Docker operations belong to its existing owner.
    script = "runuser -u " + shlex.quote(user) + " -- bash -c " + shlex.quote("\n".join(commands))
    return {"commands": [script], "executionTimeout": ["1200"]}


def aws(arguments: list[str]) -> dict:
    result = subprocess.run(
        ["aws", *arguments, "--output", "json"], check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def deploy(instance: str, payload: dict, region: str) -> None:
    if not re.fullmatch(r"i-[a-f0-9]{8,17}", instance):
        raise ValueError("Invalid EC2 instance ID")
    with tempfile.TemporaryDirectory(prefix="careerflowops-ssm-") as temporary:
        path = Path(temporary) / "parameters.json"
        path.write_text(json.dumps(payload))
        response = aws(
            [
                "ssm",
                "send-command",
                "--region",
                region,
                "--instance-ids",
                instance,
                "--document-name",
                "AWS-RunShellScript",
                "--timeout-seconds",
                "1200",
                "--parameters",
                "file://" + str(path),
                "--comment",
                "CareerFlowOps immutable release deployment",
            ]
        )
    command_id = response["Command"]["CommandId"]
    print("SSM command " + command_id, flush=True)
    deadline = time.monotonic() + 1200
    while time.monotonic() < deadline:
        try:
            invocation = aws(
                [
                    "ssm",
                    "get-command-invocation",
                    "--region",
                    region,
                    "--command-id",
                    command_id,
                    "--instance-id",
                    instance,
                ]
            )
        except subprocess.CalledProcessError as exc:
            if "InvocationDoesNotExist" not in (exc.stderr or ""):
                raise
            time.sleep(5)
            continue
        state = invocation["Status"]
        if state not in {"Pending", "InProgress", "Delayed", "Cancelling"}:
            print(invocation.get("StandardOutputContent", ""))
            print(invocation.get("StandardErrorContent", ""))
            if state != "Success":
                raise RuntimeError("EC2 deployment ended with SSM status " + state)
            print("EC2 release passed deployment readiness checks.")
            return
        time.sleep(5)
    raise TimeoutError(
        "Timed out waiting for EC2 deployment; inspect the SSM command before retrying"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--remote", required=True)
    parser.add_argument("--directory", default="/home/ubuntu/CareerFlowOps")
    parser.add_argument("--user", default="ubuntu")
    args = parser.parse_args()
    account = aws(["sts", "get-caller-identity", "--region", args.region])["Account"]
    payload = parameters(args.sha, account, args.region, args.remote, args.directory, args.user)
    deploy(args.instance, payload, args.region)


if __name__ == "__main__":
    main()
