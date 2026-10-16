import argparse

from apps.api.app.config import get_settings
from apps.api.app.db import SessionLocal
from ingestion.runner import run_ingestion

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures",
        action="store_true",
        help="Load captured real ATS snapshots, explicitly marked historical",
    )
    arguments = parser.parse_args()
    with SessionLocal() as db:
        run = run_ingestion(db, get_settings().data_dir, arguments.fixtures)
        print({"status": run.status, "counts": run.counts, "errors": run.errors})
        if run.status == "failed":
            raise SystemExit(1)
