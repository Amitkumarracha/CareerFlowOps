import json
from typing import Any

import joblib
import mlflow.pyfunc
import pandas as pd

from ml.inference.ranker import rank_jobs


class RankingModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context: Any) -> None:
        with open(context.artifacts["config"]) as handle:
            self.config = json.load(handle)
        self.vectorizer = joblib.load(context.artifacts["tfidf"])
        self.semantic_path = context.artifacts["semantic"]

    def predict(
        self, context: Any, model_input: pd.DataFrame, params: dict | None = None
    ) -> pd.DataFrame:
        outputs = []
        for _, row in model_input.iterrows():
            predictions = rank_jobs(
                json.loads(row["profile"]),
                json.loads(row["jobs"]),
                algorithm=self.config["algorithm"],
                weights=self.config["weights"],
                model_name=self.semantic_path,
                allow_fallback=False,
                model_version=self.config["model_version"],
                fitted_vectorizer=self.vectorizer,
            )
            outputs.append({"predictions": json.dumps(predictions)})
        return pd.DataFrame(outputs)
