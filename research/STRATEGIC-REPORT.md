# Internal strategic report

Run `python strategic_report.py bundle.json` from the repository root.
The command writes an internal report to standard output. Keep both the bundle
and the resulting report in analyst-controlled storage.

The bundle has these fields.

| Field | Contents |
| --- | --- |
| `company` | Nonempty issuer identifier or display name |
| `as_of` | Timezone-aware ISO 8601 cutoff |
| `documents` | Objects with `id`, `origin`, `available_at`, `retrieved_at`, `content_base64`, `sha256`, and `license`. Eligible license values are `research_only` and `commercial`. |
| `citations` | Objects with `element`, `document_id`, `start`, `end`, `excerpt`, and `stance`. Offsets are zero-based byte offsets with an exclusive end. The UTF-8 excerpt must match the bytes exactly. |
| `assessments` | Objects with `element`, `status`, `score`, and `rationale`. Use decimal strings for assessed scores and null for unknown scores. |
| `risk_flags` | Declared values from `insolvency`, `fraud`, `continuity`, and `regulatory_shutdown`. |

The report accounts for all 50 elements, includes cited sources and byte
ranges, and records evidence conflicts. Scored elements require a supporting
citation and a rationale. Missing observations remain unknown and still count
against coverage. The existing scoring threshold controls whether an index
is available. Source bytes and verbatim excerpts stay in the input bundle.

The workflow checks byte integrity, declared availability and license
eligibility. Publisher identity, license rights, factual support for scores
and independent risk review still need verification. The existing publication
gate keeps every report internal.

QA passed for the complete CLI flow, partial coverage, UTF-8 byte offsets,
changed excerpts, hash mismatch, future evidence, restricted sources,
context-only citations and references to missing assessments. Tests used
synthetic scoring and evidence. All 75 Python tests passed.

## Sealed snapshot submission

A backend worker can use `assessment_submission.submit_assessment` with a
psycopg-compatible cursor. Supply the original audited bundle and a request
with a stable UUID `request_id`, the registered UUID `company_id`,
`methodology_version`, `model_version` and `sources`. The source mapping must
come from the trusted ingestion registry and be keyed by cited document ID.
Each entry contains `id`, `url`, `content_sha256`, `available_at`,
`retrieved_at` and `license_status`. The worker verifies these values against
the audited sources before submitting. A research seal marks snapshot
immutability and leaves the separate publication gate closed.

To inspect the payload without writing to a database, run
`python assessment_submission.py bundle.json request.json`. The worker
function sends typed parameters and uses the caller's read-committed
transaction. Keep retries on the same request UUID. The adapter checks the
supplied registry export. Access to the trusted source registry and a worker
identity that can assume `stratiq_assessor` are deployment prerequisites.

QA committed a generated payload using the migrated PostgreSQL database and
verified that the evaluator could read all 50 assessments only after the
snapshot was sealed. Adapter tests also checked metadata mismatches,
insufficient coverage, deterministic input order and parameter binding.
The Python suite passed 79 tests. Hosted worker credentials and live
integration remain outstanding.
