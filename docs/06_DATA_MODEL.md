# Data model

Reconstructed from the user-provided implementation brief; original file was absent.

Entities: Company, Job, JobSource, JobSourceOccurrence, Candidate, CandidateProfile, Resume, CandidateSkill, JobSkill, SavedJob, Application, ApplicationHistory, ModelExperiment, ModelDeployment and IngestionRun. Occurrences are unique by source/board/job ID and preserve source_name, source_job_id, source_url, apply_url, source_payload_hash, first_seen_at, last_seen_at, source_posted_at, verified_at and verification_status. Raw JSON is content-addressed separately. Job fingerprints are unique. Candidate data is private and candidate-owned. Applications are unique per candidate/job, with append-only timestamp history.
