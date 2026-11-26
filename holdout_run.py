"""Register predictions without labels, then evaluate with a separate outcome file."""
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from backtest import Observation
from holdout import HoldoutProtocol, evaluate_holdout, prediction_digest
from validation import number, text


@dataclass(frozen=True)
class Prediction:
    company: str
    as_of: datetime
    outcome_end: datetime
    scores: dict
    feature_available_at: dict


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("expected an ISO 8601 timestamp")
    result = datetime.fromisoformat(value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value)
    if result.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return result.astimezone(timezone.utc)


def checked_fields(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ValueError(f"expected exactly these fields: {fields}")
    return value


def row_key(row):
    if not text(row["company"]) or row["company"] != row["company"].strip():
        raise ValueError("invalid company identifier")
    key = (row["company"], timestamp(row["as_of"]), timestamp(row["outcome_end"]))
    if key[1] >= key[2]:
        raise ValueError("invalid observation chronology")
    return key


def register(specification, model_artifact, predictions):
    checked_fields(specification, "start end label_cutoff models metric")
    if specification["metric"] not in ("revenue_growth", "total_return"):
        raise ValueError("unsupported outcome metric")
    if not isinstance(specification["models"], list):
        raise ValueError("models must be a list")
    start, end, cutoff = (timestamp(specification[name]) for name in ("start", "end", "label_cutoff"))
    models = tuple(specification["models"])
    artifact_digest = sha256(model_artifact).hexdigest()
    # Validate the model identifiers before using them as mapping keys.
    HoldoutProtocol(start, end, cutoff, models, artifact_digest, "0" * 64)
    if not isinstance(predictions, list) or not predictions:
        raise ValueError("nonempty prediction list required")

    validated = []
    for row in predictions:
        checked_fields(row, "company as_of outcome_end scores feature_available_at")
        key = row_key(row)
        if not start <= key[1] < end or key[2] > cutoff:
            raise ValueError("prediction outside registered window")
        scores = row["scores"]
        dates = row["feature_available_at"]
        if (not isinstance(scores, dict) or not isinstance(dates, dict)
                or set(scores) != set(models) or set(dates) != set(models)):
            raise ValueError("prediction model fields must match the registration")
        available = {model: timestamp(dates[model]) for model in models}
        if any(value > key[1] for value in available.values()) or any(not number(x) for x in scores.values()):
            raise ValueError("predictions require finite scores and point-in-time feature dates")
        validated.append(Prediction(*key, scores, available))

    protocol = HoldoutProtocol(start, end, cutoff, models, artifact_digest, prediction_digest(models, validated))
    return protocol, tuple(validated)


def registration_digest(protocol, metric):
    payload = json.dumps(["stratiq-holdout-v1", protocol.digest, metric], separators=(",", ":"))
    return sha256(payload.encode()).hexdigest()


def evaluate(specification, registered_digest, model_artifact, predictions, outcomes):
    protocol, frozen = register(specification, model_artifact, predictions)
    metric = specification["metric"]
    digest = registration_digest(protocol, metric)
    if digest != registered_digest:
        raise ValueError("bundle differs from the registered holdout")
    checked_fields(outcomes, "metric rows")
    if outcomes["metric"] != metric or not isinstance(outcomes["rows"], list):
        raise ValueError("outcome file does not match the registered metric")

    expected = {(row.company, row.as_of, row.outcome_end) for row in frozen}
    labels = {}
    for row in outcomes["rows"]:
        checked_fields(row, "company as_of outcome_end label_available_at value")
        key = row_key(row)
        available = timestamp(row["label_available_at"])
        if key not in expected or key in labels:
            raise ValueError("unexpected or duplicate outcome key")
        if not key[2] <= available <= protocol.label_cutoff or not number(row["value"]) or row["value"] < -1:
            raise ValueError("invalid or unavailable outcome")
        labels[key] = available, row["value"]
    if labels.keys() != expected:
        raise ValueError("outcomes missing for registered predictions")

    joined = []
    for row in frozen:
        available, value = labels[row.company, row.as_of, row.outcome_end]
        joined.append(Observation(
            company=row.company, as_of=row.as_of, outcome_end=row.outcome_end,
            label_available_at=available, scores=row.scores, total_return=value,
            feature_available_at=row.feature_available_at,
        ))
    result = evaluate_holdout(protocol, protocol.digest, model_artifact, joined)
    return {**result, "metric": metric, "registration_sha256": digest}


def load_json(path):
    def unique_pairs(pairs):
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError("duplicate JSON field")
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("register", "evaluate"):
        command = commands.add_parser(name)
        command.add_argument("specification", type=Path)
        command.add_argument("model_artifact", type=Path)
        command.add_argument("predictions", type=Path)
        if name == "evaluate":
            command.add_argument("registered_digest")
            command.add_argument("outcomes", type=Path)
    args = parser.parse_args()
    try:
        specification = load_json(args.specification)
        artifact = args.model_artifact.read_bytes()
        predictions = load_json(args.predictions)
        if args.command == "register":
            protocol, frozen = register(specification, artifact, predictions)
            result = {
                "registration_sha256": registration_digest(protocol, specification["metric"]),
                "protocol_sha256": protocol.digest,
                "predictions": len(frozen),
            }
        else:
            result = evaluate(specification, args.registered_digest, artifact, predictions, load_json(args.outcomes))
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, indent=2, default=lambda value: value.isoformat(), allow_nan=False))


if __name__ == "__main__":
    main()
