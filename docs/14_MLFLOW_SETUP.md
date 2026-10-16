# MLflow setup

Reconstructed from the user-provided implementation brief; original file was absent.

Run MLflow on port 5000 with persistent backend and artifacts; keep it private. Log each algorithm, parameters, dataset version, git commit, seed, actual metrics and artifacts. Register careerflowops-ranker, production alias. API may load models:/careerflowops-ranker@production; local deterministic fallback is explicit in responses. Dashboard reads saved evaluation artifacts only.
