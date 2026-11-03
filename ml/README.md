# NexAbility ML

## Architecture

- `nexability_ml/parser.py` extracts text from PDF/DOCX bytes without OCR.
- `normalizer.py` extracts candidate fields and heading/bullet job requirements.
- `groq_extraction.py` implements optional structured extraction and privacy filters.
- `schemas.py` validates résumé, job-enrichment, and persisted job-profile data.
- `pipeline.py` composes parsing, normalization, optional Groq, chunking, and the
  existing matching implementation.
- `api_client.py` retrieves metadata, bytes, and pending work only from the backend
  internal ML routes. ML has no Supabase client or credentials.
- `resume_processing.py` and `job_processing.py` validate and persist one profile
  against its exact source document.
- `document_dispatcher.py` dispatches both queue types independently and isolates
  per-document failures.
- `backend/app/repositories/*_profile_repository.py` claim work and persist profiles.
- `backend/app/models/*_profile.py` and the corresponding Alembic revisions define
  profile storage.

The existing pipeline supplies E5 embedding generation, chunking, and professional
matching. Those remain non-persistent; no pgvector or match table is implemented.
Professional evidence scoring remains unchanged, and there is no combined score.

## Extraction and privacy

Groq extraction is disabled by default. It runs only when the process setting
`NEXABILITY_LLM_EXTRACTION=true` is explicitly enabled. With it unset or false, both
document types use rule-based extraction.

Résumé Groq input is limited to allow-listed professional sections. Contact details,
URLs, and phone numbers are redacted; accessibility/accommodation and indirect
accommodation cues fail closed to rule-based extraction with
`extraction_mode="rule_based"` and `llm_skipped_reason="privacy_filter"`. Extracted
identity fields remain null because no trusted backend identity source is connected.

Job Groq input contains only parser-derived professional requirement strings, never the
source job document. Contact details and accessibility/accommodation cues in any
requirement fail closed. Groq output cannot replace, add, remove, combine, or alter the
parser-derived requirement list. Candidate accessibility inputs are never sent to Groq,
stored in job profiles, or included in employer-facing payloads.

The extraction model defaults to `openai/gpt-oss-120b`; `GROQ_API_KEY` is only needed
when Groq is explicitly enabled and approved. `EMBEDDING_MODEL` defaults to
`intfloat/e5-base-v2`; `placeholder` selects the local non-semantic fallback. E5 and
its tokenizer require the optional `embeddings` dependencies.

## Backend document processing

The standalone backend worker polls `GET /api/v1/internal/ml/pending-documents`. It
consumes `active_resumes` and `pending_job_documents`, retrieves metadata and document
bytes from existing backend internal routes, and dispatches each item by type. The
backend remains the only component that accesses Supabase Storage. Existing upload
routes do not start the worker.

Only the active résumé is processed, matching the existing queue policy. Inactive
historical résumé versions are not queued unless they later become active. Job
documents continue to appear in the pending endpoint after success; a persisted
`SUCCEEDED` profile causes later polls to skip them. Failures are stored as content-free
error codes and retried with backoff.

Résumé profiles are stored in `candidate_resume_profiles`, uniquely keyed by
`resume_id`; candidate ownership is derived through the `resumes` row. Job profiles are
stored in `job_document_profiles`, uniquely keyed by `document_id`; employer ownership
is derived through `job_documents`. Both store JSONB profiles, status, attempts,
retry timing, extraction mode, error code, and last-success provider/model/schema
metadata. Failed re-extraction keeps the last successful JSON and `last_success_*`
metadata but sets status to `FAILED`. Readers must return JSON only for `SUCCEEDED`
rows. Original binaries remain in Supabase; the profile tables do not store source
text, chunks, or embeddings.

Before operation, the candidate and job profile migrations require review and
application to an approved development database. Alembic's `env.py` import list must
register `candidate_resume_profile` and `job_document_profile`; do not change existing
backend configuration to do so without approval. The existing
`backend/alembic/env.py` also prints the full `settings.DATABASE_URL`; do not invoke it
until that output is redacted or an approved safe migration environment is used. There
are no profile HTTP retrieval endpoints yet; current retrieval is through the backend
repository getters. The worker requires process
environment values `DATABASE_URL`, `NEXABILITY_BACKEND_URL`, and
`INTERNAL_ML_API_KEY`, and disables dotenv loading. `NEXABILITY_LLM_EXTRACTION` defaults
to false. It supports `--once`, `--status <resume-uuid>` (status only, no profile
contents), and `--reprocess <resume-uuid>`.

The worker database role needs `SELECT` on `resumes` and `job_documents`, and
`SELECT`, `INSERT`, and `UPDATE` on `candidate_resume_profiles` and
`job_document_profiles`. The repositories use PostgreSQL advisory transaction locks
and database-side `now()` for stale claims. This concurrency guarantee is **NOT
VERIFIED** until tested on PostgreSQL. SQLite tests do not prove PostgreSQL behavior.

Install the ML package from the backend directory and run the worker only after the
development database and backend are approved and configured:

```powershell
pip install -e ..\ml
python -m app.workers.resume_extraction_worker
```

No live Groq call is made by unit tests; use mocked clients and synthetic documents.
OCR is not supported.

## Accessibility and future matching

`backend/app/repositories/accessibility_profile_repository.py` reads the existing
`accommodation_preferences` columns (`category`, `preference`, `details`, `is_active`)
and `employer_accessibility_capabilities` columns (`category`, `capability`, `status`,
`details`) with SELECT queries only. Its database role must be SELECT-only for those
tables. No profile-completion column exists, so an unmatched need stays `unknown`.
Candidate accessibility details are internal only and must never be exposed to an
employer.

Matching remains audit-only. After both profile retrieval paths are verified, the
proposed `job_matches` table is unique on `(resume_id, job_document_id)` and stores
separate `professional_match` and `accessibility_match` JSON, input schema versions,
status, and `computed_at`. It has no combined score. A future match step retrieves one
succeeded candidate profile and all succeeded job profiles, then evaluates each job
independently using the existing professional scoring formula; accessibility is never
part of that score.

## Validation and tests

From `ml`:

```powershell
pytest .\tests
```

From `backend`:

```powershell
pytest .\tests\unit\test_candidate_resume_profile_repository.py .\tests\unit\test_job_document_profile_repository.py .\tests\unit\test_accessibility_profile_repository.py
```
