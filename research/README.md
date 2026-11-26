# SEC accounting benchmark pilot

The starting universe is a convenience sample of 40 listed issuers. Eligibility
requires December fiscal-year ends, adjacent annual periods and complete
point-in-time standardized US GAAP accounts. SEC Company Facts responses were
downloaded from `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`.
The reports record the original response SHA-256 for each issuer, the revenue
tag used and every issuer exclusion. SEC updates the endpoint over time, so
exact reproduction requires the archived responses.

Run from the repository root.

```sh
python sec_cohort.py research/sec-pilot-issuers.tsv /path/to/archives 2022
python sec_cohort.py research/sec-pilot-issuers.tsv /path/to/archives 2023
```

Name each archive after the ticker in the TSV, with a `.json` extension.
The runner verifies that its CIK matches the issuer list. The feature cutoff
is April 1 UTC after the fiscal year. The following year's growth label must be
available by the next April 1 UTC. Revenue tagging is fixed using only
the feature-period observations. If the outcome is unavailable under the
fixed tag, the issuer is excluded. All usable accounts carry SEC filing dates.
The archive hashes identify the downloaded bytes. Original historical feed
availability and financial statement lineage have not been independently audited.

| Feature year | Matched issuers | ROA rank correlation | Negative Sloan accruals rank correlation |
| --- | ---: | ---: | ---: |
| 2022 | 27 | -0.175 | -0.004 |
| 2023 | 29 | 0.203 | -0.114 |

The baseline ordering reversed between the cohorts. Leave-one-issuer-out
sensitivity for the difference in rank correlation was -0.331 to 0.020 in
2022 and 0.149 to 0.400 in 2023. These ranges describe sensitivity to issuer
omission. The cohorts share issuers and are exploratory. Neither is an
independent holdout. The universe omits delisted companies and is susceptible
to survivorship and selection bias. The results concern later reported revenue
growth and do not measure investment returns or evaluate the strategic score.

Regression coverage includes late filings, tag-switch leakage, missing
archives and CIK mismatch. After the changes, all 67 Python tests passed.
