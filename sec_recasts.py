"""Apply a documented continuing-operations recast to an exact SEC filing vintage."""
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path

from holdout_run import timestamp

RECASTS = Path(__file__).resolve().parent / "research" / "rolling" / "recasts.json"


def reconcile_recast(cik, cutoff, sources, inputs):
    recast = json.loads(RECASTS.read_text()).get(str(cik))
    if recast is None or len(sources) != 3:
        return None
    annual, current, prior = sources
    accepted = timestamp(recast["available_at"])
    latest, earlier = recast["prior_years"]
    if (accepted > cutoff or accepted > current.available_at or current.accession != recast["interim_accession"]
            or annual.start.isoformat() != latest["annual_start"] or annual.end.isoformat() != latest["annual_end"]
            or prior.start != annual.start or prior.end.isoformat() != latest["ytd_end"]
            or prior.value != Decimal(latest["ytd_revenue"])
            or date.fromisoformat(earlier["annual_end"]) + timedelta(days=1) != annual.start):
        return None

    def exhibit_input(period, role, end, value):
        return {
            "role": role, "accession": recast["annual_accession"], "start": period["annual_start"],
            "end": period[end], "available_at": accepted.isoformat(), "revenue_usd": period[value],
            "document": recast["exhibit"], "document_sha256": recast["exhibit_sha256"],
        }

    earlier_total = Decimal(earlier["annual_revenue"]) + prior.value - Decimal(earlier["ytd_revenue"])
    total = Decimal(latest["annual_revenue"]) + current.value - prior.value
    if earlier_total <= 0 or total < 0:
        return None
    return {
        "reporting_basis": recast["basis"],
        "trailing_four_quarter_revenue_usd": str(total),
        "inputs": [exhibit_input(latest, "annual", "annual_end", "annual_revenue"), *inputs[1:]],
        "year_over_year": {
            "prior_period_end": prior.end.isoformat(), "prior_cutoff": max(accepted, prior.available_at).isoformat(),
            "prior_revenue_usd": str(earlier_total), "percent": float((total - earlier_total) * 100 / earlier_total),
            "inputs": [
                exhibit_input(earlier, "annual", "annual_end", "annual_revenue"),
                {**inputs[2], "role": "current_ytd"},
                exhibit_input(earlier, "prior_ytd", "ytd_end", "ytd_revenue"),
            ],
            "confirmation": {
                "accession": recast["annual_accession"], "document": recast["confirmation_exhibit"],
                "document_sha256": recast["confirmation_sha256"],
            },
        },
    }
