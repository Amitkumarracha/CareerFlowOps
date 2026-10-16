import json
import os
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def load_registered(tracking_uri: str, model_uri: str) -> Any:
    os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "5")
    os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "1")
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    return mlflow.pyfunc.load_model(model_uri)


def predict_registered(
    tracking_uri: str, model_uri: str, profile: dict, jobs: list[dict]
) -> list[dict]:
    import pandas as pd

    model = load_registered(tracking_uri, model_uri)
    return json.loads(
        model.predict(
            pd.DataFrame([{"profile": json.dumps(profile), "jobs": json.dumps(jobs)}])
        ).iloc[0]["predictions"]
    )
