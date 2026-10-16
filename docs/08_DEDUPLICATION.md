# Deduplication

Reconstructed from the user-provided implementation brief; original file was absent.

Baseline fingerprint: casefolded, whitespace/punctuation-normalized company + title + location. Exact duplicates share a canonical job and retain all occurrences. Conservative behavior avoids merging distinct requisitions from the same board solely on a similar title. Fuzzy similarity is diagnostic only until labeled merge evidence exists. Admin exposes fingerprints and occurrence counts. Upsert conflicts must be handled transactionally.

Existing source IDs retain their canonical job identity when titles or locations change. If an edit collides with another existing canonical fingerprint, retain both jobs and their application histories for manual review; fuzzy diagnostics expose the pair. Newly seen source IDs still use exact fingerprint deduplication.
