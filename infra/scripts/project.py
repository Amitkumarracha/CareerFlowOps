"""Inspectable status, presentation and artifact-first release commands."""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import yaml

from ml.inference.bundle import load_bundle

DVC = str(Path(sys.executable).parent / "dvc")
BUNDLE = Path("ml/artifacts/production")


def command(arguments: list[str], cwd: Path | None = None) -> None:
    print("$ " + shlex.join(arguments), flush=True)
    environment = {**os.environ, "DVC_NO_ANALYTICS": "true"}
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    subprocess.run(arguments, cwd=cwd, env=environment, check=True)


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], text=True).strip()


def artifact(name: str) -> dict:
    path = Path("ml/artifacts") / name
    return json.loads(path.read_text()) if path.exists() else {}


def remote_url(name: str) -> str:
    # DVC resolves local remote paths relative to the configuration file for us.
    from dvc.repo import Repo

    with Repo() as repository:
        config = repository.config.get("remote", {}).get(name)
        if not config:
            raise ValueError(f"DVC remote {name!r} is not configured")
        url = config["url"]
    parsed = urlsplit(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Keep remote credentials in the AWS provider chain, not the remote URL")
    return url


def delivery_dvc(url: str) -> str:
    if urlsplit(url).scheme == "s3":
        executable = Path(".venv-deploy/bin/dvc").resolve()
        if not executable.is_file():
            raise ValueError("Run make cloud-setup for the pinned DVC/S3 delivery environment")
        return str(executable)
    return DVC


def status(api_url: str = "http://localhost:8000") -> dict:
    packages = {}
    for name in ["fastapi", "scikit-learn", "sentence-transformers", "mlflow", "dvc", "torch"]:
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    services = {}
    for name, url in {
        "api_health": api_url + "/health",
        "api_readiness": api_url + "/ready",
        "mlflow": "http://localhost:5000/health",
        "prometheus": "http://localhost:9090/-/ready",
        "grafana": "http://localhost:3000/api/health",
    }.items():
        try:
            response = httpx.get(url, timeout=5)
            services[name] = {"http_status": response.status_code}
            if name == "api_readiness" and response.is_success:
                services[name]["identity"] = response.json()
        except httpx.HTTPError:
            services[name] = {"http_status": None}
    training, registry, config = (
        artifact(name) for name in ["training.json", "registry.json", "model.json"]
    )
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "git_commit": git("rev-parse", "HEAD"),
        "tracked_changes": bool(git("diff", "HEAD", "--name-only")),
        "python": sys.version.split()[0],
        "packages": packages,
        "pipeline": list(yaml.safe_load(Path("dvc.yaml").read_text())["stages"]),
        "training_commit": training.get("git_commit"),
        "dataset_version": training.get("dataset_version"),
        "model_version": config.get("model_version"),
        "selected_algorithm": config.get("algorithm"),
        "mlflow_version": registry.get("version"),
        "mlflow_run_id": registry.get("run_id"),
        "services": services,
        "cloud_execution": "Not established by local checks; verify ECR/S3/EC2 separately.",
    }


def present(remote: str, api_url: str) -> None:
    report = status(api_url)
    print(json.dumps(report, indent=2), flush=True)
    command(["docker", "compose", "images"])
    command([DVC, "dag", "--mermaid"])
    command([DVC, "status"])
    training, evaluation, registry = (
        artifact(name) for name in ["training.json", "evaluation.json", "registry.json"]
    )
    if not all([training, evaluation, registry]):
        raise ValueError(
            "Run make reproduce to generate training, evaluation and registry artifacts"
        )
    from mlflow.tracking import MlflowClient

    tracking = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    client = MlflowClient(tracking_uri=tracking)
    production = client.get_model_version_by_alias(registry["model_name"], registry["alias"])
    if production.run_id != registry["run_id"] or production.version != registry["version"]:
        raise ValueError("Saved registry metadata differs from the active MLflow alias")
    for run in training["runs"]:
        actual = client.get_run(run["run_id"])
        if actual.info.status != "FINISHED":
            raise ValueError("A recorded experiment has not finished")
        print(
            json.dumps(
                {
                    "algorithm": run["algorithm"],
                    "run_id": run["run_id"],
                    "measured_metrics": actual.data.metrics,
                }
            ),
            flush=True,
        )
    print(evaluation["labels_description"], flush=True)
    url = remote_url(remote)
    downloader = delivery_dvc(url)
    print(f"Fresh DVC pull from {remote!r} ({urlsplit(url).scheme or 'local filesystem'}).")
    with tempfile.TemporaryDirectory(prefix="careerflowops-presentation-") as temporary:
        folder = Path(temporary)
        for name in ["dvc.yaml", "dvc.lock"]:
            shutil.copy2(name, folder / name)
        command([downloader, "init", "--no-scm"], folder)
        command([downloader, "remote", "add", "presentation", url], folder)
        command([downloader, "pull", "-r", "presentation", str(BUNDLE)], folder)
        release = load_bundle(str(folder / BUNDLE))
        identity = report["services"]["api_readiness"].get("identity", {})
        if identity.get("bundle_id") != release.bundle_id:
            raise ValueError("Running API is not serving this bundle; run make serve-release first")
        response = httpx.get(api_url + "/api/jobs?limit=5", timeout=15)
        response.raise_for_status()
        jobs = response.json()["items"]
        if not jobs:
            raise ValueError("Ingest real source jobs before presenting predictions")
        prediction = release.predict(
            {"skills": ["python", "sql"], "summary": "Fictional demonstration profile"}, jobs
        )[0]
        if not prediction["explanation"] or prediction["fallback_reason"]:
            raise ValueError("Release did not produce an explained prediction without fallback")
        report["verified_pull"] = {
            "remote": remote,
            "kind": urlsplit(url).scheme or "local",
            "bundle_id": release.bundle_id,
            "profile_source": "Fictional demonstration profile, evaluated in memory only",
            "prediction": prediction,
        }
    load_bundle.cache_clear()
    output = Path("ops-private/evidence/presentation.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report["verified_pull"], indent=2))
    print(f"Presentation checks passed. Actual evidence saved to {output}.")


def release_preflight() -> None:
    if git("branch", "--show-current") != "main":
        raise ValueError("Switch to reviewed main before synchronizing a release")
    changed = set(git("diff", "HEAD", "--name-only").splitlines())
    if changed - {"dvc.lock"}:
        raise ValueError("Commit reviewed source changes first; only dvc.lock is auto-committed")
    git("remote", "get-url", "origin")


def sync(remote: str) -> None:
    release_preflight()
    url = remote_url(remote)
    load_bundle(str(BUNDLE))
    changed = json.loads(
        subprocess.check_output([DVC, "status", "export_model", "--json"], text=True)
    )
    if changed:
        raise ValueError("Production bundle pointer is stale; run make reproduce before syncing")
    # Publish objects before exposing a Git pointer that depends on them.
    command([delivery_dvc(url), "push", "-r", remote])
    if git("diff", "HEAD", "--name-only", "--", "dvc.lock"):
        command(["git", "add", "--", "dvc.lock"])
        command(
            ["git", "commit", "--only", "-m", "ml: version evaluated release", "--", "dvc.lock"]
        )
    command(["git", "push", "-u", "origin", "main"])
    print("Synchronized release " + git("rev-parse", "HEAD"))
    print("GitHub Actions now checks/builds it; configured AWS jobs publish/deploy it.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["status", "present", "sync", "release"])
    parser.add_argument("--remote", default="storage")
    parser.add_argument("--api-url", default="http://localhost:8000")
    args = parser.parse_args()
    try:
        if args.action == "status":
            print(json.dumps(status(args.api_url), indent=2))
        elif args.action == "present":
            present(args.remote, args.api_url)
        else:
            if args.action == "release":
                release_preflight()
                command(["make", "test"])
                command(["make", "lint"])
                command(["npm", "--prefix", "apps/web", "run", "build"])
                command([sys.executable, "infra/scripts/host.py", DVC, "repro"])
            sync(args.remote)
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Project command stopped: {exc}\n")


if __name__ == "__main__":
    main()
