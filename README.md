# StratIQ research foundation 0.1
Run `python -m unittest -v` with Python 3.10+. No dependencies or credentials.

Experimental equal-weight 50-element registry; positive means favorable to the company. Unknown is not neutral. NA requires evidence. Coverage threshold 80% is provisional. Core is not a return forecast. No actual company assessments included.

## Research protocol
Freeze universe, source vintages, outcome definitions, model versions, prompts, weights and experiment configuration before evaluation. Preserve publication and retrieval timestamps, original documents and revisions, historical identifiers, delisting returns and corporate actions. Keep outcome data isolated from assessment workers. Historical LLM hindsight cannot be fully eliminated; compare deterministic baselines and prospective frozen scores. Use chronological rolling splits, purge overlapping labels, reserve final holdout, account for clustered observations and multiple testing. Report null and negative findings, costs, uncertainty and coverage. Compare matched universes and horizons against financial-only baselines, Piotroski, distress models and factor exposures as appropriate. Do not optimize Core for stock returns; separate valuation, risk and alpha. Start with 25–50 companies; scale only after reliability and data integrity gates.

## Next implementation
Database migrations with deny-by-default access, immutable evidence snapshots and experiment registry; historical data licensing and ingestion; rubric anchors per element, independent human labels, critical risk flags, source independence and citation verification; quantitative benchmark calculations; actual backtest runner and statistical inference; authenticated API and UI. Current code is a local foundation, not a deployed application. Piotroski helper aggregates precomputed signals only. No external data or live database modifications.

## v0.2 research mechanics
`quant.py` implements original public-manufacturing Altman Z and account-based Piotroski signals (annual inputs, consistent units, beginning/average assets as specified; issuance must be supplied). `backtest.py` compares matched cross-sectional Spearman rank correlations by exact observation and outcome dates. It does not simulate portfolios, establish significance or verify feature provenance. `schema.sql` is a draft PostgreSQL server-only schema with RLS and evidence cutoff trigger; it has not been executed or validated against PostgreSQL. Source and snapshot immutability, publication-time provenance, experiment freeze enforcement, role separation, complete rubrics and ingestion remain required before production. All tests use synthetic data. Run `python -m unittest -v`.

## v0.3 calibration prototype
`calibration.py` selects predeclared nonnegative weight vectors on mature historical labels and evaluates them on subsequent disjoint snapshot-date windows. Constant predictions receive zero rank signal. Candidate zero is the baseline. Run each outcome/horizon separately; no final holdout enforcement, inference, feature provenance verification or portfolio simulation yet. This is a descriptive research tool, not a validated predictor. `quant.py` adds DuPont, ROIC, EVA and cash-flow accrual ratio. All tests are synthetic. No live database changes or external data acquisition.

## v0.4 hardening
See QA.md for mandatory release policy, changes and blockers. Baseline-0.4 rejects N/A, fixes coverage at 80% and requires half of each framework. Calibration requires per-feature availability timestamps.

## v0.5 — analyst rubric draft
`rubrics.py` defines all 50 criteria, adverse/favorable anchors and preferred evidence; intermediate anchors are shared. Quarter-point distinctions remain provisional and require analyst agreement testing. Overlap groups identify candidates for ablation, not automatic discounts. The separate publication gate blocks reports with declared critical risk flags; it does not detect risks or authenticate sources. N/A remains disabled. Run `python -m unittest discover -v` from this directory. See QA.md for release limitations.

## v0.6 database hardening
Fresh-install schema only (not an upgrade migration). Append-only triggers, registry FK, deferred scored-evidence check, source-license gate and additional access restrictions. Runtime PostgreSQL verification, worker grants, snapshot sealing and audit logging are pending. See QA.md.

## v0.7
Added experimental Beneish eight-index score, earnings and FCF yields, Magic Formula component ratios and interest coverage. New inputs use finite bounded Python int/float values; the bound is provisional. Negative earnings/FCF are retained, nonpositive denominators suppressed. No rankings or investment recommendations. Added draft snapshot sealing with full registry and evidence checks; requires read committed and parent locking. Not runtime verified. See QA.md for blockers.

## v0.8 hardening
Shared validation, mandatory declared comparison feature timestamps, conservative calendar horizon separation in calibration, explicit insufficient-testing status, fail-closed publication, and SQL seal coverage gates. Internal scores are not verified. See QA.md and QA-test-log.txt. Not production ready.

### v0.9 local evidence integrity
`evidence.audit` checks SHA-256 against supplied bytes and exact byte-span citations, validates declared dates and license eligibility, groups exact mirrors and declared common origins, and reports declared opposing stances. It is a standalone prototype, not a trusted ingestion service. It never authorizes publication. No source authenticity or historical availability is proven by a self-supplied digest or timestamp. See QA.md for blockers.

## Database migration history

The files in `supabase/migrations/` are the six migrations recovered from the
live StratIQ project `aobhcuvawfmxnbkyftyl`. They are authoritative for that
project. The root `schema.sql` is retained as the v0.9 fresh-install draft for
historical reference and its original static tests. Use the migration history
to reconstruct an isolated database. See [v0.10 QA](qa/V0.10.md).
