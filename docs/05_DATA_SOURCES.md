# Data sources

Reconstructed from the user-provided implementation brief; original file was absent.

Use unauthenticated GETs to public Greenhouse, Lever and Ashby endpoints. Board identifiers come from configuration, never arbitrary request URLs. Bound timeouts/retries and honor Retry-After. Live board payload snapshots are fixtures with retrieval URL/time; snapshots are historical, never marked currently verified. Workday/JobSpy are disabled optional connectors until a company-specific policy and schema are reviewed. Social links are leads, not authoritative records.
