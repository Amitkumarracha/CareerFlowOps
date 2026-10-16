import subprocess
from pathlib import Path

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
