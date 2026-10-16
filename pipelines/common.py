import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ARTIFACTS = Path("ml/artifacts")


def read(path: str | Path) -> Any:
    return json.loads(Path(path).read_text())


def write(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False))


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "uncommitted"
