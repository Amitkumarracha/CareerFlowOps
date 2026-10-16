# Matching model

Reconstructed from the user-provided implementation brief; original file was absent.

A: TF-IDF cosine; B: all-MiniLM-L6-v2 cosine; C: hybrid semantic/skills/eligibility/location/freshness. Default weights 0.40/0.30/0.15/0.08/0.07 in params.yaml and optional environment overrides; validate nonnegative weights sum to one. Unknown eligibility is explicitly unknown and scores neutrally, not as a proven match. Scores expose all components, matched/missing skills and explanation. TF-IDF fallback must be visibly identified; do not call it a transformer.
