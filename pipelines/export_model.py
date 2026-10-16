"""Export only the evaluated production model and its audit metadata for DVC."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from ml.inference.bundle import (
    CODE_FILES,
    METADATA_FILES,
    ROOT,
    checksum,
    load_bundle,
    validate_metadata,
)
from pipelines.common import ARTIFACTS, read, write


def export_bundle(artifacts: Path, output: Path) -> None:
    metadata = {name: read(artifacts / name) for name in METADATA_FILES}
    validate_metadata(metadata)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not (output / "manifest.json").is_file():
        raise ValueError("Refusing to replace a directory without a model manifest")
    with tempfile.TemporaryDirectory(prefix=".release-", dir=output.parent) as temporary:
        staging = Path(temporary) / "bundle"
        staging.mkdir()
        for name in (*METADATA_FILES, "tfidf.joblib"):
            shutil.copy2(artifacts / name, staging / name)
        if metadata["model.json"]["algorithm"] != "tfidf":
            shutil.copytree(artifacts / "sentence-transformer", staging / "sentence-transformer")
        write(
            staging / "manifest.json",
            {
                "schema_version": 1,
                "code": {name: checksum(ROOT / name) for name in CODE_FILES},
                "files": {
                    item.relative_to(staging).as_posix(): checksum(item)
                    for item in sorted(staging.rglob("*"))
                    if item.is_file()
                },
            },
        )
        load_bundle.cache_clear()
        load_bundle(str(staging))
        # Preserve the previous release until the candidate passes validation.
        backup = Path(temporary) / "previous"
        if output.exists():
            output.rename(backup)
        try:
            staging.rename(output)
        except OSError:
            if backup.exists():
                backup.rename(output)
            raise
    load_bundle.cache_clear()
    bundle = load_bundle(str(output))
    print(json.dumps({"bundle_id": bundle.bundle_id, **bundle.config}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validate", type=Path, help="Validate an existing release without writing"
    )
    args = parser.parse_args()
    if args.validate:
        bundle = load_bundle(str(args.validate))
        print(json.dumps({"bundle_id": bundle.bundle_id, **bundle.config}))
    else:
        export_bundle(ARTIFACTS, ARTIFACTS / "production")


if __name__ == "__main__":
    main()
