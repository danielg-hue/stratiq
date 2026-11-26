# FY2026 prospective outcome freeze

The forecast bundle fixes two accounting baselines on the existing
40-issuer convenience universe. Thirty issuers qualified using their
December FY2025 filings available by April 1, 2026 UTC. The November 2026
freeze takes place partway through the outcome year. Interim performance
was already public. The full-year outcomes are still pending. This bundle
does not evaluate the StratIQ strategic score or establish independent custody.

Use adjacent December-ending FY2026 annual periods and the fixed revenue
tag for each issuer. The denominator is the artifact's frozen FY2025 revenue.
Select the latest eligible 10-K or 10-K/A fact available by April 1, 2027 UTC,
using the existing conservative SEC filing-date availability convention.
Growth is (FY2026 revenue minus frozen FY2025 revenue) divided by frozen
FY2025 revenue. Use the fixed observation and outcome keys in
`predictions.json`. Preserve missing or conflicting figures as unresolved.
A missing outcome blocks the registered complete-cohort evaluation.

A custodian should retain the digest in `registration.json` independently
and run the documented [holdout workflow](../HOLDOUT.md) with the sealed
bundle when the outcome window closes. Preserve the committed bundle.
Reproduction requires the exact original Company Facts archives identified
by the SHA-256 values in `model.json`.

QA covered forecast generation without outcome records, cutoff rejection
of a late FY2025 revision, and identical predictions after adding future
data. The Python suite passed all 86 tests.
