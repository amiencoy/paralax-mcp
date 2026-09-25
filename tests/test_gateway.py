import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
import pytest
from axionorm import Engine, PolicyDenied
from axionorm.engine import digest
from parabiont.carrier import keygen, pack, verify
from parabiont.store import Store
from paralax_mcp.gateway import Gateway


@pytest.fixture
def config(tmp_path, request):
    sibling = Path(__file__).resolve().parents[2] / "axionorm"
    policy = os.environ.get("AXIONORM_POLICY", str(sibling / "examples/technical-review.yaml"))
    opa = os.environ.get("OPA_BINARY", str(sibling / ".runtime/opa/opa"))
    if getattr(request, "param", False):
        import yaml
        data = yaml.safe_load(Path(policy).read_text())
        next(r for r in data["tools"] if r["name"] == "workspace_write")["allow"] = True
        policy = str(tmp_path / "write-policy.yaml")
        Path(policy).write_text(yaml.safe_dump(data))
    engine = Engine(policy, opa)
    keygen(tmp_path / "keys")
    item = {"id": "p1", "kind": "task", "topic": "paralax", "labels": ["technical"], "text": "Review technical project files."}
    packet, _ = pack(engine, {"version": "parabiont-candidate/v0.1", "items": [item]},
        {"version": "axionorm-review/v0.1", "approved": {"p1": digest(item)}}, tmp_path / "keys/issuer.pem")
    store = Store(tmp_path / "store.sqlite")
    store.accept(verify(packet, tmp_path / "keys/issuer.pub.pem", engine))
    root = tmp_path / "workspace"; root.mkdir()
    output = tmp_path / "artifacts"; output.mkdir()
    (root / "project.md").write_text("A safe project brief.")
    (root / "private.md").write_text("Personal material must not leave this directory.")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"version": "paralax-files/v0.1", "files": {
        "project.md": hashlib.sha256((root / "project.md").read_bytes()).hexdigest()}}))
    return {"policy": policy, "opa": opa, "store": store.path, "workspace": str(root), "output": str(output),
            "manifest": str(manifest), "bond_id": packet["capsule"]["bond_id"]}


def test_read_and_scope(config):
    gateway = Gateway(config)
    assert gateway.workspace_list() == ["project.md"]
    assert gateway.workspace_read("project.md") == "A safe project brief."
    for path in ("../manifest.json", "private.md", "/etc/passwd", ".env"):
        with pytest.raises(PolicyDenied): gateway.workspace_read(path)
    with pytest.raises(PolicyDenied): gateway.workspace_write("new.md", "content")


def test_change_and_symlink(config):
    gateway = Gateway(config)
    file = Path(config["workspace"]) / "project.md"
    file.write_text("Changed after approval")
    with pytest.raises(PolicyDenied): gateway.workspace_read("project.md")
    file.unlink(); file.symlink_to(Path(config["manifest"]))
    with pytest.raises(OSError): gateway.workspace_read("project.md")


def test_revocation_checked_per_call(config):
    gateway = Gateway(config)
    gateway.store.revoke(config["bond_id"])
    with pytest.raises(ValueError): gateway.context_read()


@pytest.mark.parametrize("config", [True], indirect=True)
def test_bounded_artifact_creation(config):
    gateway = Gateway(config)
    assert gateway.workspace_write("proposal.py", "print('example')")["created"] == "proposal.py"
    with pytest.raises(FileExistsError): gateway.workspace_write("proposal.py", "overwrite")
    with pytest.raises(PolicyDenied): gateway.workspace_write("../escape.py", "escape")
    with pytest.raises(PolicyDenied): gateway.workspace_write("private.txt", "my password is example")
    assert (Path(config["output"]) / "proposal.py").read_text() == "print('example')"


def test_actual_stdio_mcp(config, tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    path = tmp_path / "config.json"; path.write_text(json.dumps(config))
    async def run():
        async with stdio_client(StdioServerParameters(command=sys.executable,
            args=["-m", "paralax_mcp.run", "--config", str(path)])) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                available = await session.list_tools()
                assert {t.name for t in available.tools} == {"context_read", "workspace_list", "workspace_read"}
                context = await session.call_tool("context_read", {})
                assert not context.isError
                result = await session.call_tool("workspace_read", {"name": "project.md"})
                assert not result.isError
                forbidden = await session.call_tool("workspace_read", {"name": "../manifest.json"})
                assert forbidden.isError
    asyncio.run(run())
