# Rolling four-quarter SEC revenue

Run a current check with an SEC-compliant contact User-Agent in
`STRATIQ_SEC_USER_AGENT`.

```sh
python sec_rolling.py --cik 1652044
python sec_rolling.py --archive alphabet-facts.json --as-of 2026-11-26T00:00:00Z
```

When a newer interim report is available, trailing revenue equals prior
fiscal-year revenue plus current fiscal year-to-date revenue minus the
comparative prior fiscal year-to-date revenue. The two interim values must
come from the same filing, use one revenue tag and cover comparable fiscal
durations. At a fiscal year-end, the annual figure supplies all four quarters.
Each output includes the period end, input accessions, cutoff and archive
digest. A newer recognized period with unresolved inputs can block the
calculation. The freshness check is bounded by the supplied SEC dataset
and supported revenue tags.

The archived SEC pilot returned a usable result for 39 of 40 issuers at
the November 26 UTC cutoff. One newer period could not be reconciled.
Among results, the latest reported period varied by issuer. The checked-in
examples cover Alphabet, Meta and Amazon for the period ending September 30,
2026. Archive data can differ from a later live SEC response.

All 89 Python tests and the PostgreSQL regression suite passed. Tests included
the exact filing-availability boundary and mismatched interim comparatives.
The rolling check is a revenue monitor. The frozen FY2026 holdout is
evaluated separately against its preregistered full-year outcome.
