# Resume pipeline

Reconstructed from the user-provided implementation brief; original file was absent.

Accept only bounded PDF uploads, validate magic bytes, reject encrypted/malformed/image-only files with actionable errors. PyMuPDF extracts text without logging it. Keep text separate from editable structured profile. Extract only evidence-backed email/phone/skills and named sections; leave uncertain name, education or dates empty. Normalize known skill aliases. Store no user-supplied filenames as paths. Candidate can delete resume and profile data.
