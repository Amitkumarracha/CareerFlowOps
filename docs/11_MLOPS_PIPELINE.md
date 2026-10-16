# MLOps pipeline

Reconstructed from the user-provided implementation brief; original file was absent.

DVC stages ingest, preprocess, build_training_set, train, evaluate, register. Evaluation uses explicitly labeled relevance judgments, separated from training candidates and never user resumes. Metrics and latencies are computed and stored with dataset hashes, seed and git version. Select using held-out validation; reserve test metrics for final reporting. Registry alias production references the selected run; inference records model identity and local fallback reason.
