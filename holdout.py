"""Evaluate a frozen, independently supplied holdout on matched cohorts."""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from backtest import compare


def _utc(value):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class HoldoutProtocol:
    start: datetime
    end: datetime
    label_cutoff: datetime
    models: tuple
    model_artifact_sha256: str
    predictions_sha256: str

    def __post_init__(self):
        if not _utc(self.start) < _utc(self.end) <= _utc(self.label_cutoff):
            raise ValueError("invalid holdout chronology")
        if (not isinstance(self.models, tuple) or len(self.models) < 2
                or any(not isinstance(model, str) or not model.strip() for model in self.models)
                or len(set(self.models)) != len(self.models)):
            raise ValueError("at least two distinct model names required")
        for digest in (self.model_artifact_sha256, self.predictions_sha256):
            if (not isinstance(digest, str) or len(digest) != 64
                    or any(character not in "0123456789abcdef" for character in digest)):
                raise ValueError("invalid artifact digest")

    @property
    def digest(self):
        payload = [
            _utc(self.start).isoformat(), _utc(self.end).isoformat(),
            _utc(self.label_cutoff).isoformat(), self.models,
            self.model_artifact_sha256, self.predictions_sha256,
        ]
        return sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def development_rows(rows, holdout_start):
    """Discard observations whose outcomes were unavailable before the holdout."""
    cutoff = _utc(holdout_start)
    selected = []
    for row in rows:
        start, end, available = map(_utc, (row.as_of, row.outcome_end, row.label_available_at))
        if not start < end <= available:
            raise ValueError("invalid outcome chronology")
        if available < cutoff:
            selected.append(row)
    return tuple(selected)


def prediction_digest(models, rows):
    """Hash the prediction keys, values, and feature dates before label release."""
    records = [
        (row.company, _utc(row.as_of).isoformat(), _utc(row.outcome_end).isoformat(),
         [row.scores.get(model) for model in models],
         [_utc(row.feature_available_at[model]).isoformat() for model in models])
        for row in rows
    ]
    records.sort(key=lambda record: record[:3])
    if len({tuple(record[:3]) for record in records}) != len(records):
        raise ValueError("duplicate prediction key")
    return sha256(json.dumps(records, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def evaluate_holdout(protocol, registered_digest, model_artifact, rows):
    """Evaluate fixed predictions. The caller controls label custody and release."""
    if protocol.digest != registered_digest:
        raise ValueError("protocol differs from registered holdout")
    if sha256(model_artifact).hexdigest() != protocol.model_artifact_sha256:
        raise ValueError("model artifact differs from registered holdout")

    start, end = _utc(protocol.start), _utc(protocol.end)
    rows = tuple(rows)
    if not rows or any(not start <= _utc(row.as_of) < end for row in rows):
        raise ValueError("evaluation requires holdout-only observations")
    if prediction_digest(protocol.models, rows) != protocol.predictions_sha256:
        raise ValueError("predictions differ from registered holdout")
    result = compare(rows, protocol.models, protocol.label_cutoff)
    if not any(all(value is not None for value in cohort["rank_ic"].values())
               for cohort in result["cohorts"]):
        raise ValueError("holdout has no cohort with comparable rank correlations")
    return {**result, "protocol_sha256": protocol.digest}
