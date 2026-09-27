import argparse
import hashlib
import json
import os
import re
import sys
from importlib.resources import files
from pathlib import Path

from axionorm import Engine
from axionorm.engine import PolicyDenied, digest
from jsonschema import Draft202012Validator, FormatChecker


class DeltaValidationError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Context delta failed JSON Schema validation")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def bundled_schema():
    resource = files("paralax_mcp").joinpath("schemas/context-delta.schema.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def load_delta(path, schema=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Delta must be a regular non-symlink file")
    if path.stat().st_size > 1048576:
        raise ValueError("Delta exceeds the 1 MiB review limit")
    raw = path.read_bytes()
    try:
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise DeltaValidationError([{"path": "$", "message": str(error)}]) from error
    validate_delta(value, schema or bundled_schema())
    return raw, value


def validate_delta(value, schema=None):
    validator = Draft202012Validator(schema or bundled_schema(), format_checker=FormatChecker())
    problems = []
    for error in sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path)):
        pointer = "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path)
        problems.append({"path": pointer, "message": error.message})
    if not problems:
        identifiers = [item["id"] for item in value["items"]]
        if len(identifiers) != len(set(identifiers)):
            problems.append({"path": "$.items", "message": "item IDs must be unique"})
    if problems:
        raise DeltaValidationError(problems)
    return value


def adapt_delta(delta, add_labels=()):
    additions = tuple(dict.fromkeys(add_labels))
    if any(not re.fullmatch(r"[a-z0-9-]{1,64}", label) for label in additions):
        raise ValueError("Added labels must match [a-z0-9-]{1,64}")
    candidate_items = []
    provenance_items = []
    for source in delta["items"]:
        labels = list(source["labels"])
        added = []
        for label in additions:
            if label not in labels:
                labels.append(label)
                added.append(label)
        if len(labels) > 20:
            raise ValueError(f"Item {source['id']} exceeds 20 labels after adaptation")
        candidate = {key: source[key] for key in ("id", "kind", "topic")}
        candidate["labels"] = labels
        candidate["text"] = source["text"]
        candidate_items.append(candidate)
        provenance_items.append({
            "id": source["id"],
            "provenance": source["provenance"],
            "confidence": source["confidence"],
            "supersedes": source["supersedes"],
            "source_item_digest": sha256(canonical(source)),
            "candidate_item_digest": digest(candidate),
            "added_labels": added,
        })
    return {"version": "parabiont-candidate/v0.1", "items": candidate_items}, provenance_items


def policy_diagnostics(engine, candidate, review):
    decisions = []
    denied_labels = set(engine.policy["context"]["denied_labels"])
    for item in candidate["items"]:
        reviewed = review["approved"].get(item["id"]) == digest(item)
        sensitive = engine.sensitive(item["text"])
        allowed = engine.decide({"action": "context", "item": item, "reviewed": reviewed, "sensitive": sensitive})
        checks = {
            "review_digest_matches": reviewed,
            "sensitive_pattern_clear": not sensitive,
            "topic_allowed": item["topic"] in engine.policy["context"]["topics"],
            "kind_allowed": item["kind"] in engine.policy["context"]["kinds"],
            "denied_labels_clear": not bool(denied_labels.intersection(item["labels"])),
            "within_text_limit": len(item["text"]) <= engine.policy["context"]["max_item_chars"],
            "technical_label_present": "technical" in item["labels"],
        }
        reasons = [name for name, passed in checks.items() if not passed]
        if not allowed and not reasons:
            reasons.append("denied-by-active-opa-rule")
        decisions.append({"id": item["id"], "allowed": allowed, "checks": checks, "reasons": reasons})
    return decisions


def create_review_bundle(delta_path, output, policy, opa, *, approved_ids, add_labels=(), schema=None):
    raw, delta = load_delta(delta_path, schema)
    candidate, mappings = adapt_delta(delta, add_labels)
    known = {item["id"] for item in candidate["items"]}
    approved = set(approved_ids)
    unknown = sorted(approved - known)
    if unknown:
        raise ValueError("Unknown item IDs: " + ", ".join(unknown))
    review = {
        "version": "axionorm-review/v0.1",
        "approved": {item["id"]: digest(item) for item in candidate["items"] if item["id"] in approved},
    }
    engine = Engine(policy, opa)
    decisions = policy_diagnostics(engine, candidate, review)
    try:
        context, audit = engine.filter_context(candidate, review)
    except PolicyDenied as error:
        context = []
        audit = {"policy_digest": engine.policy_digest, "error": str(error)}
    allowed_ids = {item["id"] for item in context}
    selected_denied = sorted(approved - allowed_ids)
    status = "allowed" if approved and not selected_denied else "denied"
    report = {
        "version": "paralax-delta-policy-report/v0.1",
        "status": status,
        "source_delta_sha256": sha256(raw),
        "candidate_sha256": sha256(canonical(candidate)),
        "policy_digest": engine.policy_digest,
        "approved_ids": sorted(approved),
        "allowed_ids": sorted(allowed_ids),
        "denied_ids": selected_denied,
        "decisions": decisions,
        "axionorm_audit": audit,
        "authoritative_promotion": False,
    }
    provenance = {
        "version": "paralax-delta-provenance/v0.1",
        "source": {
            "name": Path(delta_path).name,
            "sha256": sha256(raw),
            "schema_id": (schema or bundled_schema()).get("$id"),
            "created_at": delta["created_at"],
            "source_runtime": delta["source_runtime"],
            "status": delta["status"],
        },
        "items": mappings,
        "authoritative_promotion": False,
    }
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    _exclusive_write(destination / "source-delta.json", raw)
    _exclusive_json(destination / "candidate.json", candidate)
    _exclusive_json(destination / "provenance.json", provenance)
    _exclusive_json(destination / "review.json", review)
    _exclusive_json(destination / "policy-report.json", report)
    return report


def _exclusive_write(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)


def _exclusive_json(path, value):
    _exclusive_write(path, json.dumps(value, indent=2, ensure_ascii=False).encode() + b"\n")


def _reject_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def _read_schema(path):
    return json.loads(Path(path).read_text()) if path else bundled_schema()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate and review quarantined Parabiont context deltas")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="Validate a delta without creating review artifacts")
    validate.add_argument("delta")
    validate.add_argument("--schema")
    review = sub.add_parser("review", help="Create a non-promoting Axionorm review bundle")
    review.add_argument("delta")
    review.add_argument("--policy", required=True)
    review.add_argument("--opa", required=True)
    review.add_argument("--output", required=True)
    review.add_argument("--schema")
    approval = review.add_mutually_exclusive_group(required=True)
    approval.add_argument("--approve", nargs="+")
    approval.add_argument("--approve-all", action="store_true")
    review.add_argument("--add-label", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        schema = _read_schema(args.schema)
        raw, delta = load_delta(args.delta, schema)
        if args.command == "validate":
            result = {"valid": True, "items": len(delta["items"]), "sha256": sha256(raw), "schema_id": schema.get("$id")}
            print(json.dumps(result, indent=2))
            return 0
        approved = [item["id"] for item in delta["items"]] if args.approve_all else args.approve
        report = create_review_bundle(args.delta, args.output, args.policy, args.opa,
                                      approved_ids=approved, add_labels=args.add_label, schema=schema)
        print(json.dumps(report, indent=2))
        return 0 if report["status"] == "allowed" else 2
    except DeltaValidationError as error:
        print(json.dumps({"valid": False, "errors": error.errors}, indent=2), file=sys.stderr)
        return 2
    except (OSError, ValueError, json.JSONDecodeError, PolicyDenied) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
