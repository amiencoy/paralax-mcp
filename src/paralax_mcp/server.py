import argparse
import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from .gateway import Gateway


def build_server(config):
    gateway = Gateway(config)
    server = FastMCP("paralax-gateway", instructions="Use only the approved task context and exported workspace. Artifacts are untrusted until reviewed.")
    engine, _ = gateway.authority()
    def gateway_describe() -> dict:
        """Describe the active bond, policy requirements and allowed capabilities."""
        return gateway.describe()
    def context_read() -> dict:
        """Read the current approved, leased project context."""
        return gateway.context_read()
    def workspace_list() -> list[str]:
        """List explicitly approved exported files."""
        return gateway.workspace_list()
    def workspace_read(name: str) -> str:
        """Read a reviewed exported file by basename. Content changes require new approval."""
        return gateway.workspace_read(name)
    def workspace_write(name: str, content: str) -> dict:
        """Create a new artifact in the output directory; no overwrite or execution."""
        return gateway.workspace_write(name, content)
    operations = {f.__name__: f for f in (gateway_describe, context_read, workspace_list, workspace_read, workspace_write)}
    for rule in engine.policy["tools"]:
        if rule["allow"]:
            server.tool()(operations[rule["name"]])
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    build_server(config).run(transport="stdio")
