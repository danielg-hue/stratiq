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

The follow-up audit added fail-closed checks for nonnumeric JSON fact values
and annual baselines revised after their interim comparison. A later annual
revision requires a compatible interim comparison before the model can
combine the values. The three checked-in examples reproduced exactly.

A follow-up corrected the 36-week third-quarter window used by PepsiCo.
The current and prior cumulative periods must now differ by at most one
week, in addition to the existing same-filing requirement. The corrected
November 26 snapshot reconciled all 40 archived issuers. PepsiCo was the
only changed row and returned USD 98.241 billion through September 5, 2026.

The `year_over_year` result compares the current trailing value with the
same prior fiscal window reconstructed at its first eligible filing cutoff.
The prior calculation uses the same revenue tag and preserves its original
inputs. For an interim comparison, the original prior YTD amount must
match the current filing's comparative amount. Where that requirement
fails, prior inputs cannot be reconciled, or the denominator is nonpositive,
growth is unavailable. The trailing level remains independently available.

## Filing tag and reporting-basis changes

If the historical annual filing used a different revenue tag, the engine
can bridge it only when the current annual filing confirms the exact same
period and amount under the new tag. The result records the original tag
and confirmation accession. Alphabet's FY2024 amount was USD 350.018
billion under both filings. Its September 2026 trailing growth is 22.2%.

When an originally filed prior YTD figure differs from the latest
comparative, the engine withholds the trailing level and growth until the
annual baseline can be verified on the same reporting basis. Honeywell's
Q3 2026 filing recasts Aerospace Technologies and Advanced Materials
as discontinued operations. Its prior YTD comparison differs from
the original filing, and no compatible annual baseline was verified.
The updated November 26 snapshot provides both figures for 39 issuers.
Only Alphabet and Honeywell changed.

## Honeywell continuing-operations recast

The June 29, 2026 8-K, accession `0000773840-26-000084`, supplies comparable
historical net sales after the Aerospace separation. Exhibit 99.2 reports
FY2025 USD 19.945 billion and FY2024 USD 19.281 billion. Exhibit 99.3
independently reconciles those annual totals. The USD 14.703 billion
FY2025 nine-month total from Exhibit 99.2 matches the comparative in the
October 2026 10-Q. The FY2024 nine-month total is USD 14.093 billion.

On this continuing-operations basis, the two trailing periods ended
September 30 are USD 20.246 billion for 2026 and USD 19.891 billion for 2025,
or 1.8% year-over-year growth. The curated accession and exhibit digests
are checked in with the rule. It is scoped to the exact interim filing and
verified comparative. A different interim accession or changed comparative
requires a new basis review. Reprocessing the 40-issuer snapshot changed
only Honeywell and restored comparable coverage for all 40 issuers.

[SEC Exhibit 99.2](https://www.sec.gov/Archives/edgar/data/773840/000077384026000084/exhibit992-junexwintersupp.htm)
[SEC Exhibit 99.3](https://www.sec.gov/Archives/edgar/data/773840/000077384026000084/exhibit993unauditedproform.htm)
