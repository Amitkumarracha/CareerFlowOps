# MLOps pipeline

Reconstructed from the user-provided implementation brief; original file was absent.

DVC stages ingest, preprocess, build_training_set, train, evaluate, register, export_model. Evaluation uses explicitly labeled relevance judgments, separated from training candidates and never user resumes. Metrics and latencies are computed and stored with dataset hashes, seed and git version. Select using held-out validation; reserve test metrics for final reporting. Registry alias production references the selected run; inference records model identity and local fallback reason.

The final stage exports the selected model with evaluation, training and registry metadata, a file manifest and inference-code/runtime-lock checksums. DVC stores the release; EC2 pulls it before API startup. A configured bundle fails closed on missing files, incompatible code or failed inference. MLflow remains the experiment and alias registry; EC2 serving does not require copying its SQLite backend.
