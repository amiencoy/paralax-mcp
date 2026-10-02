import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
import yaml
from axionorm import Engine
from axionorm.engine import digest
from parabiont.carrier import keygen, pack, verify
from parabiont.store import Store

from paralax_mcp.delta import DeltaValidationError, create_review_bundle, load_delta


def policy_and_opa(tmp_path):
    sibling = Path(__file__).resolve().parents[2] / "axionorm"
    source = Path(os.environ.get("AXIONORM_POLICY", sibling / "examples/technical-review.yaml"))
    opa = os.environ.get("OPA_BINARY", str(sibling / ".runtime/opa/opa"))
    policy = yaml.safe_load(source.read_text())
    next(rule for rule in policy["tools"] if rule["name"] == "workspace_write")["allow"] = True
    target = tmp_path / "policy.yaml"
    target.write_text(yaml.safe_dump(policy))
    return target, opa


def valid_delta(*, technical=True):
    labels = ["roundtrip", "migration"]
    if technical:
        labels.insert(0, "technical")
    return {
        "version": "parabiont-delta/v0.1",
        "created_at": "2026-09-27T11:14:48Z",
        "source_runtime": "integration-test/model",
        "status": "untrusted-proposal",
        "summary": "Round-trip context carrier proposal.",
        "items": [{
            "id": "roundtrip-fact",
            "kind": "fact",
            "topic": "paralax",
            "labels": labels,
            "text": "The governed return path produced a quarantined delta proposal.",
            "provenance": ["integration test MCP context_read and workspace_write calls"],
            "confidence": "verified",
            "supersedes": [],
        }],
    }


def gateway_config(tmp_path, policy, opa):
    engine = Engine(policy, opa)
    keygen(tmp_path / "keys")
    item = {"id": "incoming", "kind": "task", "topic": "paralax",
            "labels": ["technical"], "text": "Verify the governed round trip."}
    packet, _ = pack(engine, {"version": "parabiont-candidate/v0.1", "items": [item]},
                     {"version": "axionorm-review/v0.1", "approved": {"incoming": digest(item)}},
                     tmp_path / "keys/issuer.pem")
    store = Store(tmp_path / "store.sqlite")
    store.accept(verify(packet, tmp_path / "keys/issuer.pub.pem", engine))
    workspace = tmp_path / "workspace"; workspace.mkdir()
    output = tmp_path / "artifacts"; output.mkdir()
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"version":"paralax-files/v0.1","files":{}}')
    return {
        "policy": str(policy), "opa": str(opa), "store": store.path,
        "workspace": str(workspace), "output": str(output), "manifest": str(manifest),
        "bond_id": packet["capsule"]["bond_id"],
    }


def test_delta_schema_diagnostics(tmp_path):
    delta = valid_delta()
    delta["items"][0]["provenance"] = "not-an-array"
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(delta))
    with pytest.raises(DeltaValidationError) as caught:
        load_delta(path)
    assert caught.value.errors[0]["path"] == "$.items[0].provenance"


def test_duplicate_json_keys_and_item_ids_are_rejected(tmp_path):
    duplicate_key = tmp_path / "duplicate-key.json"
    duplicate_key.write_text('{"version":"parabiont-delta/v0.1","version":"other"}')
    with pytest.raises(DeltaValidationError) as caught:
        load_delta(duplicate_key)
    assert "Duplicate JSON key" in caught.value.errors[0]["message"]

    delta = valid_delta()
    delta["items"].append(dict(delta["items"][0]))
    duplicate_id = tmp_path / "duplicate-id.json"
    duplicate_id.write_text(json.dumps(delta))
    with pytest.raises(DeltaValidationError) as caught:
        load_delta(duplicate_id)
    assert caught.value.errors == [{"path": "$.items", "message": "item IDs must be unique"}]


def test_policy_diagnostics_explain_required_labels(tmp_path):
    policy, opa = policy_and_opa(tmp_path)
    path = tmp_path / "delta.json"
    path.write_text(json.dumps(valid_delta(technical=False)))
    report = create_review_bundle(path, tmp_path / "review", policy, opa,
                                  approved_ids=["roundtrip-fact"])
    assert report["status"] == "denied"
    decision = report["decisions"][0]
    assert decision["checks"]["required_labels_present"] is False
    assert "required_labels_present" in decision["reasons"]
    allowed = create_review_bundle(path, tmp_path / "review-with-label", policy, opa,
                                   approved_ids=["roundtrip-fact"], add_labels=["technical"])
    assert allowed["status"] == "allowed"
    provenance = json.loads((tmp_path / "review-with-label/provenance.json").read_text())
    assert provenance["items"][0]["added_labels"] == ["technical"]


def test_stdio_roundtrip_to_schema_valid_axionorm_review(tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    policy, opa = policy_and_opa(tmp_path)
    config = gateway_config(tmp_path, policy, opa)
    config_path = tmp_path / "gateway.json"
    config_path.write_text(json.dumps(config))
    delta_text = json.dumps(valid_delta(), indent=2) + "\n"

    async def run():
        params = StdioServerParameters(command=sys.executable,
            args=["-m", "paralax_mcp.run", "--config", str(config_path)])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                context = await session.call_tool("context_read", {})
                assert not context.isError
                created = await session.call_tool("workspace_write", {
                    "name": "context-delta.json", "content": delta_text})
                assert not created.isError

    asyncio.run(run())
    delta_path = Path(config["output"]) / "context-delta.json"
    bundle = Path(config["output"]) / "review-bundle"
    report = create_review_bundle(delta_path, bundle, policy, opa,
                                  approved_ids=["roundtrip-fact"])
    assert report["status"] == "allowed"
    assert report["allowed_ids"] == ["roundtrip-fact"]
    assert report["authoritative_promotion"] is False
    assert (bundle / "source-delta.json").read_text() == delta_text
    provenance = json.loads((bundle / "provenance.json").read_text())
    assert provenance["source"]["sha256"] == hashlib.sha256(delta_text.encode()).hexdigest()
    assert provenance["source"]["name"] == "context-delta.json"
    assert str(tmp_path) not in (bundle / "provenance.json").read_text()
    assert provenance["items"][0]["provenance"] == valid_delta()["items"][0]["provenance"]
    assert provenance["items"][0]["added_labels"] == []
    policy_report = json.loads((bundle / "policy-report.json").read_text())
    assert policy_report["decisions"][0]["allowed"] is True
    assert policy_report["authoritative_promotion"] is False
    with pytest.raises(FileExistsError):
        create_review_bundle(delta_path, bundle, policy, opa, approved_ids=["roundtrip-fact"])
