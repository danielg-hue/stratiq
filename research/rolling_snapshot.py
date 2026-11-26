"""Build or safely refresh the Explorer's rolling-revenue snapshot."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import sleep

from holdout_run import timestamp
from sec_facts import fetch_company_facts
from sec_rolling import rolling_revenue


UNIVERSE = Path(__file__).with_name("sec-pilot-issuers.tsv")


def build_snapshot(universe, read_archive, cutoff, *, strict=False):
    issuers = []
    for line in universe.read_text().splitlines():
        ticker, cik_text = line.split()
        cik = int(cik_text)
        try:
            row = rolling_revenue(read_archive(ticker, cik), cutoff)
            if row["cik"] != cik:
                raise ValueError("SEC archive CIK mismatch")
        except (OSError, ValueError, KeyError) as error:
            if strict:
                raise ValueError(f"{ticker}: {error}") from error
            row = {"cik": cik, "unavailable": True}
        issuers.append({"ticker": ticker, **row})
    return {"cutoff": cutoff.isoformat(), "issuers": issuers}


def snapshot_index(snapshot):
    by_cik = {row["cik"]: row for row in snapshot["issuers"]}
    if not by_cik or len(by_cik) != len(snapshot["issuers"]):
        raise ValueError("snapshot must have unique issuer identities")
    return by_cik


def replace_snapshot(destination, candidate):
    """Replace an existing snapshot only after checking coverage and freshness."""
    lock_path = destination.with_name(f".{destination.name}.refresh.lock")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = json.loads(destination.read_text())
        if timestamp(candidate["cutoff"]) < timestamp(previous["cutoff"]):
            raise ValueError("candidate filing cutoff is older than current snapshot")
        old, new = map(snapshot_index, (previous, candidate))
        if old.keys() != new.keys() or any(new[cik]["ticker"] != row["ticker"] for cik, row in old.items()):
            raise ValueError("candidate issuer universe differs from current snapshot")
        for cik, row in old.items():
            updated = new[cik]
            if updated.get("unavailable"):
                raise ValueError(f'{row["ticker"]}: refresh has no usable result')
            if row.get("period_end") and updated["period_end"] < row["period_end"]:
                raise ValueError(f'{row["ticker"]}: reported period would move backward')
        if candidate == previous:
            return False
        temporary = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(json.dumps(candidate, indent=2, allow_nan=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", type=Path, nargs="?")
    parser.add_argument("cutoff", nargs="?")
    parser.add_argument("--live", action="store_true", help="fetch fresh SEC Company Facts instead of reading archives")
    parser.add_argument("--replace", type=Path, help="validate and replace an existing snapshot")
    args = parser.parse_args()
    if args.live == (args.archives is not None):
        parser.error("specify either the archive directory or --live")
    try:
        cutoff = timestamp(args.cutoff) if args.cutoff else datetime.now(timezone.utc)
        if cutoff > datetime.now(timezone.utc):
            raise ValueError("filing cutoff cannot be in the future")
        if args.live:
            user_agent = os.environ.get("STRATIQ_SEC_USER_AGENT")

            def read_archive(ticker, cik):
                sleep(.2)
                return fetch_company_facts(cik, user_agent)
        else:
            def read_archive(ticker, cik):
                return (args.archives / f"{ticker}.json").read_bytes()

        snapshot = build_snapshot(UNIVERSE, read_archive, cutoff, strict=args.live or args.replace is not None)
        if args.replace:
            changed = replace_snapshot(args.replace, snapshot)
            print("Snapshot updated." if changed else "Snapshot already current.")
        else:
            print(json.dumps(snapshot, indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    main()
