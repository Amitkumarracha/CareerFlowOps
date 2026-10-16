# Ingestion pipeline

Reconstructed from the user-provided implementation brief; original file was absent.

fetch -> validate -> archive raw -> normalize -> deduplicate -> transactional upsert. Re-ingestion updates last-seen without duplicating occurrences. A failed board does not discard successful boards. Store run counts and safe errors; do not expose stack traces. CLI supports explicit historical fixture mode. Admin API is protected by an environment token. No automatic silent switch from live to fixtures.
