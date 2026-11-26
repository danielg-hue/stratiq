# StratIQ SEC research explorer

Build the static release from the repository root with
`python app/build.py /path/to/dist`. Serve the resulting directory over HTTP.
The build uses the checked-in SEC cohort reports and issuer names from
the downloaded Company Facts records. The browser uses same-origin JSON and
links to issuer filings on EDGAR. No credentials or database access are needed.

The explorer provides a fiscal cohort switch, rank correlations, issuer
lookup by company name, ticker or CIK, coverage filters, filing links and a
JSON export of the active cohort. The published data covers an exploratory
accounting pilot. Customer accounts, watchlists, alerts and strategic
assessments are outside this release.

QA passed for the default cohort, switching fiscal years, company-name search,
coverage filtering, empty results, inert HTML-like input, EDGAR URLs and JSON
export in a DOM test. The managed preview relay timed out before a browser
session could load, so browser rendering and keyboard navigation remain
unverified. The existing 67 Python regression tests passed.
