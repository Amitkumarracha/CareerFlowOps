"""Load a trusted, DVC-versioned model release without a live tracking server."""

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from ml.inference.ranker import rank_jobs

ROOT = Path(__file__).resolve().parents[2]
CODE_FILES = ("ml/inference/ranker.py", "ml/features/skills.py", "requirements-runtime.lock")
METADATA_FILES = ("model.json", "evaluation.json", "registry.json", "training.json")


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_metadata(metadata: dict[str, Any]) -> None:
    config, evaluation, registry, training = (metadata[name] for name in METADATA_FILES)
    if config["algorithm"] not in {"tfidf", "sentence_transformer", "hybrid"}:
        raise ValueError("Unsupported release algorithm")
    selected = next(run for run in training["runs"] if run["algorithm"] == config["algorithm"])
    if (
        evaluation["selected_algorithm"] != config["algorithm"]
        or registry["run_id"] != selected["run_id"]
        or registry["dataset_version"] != training["dataset_version"]
        or evaluation["dataset_version"] != training["dataset_version"]
        or config["weights"] != training["weights"]
        or not config["model_version"]
    ):
        raise ValueError("Release metadata does not identify the selected evaluated model")


@dataclass
class ModelBundle:
    path: Path
    bundle_id: str
    metadata: dict[str, Any]
    vectorizer: Any

    @property
    def config(self) -> dict:
        return self.metadata["model.json"]

    def predict(self, profile: dict, jobs: list[dict]) -> list[dict]:
        return rank_jobs(
            profile,
            jobs,
            algorithm=self.config["algorithm"],
            weights=self.config["weights"],
            model_version=self.config["model_version"],
            fitted_vectorizer=self.vectorizer,
            model_name=str(self.path / "sentence-transformer"),
            allow_fallback=False,
        )


@lru_cache(maxsize=1)
def load_bundle(path: str) -> ModelBundle:
    """Verify before deserializing; cache for this process's read-only release mount.

    Checksums detect corruption, not malicious publishers. Only pull artifacts from
    the project's trusted remote and a reviewed Git/DVC revision.
    """
    try:
        folder = Path(path).resolve(strict=True)
        manifest_path = folder / "manifest.json"
        if manifest_path.is_symlink():
            raise ValueError("Symlink manifest")
        manifest = json.loads(manifest_path.read_text())
        if manifest["schema_version"] != 1:
            raise ValueError("Unsupported bundle schema")
        expected = manifest["files"]
        if not set((*METADATA_FILES, "tfidf.joblib")).issubset(expected):
            raise ValueError("Incomplete model bundle")
        actual = set()
        for item in folder.rglob("*"):
            if item.is_symlink():
                raise ValueError("Symlinks are not supported in model bundles")
            if item.is_file() and item != manifest_path:
                actual.add(item.relative_to(folder).as_posix())
        if actual != set(expected):
            raise ValueError("Bundle file inventory mismatch")
        for relative, digest in expected.items():
            target = folder / relative
            if not target.resolve().is_relative_to(folder) or checksum(target) != digest:
                raise ValueError("Bundle checksum mismatch")
        code = manifest["code"]
        if set(code) != set(CODE_FILES) or any(
            checksum(ROOT / name) != digest for name, digest in code.items()
        ):
            raise ValueError("Model release requires a different inference image")
        metadata = {name: json.loads((folder / name).read_text()) for name in METADATA_FILES}
        validate_metadata(metadata)
        if metadata["model.json"]["algorithm"] != "tfidf" and not any(
            name.startswith("sentence-transformer/") for name in expected
        ):
            raise ValueError("Missing semantic model")
        bundle = ModelBundle(
            folder, checksum(manifest_path), metadata, joblib.load(folder / "tfidf.joblib")
        )
        # A real prediction exercises deserialization and the selected inference path.
        prediction = bundle.predict(
            {"skills": ["python"], "summary": "Python software engineer"},
            [{"id": "readiness-probe", "title": "Software engineer", "description": "Python"}],
        )
        if len(prediction) != 1 or not prediction[0]["explanation"]:
            raise ValueError("Model inference probe failed")
        return bundle
    except Exception as exc:
        raise RuntimeError("Production model bundle failed validation or inference") from exc
