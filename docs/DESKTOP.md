# Desktop setup: Gemini CLI + AionUi

This guide targets Linux/macOS/WSL2, Python 3.11+, Node 20+, Gemini CLI 0.50.0. AionUi is the desktop shell; Gemini CLI performs the agent loop and authenticates through its official Google flow. The MCP layer is portable to another conforming host.

## 1. Install and check identity

Run the installer in the README. In a terminal:

```bash
cd "$HOME/paralax"
. venv/bin/activate
export PATH="$HOME/paralax/client/node_modules/.bin:$PATH"
gemini --version
gemini
```

Use **Login with Google** through Gemini CLI's official flow, then exit. Do not paste credentials into a prompt or extract browser cookies. Free individual account login is documented. Google AI Pro/Ultra may raise CLI limits; **Google AI Plus is not asserted to have those benefits**. Check your actual CLI quota/account. API-key billing is separate; no paid API is required by this reference's local demo. The existing Gemini app conversation is not the CLI session.

Sources: https://geminicli.com/docs/get-started/authentication/ , https://geminicli.com/plans/ , https://geminicli.com/docs/resources/quota-and-pricing/

## 2. Review technical context

Start from `repos/paralax-mcp/examples/project-context.json`. It contains the technical project goals only. It was not generated from a bulk private chat export. Read/edit it locally and save as `runtime/candidate.json`. Then:

```bash
axionorm review runtime/candidate.json --approve architecture continuity desktop privacy --out runtime/review.local.json
parabiont keygen runtime/keys
parabiont pack --candidate runtime/candidate.json --review runtime/review.local.json --policy repos/axionorm/examples/technical-review.yaml --opa runtime/opa/opa --private-key runtime/keys/issuer.pem --out runtime/envelope.json
```

Inspect `runtime/envelope.json`. It contains only the selected context and signature, no rejected text. Save the printed bond ID. Never approve an item only because its model-generated label says `technical`.

The policy lease defaults to 10 minutes. Set `lease_seconds` up to 3600 **before** issuing the capsule if the task needs more time. A new reviewed handoff is needed after expiry. The model may retain previously read context: lease enforcement controls new access, not remote forgetting.

## 3. A2A handoff to the local destination

```bash
parabiont serve --policy repos/axionorm/examples/technical-review.yaml --opa runtime/opa/opa --public-key runtime/keys/issuer.pub.pem --store runtime/state.sqlite
```

In another activated terminal from the same directory:

```bash
parabiont send runtime/envelope.json
```

Look for `accepted: true`. This delivers to the local agent receiver, **not directly to Google**. The Gemini runtime later reads through MCP. The server may be stopped after the receipt; the gateway uses its stored approved state.

## 4. Approved workspace and profile

Create `runtime/files.json` with `{"version":"paralax-files/v0.1","files":{}}`. Copy only files you intend the agent to read into `exports/`, with simple basenames. Review them and run:

```bash
paralax-setup approve-file exports/project.md --manifest runtime/files.json
paralax-setup desktop --directory runtime/desktop --policy repos/axionorm/examples/technical-review.yaml --opa runtime/opa/opa --store runtime/state.sqlite --workspace exports --output artifacts --manifest runtime/files.json --bond-id YOUR_BOND_ID
```

The profile contains `gateway.json`, portable `mcp.json`, system settings, a deny-first TOML policy, a clean `session/` directory and a `gemini-governed` launcher. Keep these control files outside `exports/` and `artifacts/`. Never give the agent your home directory as its workspace. A new profile directory is required when the bond changes.

Test `runtime/desktop/gemini-governed` in a terminal first. Review and trust only this generated session folder when the CLI asks; untrusted folders suppress MCP servers. Ask it to read `context_read` and summarize the approved task. `/mcp` should list only `paralax-gateway`. Requests for shell commands, installing dependencies and arbitrary file reads must be denied. If additional tools appear, stop and fix the profile before supplying personal data. The reference does not claim a malicious CLI/desktop process is sandboxed by YAML; for stronger isolation use a dedicated OS account or container with only export/artifact mounts.

## 5. Desktop UI

Install **AionUi** from https://github.com/iOfficeAI/AionUi/releases . In Settings → Agent Management → Custom Agents, add the absolute path to `runtime/desktop/gemini-governed`, with Gemini CLI's ACP argument `--acp`, and choose the generated `session/` working directory. Use the **external CLI** integration, which preserves the CLI's own authentication and configuration. Avoid switching this conversation to a built-in provider adapter with different tools and auth.

Confirm AionUi surfaces the same allowed MCP tools and asks before artifact writes. UI/ACP integration must be smoke-tested on your desktop; no authenticated Google session or desktop app was available in the build environment. The pinned CLI was checked locally for its version, ACP flag and configuration schema; live desktop authentication remains an operator step.

AionUi integration guidance: https://github.com/iOfficeAI/AionUi/wiki/ACP-Setup . Alternatives such as an MCP-capable desktop host can import generated `mcp.json`; each host still needs its own provider entitlement and must disable bypass tools. Llama is a model family, not a replacement desktop interface by itself.

## 6. Enable development capabilities deliberately

To create code/docs artifacts, change only `workspace_write.allow` to `true` in the YAML, then issue a **new capsule** and profile. Writes still require the desktop/CLI approval prompt and are create-only inside `artifacts/`; they cannot modify policy or run their contents. Review generated code outside the model before executing it. Dependency installation, network tools and test execution are future individually scoped adapters, not an unrestricted `run_shell` capability.

Optional skills live in `skills/`. Review one and copy its workflow text into the generated `PARALAX-SESSION.md` to use it with the conservative profile. Automatic skill discovery is off by default because global/workspace skills can add unreviewed context. For native Gemini skills, install only reviewed skills through the official CLI mechanism and enable skills under a separately tested policy; do not assume instructions grant permissions.

## Revocation and return context

`parabiont revoke YOUR_BOND_ID --store runtime/state.sqlite` blocks subsequent tool reads. End the old model session. Replies and generated artifacts are untrusted output: review and re-extract decisions into a new candidate before a return handoff. v0.1 does not automatically merge provider output into authoritative memory.
