from datetime import datetime
from time import perf_counter

import numpy as np

from apps.api.app.config import get_settings
from ml.evaluate.metrics import ranking_metrics
from ml.inference.ranker import rank_jobs
from pipelines.common import ARTIFACTS, read, write


def main() -> None:
    import mlflow
    import torch

    torch.set_num_threads(4)
    dataset = read("data/processed/dataset.json")
    training = read(ARTIFACTS / "training.json")
    mlflow.set_tracking_uri(get_settings().mlflow_tracking_uri)
    results = []
    for run in training["runs"]:
        # Warm up independently from the measured candidate queries.
        rank_jobs(
            {"skills": ["python"]},
            dataset["jobs"],
            algorithm=run["algorithm"],
            weights=training["weights"],
            as_of=datetime.fromisoformat(dataset["as_of"]),
            model_name=str(ARTIFACTS / "sentence-transformer"),
            allow_fallback=False,
        )
        for split in ["validation", "test"]:
            per_query = []
            for query in dataset["queries"]:
                if query["split"] != split:
                    continue
                start = perf_counter()
                ranked = rank_jobs(
                    query["profile"],
                    dataset["jobs"],
                    algorithm=run["algorithm"],
                    weights=training["weights"],
                    as_of=datetime.fromisoformat(dataset["as_of"]),
                    model_name=str(ARTIFACTS / "sentence-transformer"),
                    allow_fallback=False,
                )
                duration = (perf_counter() - start) * 1000
                metrics = ranking_metrics([row["job_id"] for row in ranked], query["relevance"])
                per_query.append(
                    {"query_id": query["id"], **metrics, "inference_latency_ms": duration}
                )
            aggregate = {
                metric: float(np.mean([query[metric] for query in per_query]))
                for metric in [
                    "precision_at_5",
                    "recall_at_5",
                    "ndcg_at_5",
                    "mrr",
                    "inference_latency_ms",
                ]
            }
            results.append(
                {
                    "algorithm": run["algorithm"],
                    "split": split,
                    "metrics": aggregate,
                    "queries": per_query,
                }
            )
            with mlflow.start_run(run_id=run["run_id"]):
                mlflow.log_metrics(
                    {f"{split}_{metric}": value for metric, value in aggregate.items()}
                )
                mlflow.log_dict({"queries": per_query}, f"evaluation/{split}.json")
    best = max(
        (row for row in results if row["split"] == "validation"),
        key=lambda row: (
            row["metrics"]["ndcg_at_5"],
            row["metrics"]["precision_at_5"],
            row["algorithm"],
        ),
    )
    evaluation = {
        "dataset_version": dataset["dataset_version"],
        "labels_description": dataset["labels_description"],
        "selected_algorithm": best["algorithm"],
        "selection_metric": "validation NDCG@5, Precision@5, algorithm tie-break",
        "results": results,
    }
    write(ARTIFACTS / "evaluation.json", evaluation)
    print("Measured all three algorithms on held-out queries. Selected:", best["algorithm"])


if __name__ == "__main__":
    main()
