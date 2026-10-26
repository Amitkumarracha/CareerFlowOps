"""Host operations: health checks, live ingestion, private backups and isolated restore drills."""

import argparse
import fcntl
import hashlib
import http.client
import json
import os
import shutil
import signal
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values

COMPOSE = [
    "docker",
    "compose",
    "-f",
    "docker-compose.yml",
    "-f",
    "infra/aws/compose.production.yml",
]
FILES = ("postgres.dump", "data-and-mlflow.tar.gz", "runtime.env", "git-sha.txt", "dvc.lock")
COUNTS_SQL = (
    "SELECT json_build_object("
    + ",".join(
        f"'{name}', (SELECT count(*) FROM {name})"
        for name in ["jobs", "candidates", "resumes", "applications", "saved_jobs"]
    )
    + ");"
)


def compose(*args: str, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([*COMPOSE, *args], check=True, **kwargs)


def api(path: str, *, live: bool = False) -> dict:
    environment = {**dotenv_values(".env"), **os.environ}
    headers = {}
    if live:
        token = environment.get("ADMIN_API_TOKEN")
        if not token:
            raise ValueError("ADMIN_API_TOKEN is not configured")
        headers["Authorization"] = "Bearer " + token
    connection = http.client.HTTPConnection(
        "127.0.0.1", int(environment.get("API_PORT", "8000")), timeout=900 if live else 30
    )
    try:
        headers["Content-Type"] = "application/json"
        connection.request(
            "POST" if live else "GET",
            path,
            headers=headers,
            body=json.dumps({"mode": "live"}) if live else None,
        )
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(
                f"Local API returned HTTP {response.status}; inspect service health/access"
            )
        return json.loads(response.read())
    finally:
        connection.close()


@contextmanager
def exclusive() -> Iterator[None]:
    folder = Path("ops-private")
    folder.mkdir(mode=0o700, exist_ok=True)
    folder.chmod(0o700)
    with (folder / "operations.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another ingestion/backup/restore operation is active") from exc
        yield


def ingest() -> dict:
    with exclusive():
        result = api("/api/admin/ingestion/run", live=True)
        if result.get("status") != "succeeded":
            raise RuntimeError(
                f"Ingestion ended {result.get('status')}; "
                f"inspect Source health for run {result.get('id')}"
            )
        return {key: result[key] for key in ["id", "status", "counts", "finished_at"]}


def checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def counts(database: str | None = None) -> dict:
    result = compose(
        "exec",
        "-T",
        "postgres",
        "sh",
        "-c",
        'psql -X -v ON_ERROR_STOP=1 -At -U "$POSTGRES_USER" -d "${1:-$POSTGRES_DB}" -c "$2"',
        "sh",
        database or "",
        COUNTS_SQL,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def backup() -> Path:
    with exclusive():
        running = compose("ps", "--services", "--status", "running", capture_output=True, text=True)
        services = [
            name for name in ["mlflow", "api", "web"] if name in running.stdout.splitlines()
        ]
        if set(services) != {"mlflow", "api", "web"}:
            raise RuntimeError("Start a healthy mlflow/api/web stack before a maintenance backup")
        ready = api("/ready")
        if not ready.get("bundle_id"):
            raise ValueError("Serve the verified production bundle before backing up")
        folder = Path("ops-private/backups") / (
            datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]
        )
        folder.mkdir(parents=True, mode=0o700)
        try:
            compose("stop", "web", "api", "mlflow")
            snapshot_counts = counts()
            with (folder / "postgres.dump").open("xb") as stream:
                compose(
                    "exec",
                    "-T",
                    "postgres",
                    "sh",
                    "-c",
                    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc',
                    stdout=stream,
                )
            subprocess.run(
                ["tar", "-czf", str(folder / "data-and-mlflow.tar.gz"), "data", "mlflow-data"],
                check=True,
            )
            shutil.copyfile(".env", folder / "runtime.env")
            shutil.copyfile("dvc.lock", folder / "dvc.lock")
            sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
            (folder / "git-sha.txt").write_text(sha + "\n")
            for name in FILES:
                (folder / name).chmod(0o600)
        finally:
            # Even failed dumps must return the services that this operation paused.
            compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "240", *services)
        actual = api("/ready")
        if actual.get("bundle_id") != ready["bundle_id"]:
            raise RuntimeError(
                "Model identity changed during backup; no completion manifest written"
            )
        manifest = {
            "git_commit": sha,
            "bundle_id": ready["bundle_id"],
            "counts": snapshot_counts,
            "files": {name: checksum(folder / name) for name in FILES},
        }
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (folder / "manifest.json").chmod(0o600)
        return folder


def restore_check(folder: Path) -> dict:
    with exclusive():
        folder = folder.resolve()
        if not folder.is_relative_to(Path("ops-private/backups").resolve()):
            raise ValueError("Restore checks accept only a private ops-private/backups directory")
        manifest = json.loads((folder / "manifest.json").read_text())
        if set(manifest["files"]) != set(FILES):
            raise ValueError("Invalid backup inventory")
        for name, expected in manifest["files"].items():
            if (folder / name).is_symlink() or checksum(folder / name) != expected:
                raise ValueError("Backup checksum mismatch: " + name)
        subprocess.run(
            ["tar", "-tzf", str(folder / "data-and-mlflow.tar.gz")],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        database = "careerflowops_restore_check_" + uuid4().hex
        compose(
            "exec",
            "-T",
            "postgres",
            "sh",
            "-c",
            'createdb -U "$POSTGRES_USER" "$1"',
            "sh",
            database,
        )
        try:
            with (folder / "postgres.dump").open("rb") as stream:
                compose(
                    "exec",
                    "-T",
                    "postgres",
                    "sh",
                    "-c",
                    'pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$1"',
                    "sh",
                    database,
                    stdin=stream,
                )
            restored = counts(database)
            if restored != manifest["counts"]:
                raise RuntimeError("Restored table counts differ from backup snapshot")
        finally:
            # This name is generated here; no caller can target the application database.
            compose(
                "exec",
                "-T",
                "postgres",
                "sh",
                "-c",
                'dropdb -U "$POSTGRES_USER" "$1"',
                "sh",
                database,
            )
        report = {
            "status": "passed",
            "checked_at": datetime.now(UTC).isoformat(),
            "counts": restored,
            "bundle_id": manifest["bundle_id"],
            "scope": "Database restored into a disposable database; file archive verified only",
        }
        (folder / "restore-check.json").write_text(json.dumps(report, indent=2) + "\n")
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["check", "ingest", "backup", "restore-check"])
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()

    def interrupted(signum: int, frame: object) -> None:
        raise RuntimeError("Operation interrupted; inspect service recovery before retrying")

    signal.signal(signal.SIGTERM, interrupted)
    try:
        if args.action == "check":
            result = api("/ready")
            if not result.get("bundle_id"):
                raise ValueError("API is not serving a verified production bundle")
        elif args.action == "ingest":
            result = ingest()
        elif args.action == "backup":
            result = {"backup": str(backup()), "off_host_copy": "Required separately"}
        else:
            if args.backup is None:
                raise ValueError("Use --backup ops-private/backups/<completed-backup>")
            result = restore_check(args.backup)
        print(json.dumps(result, indent=2))
    except (
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        subprocess.CalledProcessError,
        http.client.HTTPException,
    ) as exc:
        parser.exit(1, f"Operation stopped: {exc}\n")


if __name__ == "__main__":
    main()
