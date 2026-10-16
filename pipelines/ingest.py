import argparse
import json
from pathlib import Path

import httpx

from apps.api.app.config import get_settings
from apps.api.app.db import SessionLocal
from ingestion.runner import ADAPTERS, run_ingestion, sources
from pipelines.common import write

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures",
        action="store_true",
        help="Load captured real ATS snapshots, explicitly marked historical",
    )
    parser.add_argument(
        "--export", type=Path, help="Export raw snapshots for DVC instead of writing the database"
    )
    arguments = parser.parse_args()
    if arguments.export:
        payloads = {}
        with httpx.Client(timeout=30) as client:
            for source in sources():
                adapter = ADAPTERS[source.name](source, client)
                payloads[source.name] = (
                    json.loads(Path(f"data/samples/{source.name}.json").read_text())
                    if arguments.fixtures
                    else adapter.fetch()
                )
        write(arguments.export, payloads)
        raise SystemExit(0)
    with SessionLocal() as db:
        run = run_ingestion(db, get_settings().data_dir, arguments.fixtures)
        print({"status": run.status, "counts": run.counts, "errors": run.errors})
        if run.status == "failed":
            raise SystemExit(1)
