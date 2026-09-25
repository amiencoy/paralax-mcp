# PARALAX MCP

Policy-gated MCP tools and desktop integration for [Axionorm](https://github.com/amiencoy/axionorm) and [Parabiont Protocol](https://github.com/amiencoy/parabiont-protocol).

## Status

Experimental v0.1.0. The local OPA → signed A2A → MCP flow works without a model subscription. Gemini CLI/AionUi configuration is generated for installation; live login, entitlement and desktop behavior must be checked on the user's machine. This is an initial PARALAX integration, not the full multi-agent orchestrator.

## Install

Requirements: Python 3.11+, Git, Linux/macOS/WSL2 for the filesystem gateway; Node.js 20+ and npm for Gemini CLI. Install AionUi separately from its official releases.

```bash
git clone --branch v0.1.0 https://github.com/amiencoy/paralax-mcp.git
cd paralax-mcp
python3 install.py --directory "$HOME/paralax" --gemini-cli
```

The installer creates a virtual environment, checks out tagged versions of all three repos, applies tested dependency constraints, and installs checksum-verified OPA in `runtime/opa`. It refuses to overwrite existing repositories. Omit `--gemini-cli` to maintain that CLI separately.

Follow [desktop setup and handoff](docs/DESKTOP.md) and [architecture/limits](docs/ARCHITECTURE.md).

## Local demo

After activating the environment, run from the installation directory (choose a fresh demo directory each time):

```bash
python repos/paralax-mcp/examples/demo.py --directory runtime/demo --policy repos/axionorm/examples/technical-review.yaml --opa runtime/opa/opa
```

A real local HTTP A2A receiver and MCP stdio client verify that approved state reaches `context_read` while synthetic private/injected items do not. No Google/OpenAI call occurs.

## Tools

| Tool | Behavior |
| --- | --- |
| `context_read` | Checks policy, expiry and revocation on every read |
| `workspace_list` | Lists explicitly approved exported filenames |
| `workspace_read` | Reads a regular non-symlink file with matching reviewed digest; scans output |
| `workspace_write` | Optional create-only artifact output; disabled by default; no overwrite or execution |

No shell, package installer, unrestricted browser or arbitrary filesystem tool is exposed. Denied tools are omitted from discovery and checked again during execution. Skills are advisory and cannot grant capabilities. MCP is provider-agnostic; the generated desktop launcher is Gemini-specific.

## Development

Clone the repos as siblings. In one environment: `python -m pip install ../axionorm ../parabiont-protocol . pytest`. Install OPA, then run `python -m pytest tests -q`. `AXIONORM_POLICY` and `OPA_BINARY` override sibling defaults. Fixtures contain no personal history or credentials.

## Licensing

Licensing remains to be selected, consistently with Axionorm and Parabiont. Dependencies retain their upstream licenses.

---

<p align="center"><sub>Built with code, coffee, and a healthy dislike of repetitive work.</sub></p>
