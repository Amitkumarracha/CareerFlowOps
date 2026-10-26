import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra.scripts import operations


def snapshot(tmp_path, monkeypatch) -> Path:
    monkeypatch.chdir(tmp_path)
    folder = Path("ops-private/backups/test")
    folder.mkdir(parents=True)
    for name in operations.FILES:
        (folder / name).write_bytes(b"backup data")
    (folder / "manifest.json").write_text(
        json.dumps(
            {
                "files": {name: operations.checksum(folder / name) for name in operations.FILES},
                "counts": {"jobs": 7},
                "bundle_id": "test-bundle",
            }
        )
    )
    return folder


def test_incomplete_or_partial_ingestion_is_a_failed_operation(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(operations, "api", lambda *a, **k: {"status": "partial", "id": "run-1"})
    with pytest.raises(RuntimeError, match="partial.*run-1"):
        operations.ingest()


def test_overlapping_operations_are_rejected(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    with operations.exclusive(), pytest.raises(RuntimeError, match="Another ingestion"):
        with operations.exclusive():
            pytest.fail("Second operation acquired the lock")


def test_live_api_uses_loopback_and_never_places_token_in_url_or_body(monkeypatch) -> None:
    monkeypatch.setattr(operations, "dotenv_values", lambda _: {"ADMIN_API_TOKEN": "private"})
    monkeypatch.setenv("API_PORT", "8123")
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)

    def request(method, path, headers, body):
        assert method == "POST" and path == "/api/admin/ingestion/run"
        assert headers["Authorization"] == "Bearer private"
        assert json.loads(body) == {"mode": "live"}

    def connection(host, port, **kwargs):
        assert host == "127.0.0.1" and port == 8123
        return SimpleNamespace(
            request=request,
            getresponse=lambda: SimpleNamespace(status=200, read=lambda: b'{"status":"succeeded"}'),
            close=lambda: None,
        )

    monkeypatch.setattr(
        operations.http.client,
        "HTTPConnection",
        connection,
    )
    assert operations.api("/api/admin/ingestion/run", live=True)["status"] == "succeeded"


def test_failed_backup_restarts_paused_services_without_completion_manifest(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(operations, "api", lambda _: {"bundle_id": "test"})
    monkeypatch.setattr(operations, "counts", lambda: {"jobs": 7})
    calls = []

    def compose(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(stdout="mlflow\napi\nweb\n")

    monkeypatch.setattr(operations, "compose", compose)

    def fail_archive(*a, **k):
        raise subprocess.CalledProcessError(1, ["tar"])

    monkeypatch.setattr(operations.subprocess, "run", fail_archive)
    with pytest.raises(subprocess.CalledProcessError):
        operations.backup()
    assert calls[1] == ("stop", "web", "api", "mlflow")
    assert calls[-1][-3:] == ("mlflow", "api", "web")
    assert calls[-1][0] == "up"
    assert not list(Path("ops-private/backups").glob("*/manifest.json"))


@pytest.mark.parametrize("fault", ["corrupt", "inventory", "outside"])
def test_restore_rejects_unsafe_backup_before_database_actions(
    monkeypatch, tmp_path, fault
) -> None:
    folder = snapshot(tmp_path, monkeypatch)
    if fault == "corrupt":
        (folder / "runtime.env").write_text("changed")
    elif fault == "inventory":
        (folder / "manifest.json").write_text('{"files":{"../../.env":"hash"}}')
    else:
        folder = tmp_path / "elsewhere"
    monkeypatch.setattr(operations, "compose", lambda *a, **k: pytest.fail("Database was touched"))
    with pytest.raises(ValueError):
        operations.restore_check(folder)


@pytest.mark.parametrize("fault", [None, "restore", "counts"])
def test_restore_drill_only_removes_its_generated_database(monkeypatch, tmp_path, fault) -> None:
    folder = snapshot(tmp_path, monkeypatch)
    calls = []

    def compose(*args, **kwargs):
        calls.append(args)
        if "pg_restore" in args[5] and fault == "restore":
            raise subprocess.CalledProcessError(1, ["pg_restore"])
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(operations, "compose", compose)
    monkeypatch.setattr(operations.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(operations, "counts", lambda _: {"jobs": 8 if fault == "counts" else 7})
    if fault:
        with pytest.raises((RuntimeError, subprocess.CalledProcessError)):
            operations.restore_check(folder)
        assert not (folder / "restore-check.json").exists()
    else:
        assert operations.restore_check(folder)["status"] == "passed"
    database = calls[0][-1]
    assert database.startswith("careerflowops_restore_check_")
    assert calls[-1][-1] == database
    assert "dropdb" in calls[-1][5]
