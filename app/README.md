# StratIQ SEC research explorer

Build the static release from the repository root with
`python app/build.py /path/to/dist`. Serve the resulting directory over HTTP.
The build uses the checked-in SEC cohort reports and issuer names from
the downloaded Company Facts records. The browser uses same-origin JSON and
links to issuer filings on EDGAR. No credentials or database access are needed.

The explorer provides a fiscal cohort switch, rank correlations, issuer
lookup by company name, ticker or CIK, coverage filters, filing links and a
JSON export of the active cohort. The published data covers an exploratory
accounting pilot. The watchlist is stored in the current browser and follows issuers across
cohorts by CIK. Customer accounts, cross-device sync, alerts and strategic
assessments are outside this release.

QA passed for the default cohort, switching fiscal years, company-name search,
coverage filtering, empty results, inert HTML-like input, EDGAR URLs and JSON
export in a DOM test. The managed preview relay timed out before a browser
session could load, so browser rendering and keyboard navigation remain
unverified. The existing 67 Python regression tests passed.

The verified build was deployed to an owner-private Site at
https://stratiq-sec-research.tangycharm15.chatgpt.site. The deployed source
archive was generated from application commit `4816702`. The connected Vercel
team belongs to Hospice Tools. The GitHub Pages artifact is staged on
`gh-pages`, and the GitHub integration lacks permission to enable Pages.


## Watchlist release QA

Use Node 20+ and install `jsdom@26.1.0` in a separate QA directory.
Run `node app/check.mjs /path/to/dist /path/to/qa-directory` after building.
The suite verified persistence on reopen, cross-tab refresh, removal while
filtered, focus restoration, malformed and stale stored data, and session-only
operation when storage is blocked. These are DOM tests. Visual browser QA
remains outstanding. The watchlist build was deployed on the same private Site
from hosting source commit `eca1d6d`.

## Rolling four-quarter revenue

The private Explorer includes a rolling revenue panel for the existing
40-issuer universe. It displays the archived filing cutoff, each issuer's
actual trailing-period end, USD revenue and links to its input accessions.
The November 26, 2026 UTC snapshot has 40 usable results. PepsiCo's 36-week
third quarter was reconciled using the comparative from the same filing.

To refresh the packaged snapshot from updated SEC archives, run
`PYTHONPATH=. python research/rolling_snapshot.py /path/to/archives CUTOFF`
from the repository root and save the generated JSON to
`research/rolling/explorer.json` before building. The published panel uses
a static snapshot and has no scheduled refresh.

DOM tests verified the cutoff, issuer switching, values, EDGAR links and
the unavailable state. All 92 Python tests passed. Visual browser QA remains
unverified. The corrected panel was packaged from hosting source commit `4992215`.

## On-demand rolling snapshot refresh

Set `STRATIQ_SEC_USER_AGENT` to a SEC-compliant contact header and run the
refresh from the repository root.

```sh
PYTHONPATH=. python research/rolling_snapshot.py --live --replace research/rolling/explorer.json
```

The command fetches each issuer in sequence and stages the candidate in
memory. Replacement is atomic and protected by a local writer lock.
A failed download, missing result, changed issuer universe, older cutoff
or older issuer period leaves the previous snapshot in place. An identical
retry requires no file replacement. Rebuild and publish to expose a
successfully refreshed artifact in the Explorer.

Tests covered atomic replacement, identical retries, and preservation on
download failure, loss of coverage and stale candidates. A replay of all
40 archived issuers matched the published snapshot byte for byte. Triggering
a fresh SEC batch requires a configured contact header. No scheduled job
or automatic publication is configured.

## Side-by-side issuer comparison

Use **Compare with** in the rolling revenue panel to display two issuers
from the same archived cutoff. Each card retains its own reporting period
and SEC filing inputs. The panel indicates when reporting dates differ
and suppresses self-comparison. These figures compare revenue levels,
without a peer ranking or a normalized growth comparison.

DOM regression tests covered selection, matched and mismatched period dates,
and duplicate selection. All 98 Python tests passed. Authenticated visual
browser QA remains open. Hosting source commit: `6449dff`.
