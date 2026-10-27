import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from infra.aws.policies import render
from infra.scripts.configure import main


def test_configuration_generates_and_preserves_private_env(tmp_path, monkeypatch, capsys) -> None:
    template = Path(".env.example").read_text()
    monkeypatch.chdir(tmp_path)
    Path(".env.example").write_text(template)
    main()
    content = Path(".env").read_text()
    assert "CHANGE_ME" not in content
    assert Path(".env").stat().st_mode & 0o777 == 0o600
    assert "CANDIDATE_API_TOKEN=\n" not in content
    main()
    assert Path(".env").read_text() == content
    assert content not in capsys.readouterr().out


def test_deployment_rejects_missing_image_before_cloud_actions() -> None:
    result = subprocess.run(["bash", "infra/aws/deploy.sh"], env={}, capture_output=True, text=True)
    assert result.returncode != 0
    assert "immutable ECR API image" in result.stderr


def test_iam_documents_restrict_repo_storage_and_ec2_permissions(tmp_path) -> None:
    render("123456789012", "ap-south-1", "unit-test-model-storage", tmp_path)
    trust = json.loads((tmp_path / "github-trust.json").read_text())
    assert (
        trust["Statement"][0]["Condition"]["StringEquals"][
            "token.actions.githubusercontent.com:sub"
        ]
        == "repo:Arjun-Reddy-I/CareerFlowOps:ref:refs/heads/main"
    )
    policy = json.loads((tmp_path / "ec2-pull.json").read_text())
    assert "s3:PutObject" not in json.dumps(policy)
    assert "ecr:PutImage" not in json.dumps(policy)
    assert "unit-test-model-storage/careerflowops/*" in json.dumps(policy)
    with pytest.raises(ValueError):
        render("ACCOUNT_ID", "ap-south-1", "unit-test-model-storage", tmp_path)


@pytest.mark.parametrize("model_invalid", [False, True])
def test_deployment_checks_model_before_starting_services(tmp_path, model_invalid) -> None:
    script = Path("infra/aws/deploy.sh").resolve()
    tools = tmp_path / "tools"
    tools.mkdir()
    fake = """#!/usr/bin/env python3
import hashlib, json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
with open(os.environ["CALL_LOG"], "a") as stream:
    stream.write(json.dumps([name, *sys.argv[1:]]) + "\\n")
if name == "git": print("a" * 40)
if name == "aws": print("unit-test-password")
if name == "docker" and "login" in sys.argv: sys.stdin.read()
if name == "docker" and "run" in sys.argv and os.environ["MODEL_INVALID"] == "1":
    sys.exit(1)
if name == "curl":
    manifest = Path("ml/artifacts/production/manifest.json").read_bytes()
    print(json.dumps({"status":"ready", "bundle_id":hashlib.sha256(manifest).hexdigest()}))
"""
    for name in ["aws", "docker", "git", "dvc", "curl"]:
        target = tools / name
        target.write_text(fake)
        target.chmod(0o755)
    configure = tmp_path / "infra/scripts/configure.py"
    configure.parent.mkdir(parents=True)
    shutil.copyfile("infra/scripts/configure.py", configure)
    (tmp_path / ".env").touch(mode=0o600)
    manifest = tmp_path / "ml/artifacts/production/manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}")
    registry = "123456789012.dkr.ecr.ap-south-1.amazonaws.com"
    log = tmp_path / "calls.jsonl"
    result = subprocess.run(
        ["bash", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PATH": f"{tools}:{os.environ['PATH']}",
            "API_IMAGE": f"{registry}/careerflowops-api:{'a' * 40}",
            "WEB_IMAGE": f"{registry}/careerflowops-web:{'a' * 40}",
            "AWS_REGION": "ap-south-1",
            "DVC_REMOTE_URL": "s3://test-bucket/careerflowops",
            "DVC_BIN": str(tools / "dvc"),
            "CALL_LOG": str(log),
            "MODEL_INVALID": str(int(model_invalid)),
        },
    )
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    pull = next(i for i, call in enumerate(calls) if call[:2] == ["dvc", "pull"])
    validation = next(i for i, call in enumerate(calls) if "--validate" in call)
    starts = [i for i, call in enumerate(calls) if "up" in call]
    assert pull < validation
    if model_invalid:
        assert result.returncode != 0 and not starts
    else:
        assert result.returncode == 0, result.stderr
        assert starts and validation < min(starts)
