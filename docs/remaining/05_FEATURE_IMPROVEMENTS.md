# Feature improvements and technical roadmap

These are **planned improvements**, not implemented features. First finish the Git/DVC/AWS evidence stages in this directory. The existing project is a working single-candidate MVP; expanding it does not require replacing the stack or splitting it into microservices.

Update on 26 October: [production handover](06_PRODUCTION_HANDOVER.md) records implemented backup/isolated-restore commands, optional ingestion/backup timer units, configuration guards and tested alert rules. These portions of milestones C/E now exist. EC2 schedule activation, verified source closure, encrypted off-host retention and delivered notifications are still pending; the detailed milestones below describe the complete target.

## Recommended order

| Priority | Improvement | Why it matters | Completion evidence |
| --- | --- | --- | --- |
| P0 for assessment | Complete hosted CI, S3, ECR, EC2, inference and monitoring evidence | Closes the missing deployment portion of the supplied diagrams | Actual successful release and evidence checklist |
| P0 before sharing | Real accounts and candidate/TPO/admin roles | Current candidate token identifies one candidate | Cross-user isolation and role tests |
| P1 | Scheduled ingestion, freshness and verified job closure | Jobs become stale without continuous revalidation | Timed successful runs, partial-failure handling and closure tests |
| P1 | Larger human-labeled evaluation | Current six-query benchmark cannot substantiate general ranking quality | Reviewed labels, frozen splits and measured held-out comparison |
| P1 | Backups, alerts and a tested release recovery path | A healthy demo is not an operable production service | Off-host backup, restore drill and delivered test alert |
| P1 | Atomic model release staging | Current upgrade process needs a maintenance window | Invalid candidate release leaves the active release untouched |
| P2 | Profile onboarding and source/freshness clarity | Helps users understand what to do and what is unknown | Task-based usability checks and accessible empty/error states |
| P2 | Application reminders and follow-up dates | Turns status tracking into a useful daily workflow | Per-user reminders, opt-out and delivery history |
| P2 | Feedback-driven ranking evaluation | Captures explicit relevance judgments to improve measured results | Versioned feedback schema and evaluated changes without test leakage |
| P2 | Real TPO cohorts and privacy-preserving reporting | Existing global counts are not a multi-college workflow | Cohort-scoped permissions, aggregated reports and privacy tests |
| P2 when needed | Better retrieval and database access | Ranking is bounded to 1,000 recent jobs | Measured latency/recall on a larger corpus |
| P3 | OCR and improved resume evidence extraction | Supports scanned resumes and more varied layouts | Extraction quality/latency tests on consented documents |
| P3 | Additional official employer adapters and verified leads | Expands coverage while preserving provenance | Adapter contract tests and source-policy review |
| Optional | Model/data drift reporting | Helps detect changes after sufficient traffic exists | Defined signals, real reference windows and useful alerts |

Priority reflects current needs, not an accuracy estimate or a promised delivery date. Choose one milestone at a time and verify it before adding the next.

## Milestone A: finish the deployed assessment

**Implement/configure now:** GitHub login and remote publishing, OIDC role/variables, S3 model upload, successful image publish, EC2 instance role, matching release deployment, tunnel or HTTPS, actual predictions and monitoring.

No new application pages are needed for this milestone. The existing System & guide, Model experiments, Source health and For you pages already support demonstrating it.

Acceptance:

- One release SHA links a successful GitHub run, both ECR image digests, `dvc.lock` and the deployed checkout.
- Fresh EC2 model pull and inference succeed. A missing/corrupt/incompatible model fails readiness rather than switching algorithms silently.
- An actual candidate flow persists bookmarks/application history and uses official employer links.
- The evaluator can see real experiment measurements and the stated benchmark limitations.
- Backup and operator notes identify how to restart and recover the deployment.

## Milestone B: make candidate access truly multi-user

**Current gap:** `dependencies/auth.py` maps the candidate token to `local-candidate`. A second student using that token accesses the same profile/applications. The existing bearer-token settings are a demonstration access mechanism.

Implementation scope:

1. Use a maintained authentication integration based on standard identity protocols. Validate tokens on the backend: issuer, audience, signature, expiry and subject. Do not invent password hashing or token cryptography.
2. Add identity/account and organization/cohort membership records using an Alembic migration. Map the authenticated subject to its own candidate record.
3. Enforce candidate ownership in profile/resume/saved/application queries; do not trust a candidate ID sent in a browser header.
4. Grant TPO/admin access through backend-controlled roles. Students cannot select their own admin role.
5. Replace the local-token UI with login/logout/session-expiry flows, keeping the existing workspace-cache clearing behavior.
6. Decide account recovery, retention and deletion behavior before onboarding real users.

Potential pages: `/login`, `/onboarding`, and an admin-only membership screen. Keep candidate navigation separate from authorized TPO tools, while retaining backend permission checks regardless of UI visibility.

Required tests: candidate A cannot read/update/delete B's resume/profile/application; expired/revoked tokens fail; TPO scope cannot cross organizations; logout removes cached private content. Never migrate all users into the existing single shared identity.

External needs: selected identity provider configuration and callback origins. This choice is not required to finish the private single-candidate assessment demo.

## Milestone C: continuous, trustworthy discovery

**Current gap:** live ingestion is operator-triggered. A successfully ingested job is not automatically rechecked for closure.

Implementation scope:

- Start with one host scheduler such as a systemd timer; reuse the existing ingestion entry point. No queue cluster is needed for the first version.
- Add a single-run lock and prevent overlapping ingestion from timer/admin triggers.
- Record per-source last attempt, last success, duration, failure/partial status and next scheduled run.
- Treat a source outage differently from a closed posting. Do not deactivate all jobs when an ATS request times out or returns an invalid response.
- Add explicit per-source closure/staleness evidence, grace/retry rules and timestamps. A canonical job with another verified active source must stay available.
- Preserve source occurrences and saved/application history when a job closes.
- Add stale/closed labels and user filters; allow admin retry and inspectable diagnostics.

Potential UI additions: Source health schedule/status controls and a visible freshness/availability summary on job details. An additional page is unnecessary until the workflow outgrows Source health.

Acceptance: an approved schedule produces persisted successful runs; an outage leaves jobs intact; confirmed closure is reflected without losing provenance; a later reopening/upsert stays idempotent; an alert identifies sustained source failure.

## Milestone D: credible model quality and useful feedback

**Current gap:** the model pipeline works, but six fictional queries with agent-authored labels are too small and unrepresentative to prove production ranking quality.

Implementation scope:

1. Define target users, roles, locations, seniority and what relevance means. Avoid treating sensitive attributes or hiring outcomes as convenient proxy labels.
2. Collect a larger, consented/appropriately de-identified set of candidate queries and public job snapshots. Ask domain reviewers to label relevance and uncertain eligibility; record the rubric and disagreements.
3. Freeze query-disjoint training/validation/test splits before tuning. Keep the test set untouched until final evaluation.
4. Evaluate the existing TF-IDF, semantic and hybrid methods with retrieval metrics, uncertainty, measured latency and representative error examples.
5. Record dataset version, embedding revision, weights, code/runtime version, seeds and hardware context. Show only computed saved metrics.
6. Define promotion criteria before looking at results. A more complex model should be promoted only when the measured tradeoff justifies it.
7. Add explicit candidate feedback such as Relevant / Not relevant / Wrong location / Missing experience evidence. Opening Apply or viewing a card alone is not proof of a good match or successful application.

Potential UI additions: feedback controls on explained recommendations and a richer experiment comparison. A supervised fine-tuning pipeline is optional; it is not a prerequisite to collecting better labels.

Acceptance: label provenance and split membership are reviewable, no candidate/test leakage, metrics reproduce, errors are analyzed and changes beat an appropriate baseline on the intended use case. Publish uncertainty and sample limits alongside scores.

External needs: human review time and a privacy-preserving data/consent policy. Do not upload private resumes to the public samples or default DVC remote.

## Milestone E: reliable operations and releases

Implementation scope:

- Automate a scoped encrypted off-host backup with retention, and regularly restore to an isolated environment.
- Add actionable alerts for API failure, sustained source failure, disk exhaustion and repeated model-load errors. The current Prometheus/Grafana setup has dashboards, not a completed notification workflow.
- Stage each downloaded release in its own directory; validate it before atomically switching the active read-only mount. Preserve the previous release and check database migration compatibility.
- Make deployment promotion explicit. An optional GitHub Environment approval can gate a future automated deployment; CI and ECR publishing already exist, while EC2 deployment is currently manual.
- Add measured resource limits and load checks before raising concurrency or candidate volume.
- Document model/image/dataset identity for each deployment and make recovery a rehearsed operation.

Acceptance: a failed candidate model cannot alter the active artifact files; a delivered test alert reaches its configured operator; an off-host backup restores successfully; a previous compatible release can be restored with the documented process. Do not advertise zero downtime or automatic schema rollback until tested.

External needs: backup destination and operator notification channel. Do not reuse the model-serving read-only S3 role for broad backup/delete privileges.

## Milestone F: candidate workflow improvements

### Onboarding and profile clarity

- Show actionable next steps based on actual profile/resume state, without inventing a numerical completion or employability score.
- Highlight extraction evidence and fields needing review; preserve manual edits when the user chooses how to merge a new resume.
- Show posting verification/freshness separately from content-match score.
- Explain unknown experience, work authorization, salary or location instead of treating missing evidence as approval.
- Add unsaved-edit protection and measured keyboard/screen-reader usability checks.

### Reminders and follow-ups

- Add optional application due/follow-up dates and timezone-aware reminders.
- Allow opt-in email/calendar export only after identity and ownership are implemented.
- Store delivery status and allow cancellation; duplicate scheduling must not send repeated messages.
- Continue opening the official employer page for submission. Do not implement unattended bulk applications.

Potential page: `/reminders` if the reminder list warrants its own navigation; otherwise add a panel/filter in Applications. Do not add an empty page merely for page count.

### Saved searches and notification preferences

- Save validated search filters to the authenticated candidate, rather than only URL state.
- Notify only for newly verified matching jobs; preserve last-notified identity to avoid repeated alerts.
- Add explicit frequency/quiet-hour/disable preferences, source provenance and direct official URLs.

Dependencies: real user identity, a scheduler and a chosen notification provider. No new paid API is necessary for the current manual workflow.

## Milestone G: TPO cohorts and reporting

**Current gap:** the TPO dashboard uses real aggregate data but lacks a proper institution/cohort model and scoped TPO identities.

Implementation scope:

- Add institution, cohort, graduation year and consent/membership records.
- Scope all aggregate queries to the authorized organization/cohort; document minimum group sizes and suppression for potentially identifying small groups.
- Keep student resume text and personal contact data out of default aggregate responses.
- Add cohort filters, clearly defined placement-funnel denominators and optional aggregate CSV export.
- Separate “potential skill match” from verified employer eligibility. Expose unknowns instead of implying a student is guaranteed eligible.

Potential page: a TPO-only Cohorts page after the underlying role and schema changes exist. Avoid displaying global single-candidate statistics as evidence of a real campus rollout.

Acceptance: no cross-cohort leaks, counts reconcile with persisted states, exports obey the same scope, and unknown eligibility is disclosed.

## Milestone H: scale only after measuring

Current limits: recommendations consider at most 1,000 recent active jobs; TPO matching breakdown uses at most 100 jobs/500 profiles; duplicate diagnostics use the most recent 200 jobs; resume/saved/application lists have bounded limits.

Improve in this order:

1. Measure query plans, repeated SQL access, memory and end-to-end latency on a representative larger corpus.
2. Add required database indexes/eager loading and a bounded two-stage retrieval path before scoring everything.
3. Reuse versioned job embeddings and invalidate them when source content/model revision changes.
4. Add true paginated candidate/admin lists where the current caps become user-visible.
5. Evaluate a PostgreSQL vector extension only if measured retrieval needs justify it; retain a baseline and test recall/latency tradeoffs.

Acceptance: representative load measurements meet defined latency/resource goals without truncating data silently or weakening per-user authorization. Kafka, Kubernetes, microservices and a dedicated vector database are not required for the present MVP.

## Later optional work

| Extension | What must be decided first | Validation needed |
| --- | --- | --- |
| OCR | Supported document languages, retention and CPU cost | Consented scanned-PDF extraction quality and resource limits |
| Additional ATS/company adapters | Official endpoint availability, source policies and rate limits | Contract fixtures, live bounded check, provenance and idempotency |
| User-submitted social leads | Verification against official employer sources | Unverified labeling, URL validation and manual review |
| Drift reports | Stable reference data, real traffic and useful thresholds | Genuine measured distribution change; no fabricated drift charts |
| Shared remote MLflow | Persistent tracking backend/artifacts, access control and backups | Runs/aliases survive host replacement and can be audited |
| Automated retraining | Data-quality gates, real labels and promotion policy | Evaluation failure blocks promotion; tested fallback to prior release |

## Commands for starting a future feature

These are existing project commands, not claims that the feature is already implemented:

```bash
git switch -c feat/your-feature-name
# Implement the scoped feature and meaningful tests; update its docs.
make test
make lint
npm --prefix apps/web run build
git diff --check
git status --short
```

If an actual database model changes, generate/review an Alembic migration and test it on a separate database before deployment. Do not run placeholder “train production”, “enable OCR” or “create users” commands: those features need implementation first. Record the chosen milestone, schema/API/UI changes, external configuration, tests and acceptance evidence in each pull request.
