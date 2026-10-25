import json
import shlex
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import yaml

from infra.aws import ssm_deploy
from infra.scripts import project


@pytest.mark.parametrize("change", ["apps/api/app/main.py", ".env.example", "params.yaml"])
def test_sync_refuses_uncommitted_source_changes(change, monkeypatch) -> None:
    def git(*args):
        return "main" if args[0] == "branch" else change

    monkeypatch.setattr(project, "git", git)
    with pytest.raises(ValueError, match="Commit reviewed source"):
        project.release_preflight()


def test_sync_publishes_artifacts_before_pointer_and_never_adds_unknown_files(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(project, "release_preflight", lambda: None)
    monkeypatch.setattr(project, "remote_url", lambda _: "/tmp/release-remote")
    monkeypatch.setattr(project, "load_bundle", lambda _: object())
    monkeypatch.setattr(project.subprocess, "check_output", lambda *a, **kw: "{}")
    monkeypatch.setattr(project, "command", lambda args: calls.append(args))
    monkeypatch.setattr(project, "git", lambda *args: "dvc.lock" if args[0] == "diff" else "a" * 40)
    project.sync("storage")
    assert calls[0] == [project.DVC, "push", "-r", "storage"]
    assert calls[1] == ["git", "add", "--", "dvc.lock"]
    assert calls[-1] == ["git", "push", "-u", "origin", "main"]
    assert "--only" in calls[2] and ".env" not in str(calls)


def test_failed_dvc_upload_never_commits_or_pushes_git(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(project, "release_preflight", lambda: None)
    monkeypatch.setattr(project, "remote_url", lambda _: "/tmp/release-remote")
    monkeypatch.setattr(project, "load_bundle", lambda _: object())
    monkeypatch.setattr(project.subprocess, "check_output", lambda *a, **kw: "{}")

    def failed(args):
        calls.append(args)
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(project, "command", failed)
    with pytest.raises(subprocess.CalledProcessError):
        project.sync("storage")
    assert len(calls) == 1 and calls[0][1] == "push"


def test_presentation_refuses_stale_registry_metadata(monkeypatch) -> None:
    monkeypatch.setattr(project, "status", lambda *_: {})
    monkeypatch.setattr(project, "command", lambda *_: None)
    monkeypatch.setattr(
        project,
        "artifact",
        lambda name: {
            "model_name": "test",
            "alias": "production",
            "run_id": "saved-run",
            "version": "1",
        },
    )
    module = ModuleType("mlflow.tracking")
    module.MlflowClient = lambda **kwargs: SimpleNamespace(
        get_model_version_by_alias=lambda *_: SimpleNamespace(run_id="different-run", version="2")
    )
    monkeypatch.setitem(sys.modules, "mlflow", ModuleType("mlflow"))
    monkeypatch.setitem(sys.modules, "mlflow.tracking", module)
    with pytest.raises(ValueError, match="differs from the active"):
        project.present("storage", "http://localhost:8000")


def test_ci_deploy_requires_published_images_and_explicit_configuration() -> None:
    workflow = yaml.load(
        Path(".github/workflows/docker-publish.yml").read_text(), Loader=yaml.BaseLoader
    )
    job = workflow["jobs"]["deploy"]
    assert job["needs"] == "build"
    assert "needs.build.outputs.published == 'true'" in job["if"]
    assert "vars.AUTO_DEPLOY == 'true'" in job["if"]
    assert job["concurrency"]["cancel-in-progress"] == "false"


def test_ssm_cli_reports_aws_authentication_errors(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ssm_deploy",
            "--sha",
            "a" * 40,
            "--instance",
            "i-0123456789abcdef0",
            "--region",
            "ap-south-1",
            "--remote",
            "s3://test/project",
        ],
    )

    def denied(args):
        raise subprocess.CalledProcessError(1, args, stderr="AccessDenied: role is not authorized")

    monkeypatch.setattr(ssm_deploy, "aws", denied)
    with pytest.raises(SystemExit) as failure:
        ssm_deploy.main()
    assert failure.value.code == 1
    assert "AccessDenied" in capsys.readouterr().err


def test_ssm_payload_preserves_owner_and_checks_revision_before_stopping_services() -> None:
    payload = ssm_deploy.parameters(
        "a" * 40,
        "123456789012",
        "ap-south-1",
        "s3://unit-test/careerflowops",
        "/home/ubuntu/CareerFlowOps",
        "ubuntu",
    )
    wrapper = shlex.split(payload["commands"][0])
    assert wrapper[:6] == ["runuser", "-u", "ubuntu", "--", "bash", "-c"]
    script = wrapper[6]
    assert script.index("git status") < script.index("stop api web")
    assert script.index("git rev-parse FETCH_HEAD") < script.index("stop api web")
    assert script.index("git checkout") < script.index("bash infra/aws/deploy.sh")
    subprocess.run(["bash", "-n"], input=script, text=True, check=True)


@pytest.mark.parametrize(
    "key,value",
    [
        ("sha", "main; dangerous"),
        ("account", "ACCOUNT_ID"),
        ("region", "bad; region"),
        ("remote", "s3://key:secret@bucket/path"),
        ("directory", "/home/ubuntu/../other"),
        ("user", "root"),
    ],
)
def test_ssm_rejects_invalid_deployment_inputs(key, value) -> None:
    args = dict(
        sha="a" * 40,
        account="123456789012",
        region="ap-south-1",
        remote="s3://unit-test/careerflowops",
        directory="/home/ubuntu/CareerFlowOps",
        user="ubuntu",
    )
    args[key] = value
    with pytest.raises(ValueError):
        ssm_deploy.parameters(**args)


@pytest.mark.parametrize("state", ["Success", "Failed", "TimedOut", "Cancelled"])
def test_ssm_waiter_reports_real_terminal_result(state, monkeypatch) -> None:
    calls = []

    def aws(args):
        calls.append(args)
        if args[1] == "send-command":
            payload = json.loads(Path(args[args.index("--parameters") + 1][7:]).read_text())
            assert payload["commands"]
            return {"Command": {"CommandId": "test-command"}}
        return {"Status": state}

    monkeypatch.setattr(ssm_deploy, "aws", aws)
    if state == "Success":
        ssm_deploy.deploy("i-0123456789abcdef0", {"commands": ["true"]}, "ap-south-1")
    else:
        with pytest.raises(RuntimeError, match=state):
            ssm_deploy.deploy("i-0123456789abcdef0", {"commands": ["true"]}, "ap-south-1")
    assert len(calls) == 2
    assert all(call[call.index("--region") + 1] == "ap-south-1" for call in calls)
