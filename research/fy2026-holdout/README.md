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

## Custodian outcome collection

After the cutoff, archive the relevant SEC Company Facts responses in
custodian-controlled storage as `TICKER.json` files. From the repository
root run the collector with the digest from the independent custody record.

```sh
python sec_holdout_outcomes.py research/fy2026-holdout REGISTERED_SHA256 PRIVATE_ARCHIVES NEW_PRIVATE_DIRECTORY
```

It verifies the frozen bundle, publisher CIK, adjacent fiscal periods,
revenue tag, cutoff and denominator. A missing or conflicting outcome blocks
the entire output. A successful run creates a private directory containing
`outcomes.json` for the evaluator and `provenance.json` for the custodian.
The latter records both accessions, both revenue values, archive digests
and the outcome file digest. Keep both files and the original SEC archives
outside the public repository. Share only the approved aggregate result.

The full synthetic round trip confirmed that the evaluator accepts the
generated labels and that a post-cutoff revision cannot affect them. Tests
also verified that altered registrations or premature collection never read
outcome archives. The live frozen bundle remains locked until the cutoff.
