import os
from pathlib import Path

import joblib
import numpy as np
import yaml

from apps.api.app.config import get_settings
from ml.inference.ranker import embedding_model, job_text, load_weights, tfidf_index
from pipelines.common import ARTIFACTS, git_commit, read, write


def main() -> None:
    import mlflow
    import torch

    os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
    dataset = read("data/processed/dataset.json")
    parameters = yaml.safe_load(Path("params.yaml").read_text())
    np.random.seed(parameters["seed"])
    torch.manual_seed(parameters["seed"])
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    vectorizer, matrix = tfidf_index(tuple(job_text(job) for job in dataset["jobs"]))
    joblib.dump(vectorizer, ARTIFACTS / "tfidf.joblib")
    model = embedding_model(
        parameters["embedding"]["model"],
        local_only=False,
        revision=parameters["embedding"]["revision"],
    )
    model.save(str(ARTIFACTS / "sentence-transformer"))
    vectors = model.encode(
        [job_text(job) for job in dataset["jobs"]],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    np.save(ARTIFACTS / "embeddings.npy", vectors)
    settings = get_settings()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment("careerflowops-ranking")
    runs = []
    for algorithm in ["tfidf", "sentence_transformer", "hybrid"]:
        with mlflow.start_run(run_name=algorithm) as run:
            mlflow.log_params(
                {
                    "algorithm": algorithm,
                    "dataset_version": dataset["dataset_version"],
                    "git_commit": git_commit(),
                    "seed": parameters["seed"],
                    "embedding_model": parameters["embedding"]["model"],
                    "embedding_revision": parameters["embedding"]["revision"],
                    **load_weights(environment=False),
                }
            )
            mlflow.set_tags(
                {
                    "label_provenance": "Illustrative agent judgments; not human validated",
                    "split_policy": "query-disjoint; choose on validation only",
                }
            )
            mlflow.log_artifact("data/samples/labels.json", artifact_path="dataset")
            mlflow.log_artifact(str(ARTIFACTS / "tfidf.joblib"), artifact_path="index")
            runs.append({"algorithm": algorithm, "run_id": run.info.run_id})
    write(
        ARTIFACTS / "training.json",
        {
            "runs": runs,
            "dataset_version": dataset["dataset_version"],
            "seed": parameters["seed"],
            "git_commit": git_commit(),
            "weights": load_weights(environment=False),
            "embedding_model": parameters["embedding"]["model"],
            "embedding_revision": parameters["embedding"]["revision"],
            "corpus_shape": list(matrix.shape),
            "training_note": "Frozen corpus; pretrained transformer; query-disjoint splits.",
        },
    )
    print("Indexed", len(dataset["jobs"]), "jobs; logged", len(runs), "MLflow runs")


if __name__ == "__main__":
    main()
