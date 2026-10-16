"""Create local runtime directories and an ignored environment without exposing secrets."""

import secrets
from pathlib import Path


def main() -> None:
    for folder in ["data/raw", "data/interim", "data/processed", "ml/artifacts", "mlflow-data"]:
        Path(folder).mkdir(parents=True, exist_ok=True)
    target = Path(".env")
    if target.exists():
        print("Kept existing .env; runtime directories are ready.")
        return
    password = secrets.token_hex(24)
    content = Path(".env.example").read_text().replace("CHANGE_ME", password)
    for key in ["CANDIDATE_API_TOKEN", "ADMIN_API_TOKEN", "GRAFANA_ADMIN_PASSWORD"]:
        content = content.replace(key + "=\n", key + "=" + secrets.token_urlsafe(32) + "\n")
    target.write_text(content)
    target.chmod(0o600)
    print("Created ignored .env with distinct generated credentials.")


if __name__ == "__main__":
    main()
