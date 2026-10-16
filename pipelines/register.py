import json
import shutil
import tempfile
from pathlib import Path

from apps.api.app.config import get_settings
from apps.api.app.db import SessionLocal
from apps.api.app.models.entities import ModelDeployment, ModelExperiment
from ml.registry.pyfunc_model import RankingModel
from pipelines.common import ARTIFACTS, read, write


def main() -> None:
    import mlflow
    import pandas as pd
    from mlflow.models import ModelSignature
    from mlflow.tracking import MlflowClient
    from mlflow.types import ColSpec, Schema
    from sqlalchemy import select

    settings = get_settings()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    evaluation = read(ARTIFACTS / "evaluation.json")
    training = read(ARTIFACTS / "training.json")
    algorithm = evaluation["selected_algorithm"]
    run = next(run for run in training["runs"] if run["algorithm"] == algorithm)
    config = {
        "algorithm": algorithm,
        "weights": training["weights"],
        "model_version": training["dataset_version"][:12] + "-" + training["git_commit"][:8],
    }
    write(ARTIFACTS / "model.json", config)
    client = MlflowClient()
    with tempfile.TemporaryDirectory() as folder:
        code = Path(folder) / "ml"
        shutil.copytree("ml", code, ignore=shutil.ignore_patterns("artifacts", "__pycache__"))
        dataset = read("data/processed/dataset.json")
        example = pd.DataFrame(
            [
                {
                    "profile": json.dumps({"skills": ["python"]}),
                    "jobs": json.dumps(dataset["jobs"][:1]),
                }
            ]
        )
        with mlflow.start_run(run_id=run["run_id"]):
            info = mlflow.pyfunc.log_model(
                name="ranker",
                python_model=RankingModel(),
                artifacts={
                    "config": str(ARTIFACTS / "model.json"),
                    "tfidf": str(ARTIFACTS / "tfidf.joblib"),
                    "semantic": str(ARTIFACTS / "sentence-transformer"),
                },
                code_paths=[str(code)],
                input_example=example,
                signature=ModelSignature(
                    inputs=Schema([ColSpec("string", "profile"), ColSpec("string", "jobs")]),
                    outputs=Schema([ColSpec("string", "predictions")]),
                ),
                pip_requirements=[
                    "mlflow==" + mlflow.__version__,
                    "pandas",
                    "scikit-learn",
                    "sentence-transformers",
                    "torch",
                    "pyyaml",
                    "joblib",
                ],
            )
            mlflow.log_artifact(str(ARTIFACTS / "evaluation.json"), artifact_path="evaluation")
    version = mlflow.register_model(info.model_uri, settings.mlflow_model_name)
    client.set_registered_model_alias(
        settings.mlflow_model_name, settings.mlflow_model_alias, version.version
    )
    registry = {
        "model_name": settings.mlflow_model_name,
        "version": str(version.version),
        "alias": settings.mlflow_model_alias,
        "run_id": run["run_id"],
        "model_uri": f"models:/{settings.mlflow_model_name}@{settings.mlflow_model_alias}",
        "dataset_version": training["dataset_version"],
    }
    write(ARTIFACTS / "registry.json", registry)
    # Registration is an external side effect; database records mirror the real run and version.
    with SessionLocal() as db:
        for experiment in training["runs"]:
            record = db.scalar(
                select(ModelExperiment).where(ModelExperiment.run_id == experiment["run_id"])
            )
            if record is None:
                db.add(
                    ModelExperiment(
                        run_id=experiment["run_id"],
                        algorithm=experiment["algorithm"],
                        dataset_version=training["dataset_version"],
                        metrics={
                            row["split"]: row["metrics"]
                            for row in evaluation["results"]
                            if row["algorithm"] == experiment["algorithm"]
                        },
                        artifact_path=str(ARTIFACTS / "evaluation.json"),
                    )
                )
        db.add(
            ModelDeployment(
                model_name=settings.mlflow_model_name,
                version=str(version.version),
                alias=settings.mlflow_model_alias,
                run_id=run["run_id"],
            )
        )
        db.commit()
    loaded = mlflow.pyfunc.load_model(registry["model_uri"])
    prediction = json.loads(loaded.predict(example).iloc[0]["predictions"])
    assert prediction and "explanation" in prediction[0]
    print("Registered and loaded", registry["model_uri"], "version", version.version)


if __name__ == "__main__":
    main()
