# Independent holdout workflow

The model author prepares three files. The specification JSON requires
`start`, `end`, `label_cutoff`, an ordered list of distinct `models`, and
a `metric` of `revenue_growth` or `total_return`. Use timezone-aware ISO 8601
dates. The model artifact is opaque bytes and is hashed without execution.
The predictions JSON is a list with exactly these keys per observation.

- `company` contains a stable issuer ID.
- `as_of` and `outcome_end` identify the observation and outcome period.
- `scores` maps each registered model to a finite numeric score.
- `feature_available_at` maps each model to its latest feature availability.

Run registration before the custodian releases any outcome.

```sh
python holdout_run.py register specification.json model.bin predictions.json
```

The custodian records the returned `registration_sha256` in an independent,
timestamped record. They retain the labels separately. The outcome JSON has
`metric` and `rows`. Each row has the same three key fields (`company`,
`as_of`, `outcome_end`), plus `label_available_at` and numeric `value`.
Keep the registered digest separate from the model author's bundle.

```sh
python holdout_run.py evaluate specification.json model.bin predictions.json REGISTERED_SHA256 outcomes.json
```

The evaluator rejects changes to the frozen bundle and refuses missing,
duplicate, unexpected, or cutoff-ineligible labels. Use a universe whose
outcomes can be collected under the predeclared definition. The report
returns aggregate cohort rank correlations. The evaluator cannot prove
when a registration was made, authenticate data provenance, or prevent
out-of-band label access. Independence depends on the custodian and the
external registration record. The existing SEC pilot cohorts have already
been explored and are ineligible as independent holdouts.

QA exercised both CLI entry points with disjoint files and synthetic
outcomes. It checked altered models, predictions and outcome definitions,
late features, and unavailable labels. The full Python suite passed 71 tests.
