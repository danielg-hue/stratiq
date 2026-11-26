"""Preserve SEC Company Facts filing vintages and select facts as of a cutoff."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from decimal import Decimal
import json
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Fact:
    accession: str
    form: str
    start: date | None
    end: date
    filed: date
    available_at: datetime
    value: Decimal
    source_sha256: str


def fetch_company_facts(cik, user_agent):
    """Retrieve the original response bytes using a caller-supplied SEC contact."""
    if type(cik) is not int or not 1 <= cik <= 9_999_999_999:
        raise ValueError("invalid SEC CIK")
    if not isinstance(user_agent, str) or "@" not in user_agent or "\n" in user_agent or "\r" in user_agent:
        raise ValueError("SEC User-Agent must include contact email")
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    request = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        data = response.read(64 * 1024 * 1024 + 1)
    if len(data) > 64 * 1024 * 1024:
        raise ValueError("SEC response exceeds size limit")
    return data


def vintages(raw, taxonomy, concept, unit):
    payload = json.loads(raw, parse_float=Decimal)
    source_digest = sha256(raw).hexdigest()
    entries = payload["facts"].get(taxonomy, {}).get(concept, {}).get("units", {}).get(unit, [])
    output = set()
    for entry in entries:
        start = date.fromisoformat(entry["start"]) if "start" in entry else None
        end = date.fromisoformat(entry["end"])
        filed = date.fromisoformat(entry["filed"])
        if end > filed or (start is not None and start > end):
            raise ValueError("invalid SEC filing chronology")
        # Company Facts supplies filing dates. Wait until that Eastern date has elapsed.
        available = datetime.combine(filed + timedelta(days=1), time(), ZoneInfo("America/New_York"))
        if type(entry["val"]) not in (int, Decimal):
            raise ValueError("SEC fact value must be a JSON number")
        value = Decimal(entry["val"])
        if not value.is_finite():
            raise ValueError("nonfinite SEC fact")
        output.add(Fact(entry["accn"], entry["form"], start, end, filed,
                        available.astimezone(timezone.utc), value, source_digest))
    return tuple(sorted(output, key=lambda f: (f.end, f.start or date.min, f.filed, f.accession, f.form, f.value)))


def select_as_of(facts, cutoff, *, start, end, forms=("10-K", "10-K/A", "10-Q", "10-Q/A")):
    if not isinstance(cutoff, datetime) or cutoff.utcoffset() is None:
        raise ValueError("timezone-aware cutoff required")
    eligible = [fact for fact in facts
                if fact.start == start and fact.end == end and fact.form in forms
                and fact.available_at <= cutoff]
    if not eligible:
        return None
    latest = max(fact.available_at for fact in eligible)
    candidates = [fact for fact in eligible if fact.available_at == latest]
    if len({fact.value for fact in candidates}) != 1:
        raise ValueError("conflicting SEC values at latest observable filing date")
    return min(candidates, key=lambda fact: (fact.accession, fact.form, fact.source_sha256))
