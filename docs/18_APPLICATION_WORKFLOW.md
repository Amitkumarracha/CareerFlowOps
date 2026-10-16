# Application workflow

Reconstructed from the user-provided implementation brief; original file was absent.

Statuses SAVED, APPLIED, INTERVIEW, OFFER, REJECTED, WITHDRAWN. Record status changes with timestamp and notes. Opening official Apply never claims successful submission. Save is idempotent and application history survives repeated status requests. Only candidate owner may read/update. Never auto-submit or open unvalidated URL schemes.
