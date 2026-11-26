"""Build an Explorer rolling-revenue snapshot from local SEC archives."""
import argparse
import json
from pathlib import Path

from holdout_run import timestamp
from sec_rolling import rolling_revenue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", type=Path)
    parser.add_argument("cutoff")
    args = parser.parse_args()
    cutoff = timestamp(args.cutoff)
    issuers = []
    universe = Path(__file__).with_name("sec-pilot-issuers.tsv")
    for line in universe.read_text().splitlines():
        ticker, cik = line.split()
        try:
            row = rolling_revenue((args.archives / f"{ticker}.json").read_bytes(), cutoff)
            if row["cik"] != int(cik):
                raise ValueError("SEC archive CIK mismatch")
        except (OSError, ValueError, KeyError):
            row = {"cik": int(cik), "unavailable": True}
        issuers.append({"ticker": ticker, **row})
    print(json.dumps({"cutoff": cutoff.isoformat(), "issuers": issuers}, indent=2))


if __name__ == "__main__":
    main()
