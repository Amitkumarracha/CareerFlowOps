"""Run a development command against services published on localhost."""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

if __name__ == "__main__":
    environment = {**dotenv_values(".env"), **os.environ}
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    environment["MLFLOW_DISABLE_AGENT_HINT"] = "1"
    url = make_url(environment["DATABASE_URL"])
    if url.host == "postgres":
        environment["DATABASE_URL"] = url.set(host="localhost").render_as_string(
            hide_password=False
        )
    if environment.get("MLFLOW_TRACKING_URI") == "http://mlflow:5000":
        environment["MLFLOW_TRACKING_URI"] = "http://localhost:5000"
    raise SystemExit(subprocess.call(sys.argv[1:], env=environment))
