# Reference architecture and scope

```mermaid
flowchart TD
  S["Reviewed source project brief"] --> X["Axionorm context gate"]
  X --> O["OPA decisions"]
  O --> P["Signed Parabiont capsule"]
  P --> A["Local A2A receiver"]
  A --> M["MCP gateway"]
  U["AionUi + Gemini CLI"] --> M
  M --> T["Axionorm tool gate"]
  T --> O
  T --> W["Approved exports / artifacts"]
```

OPA evaluates two policy domains. Axionorm normalizes policy/input, checks review/content, projects the permitted context and enforces decisions. Parabiont carries already-filtered context: raw private history never travels to the destination before being 'intercepted'. PARALAX's initial orchestration connects review → seal → deliver → tool access → revoke.

The source adapter accepts a curated JSON candidate; it cannot automatically read ChatGPT's hidden memory or act as the consumer app's native A2A endpoint. The destination is a local receiver; Google sees state only when the authenticated Gemini runtime requests it through MCP. A2A is pinned to 0.3, MCP to the official Python SDK 1.30.0; no latest-version or full-standard certification is claimed.

## Trust assumptions

- The user/OS controls policy, approved digests, keys, issuer public key, SQLite state and executable paths. An attacker able to replace those control files is outside this reference's boundary.
- Agents never receive signing keys, review mutation tools, OPA management tools, shell execution or package installation capabilities.
- Files are flat exported copies, explicitly reviewed by digest. POSIX no-follow opens reject symlinks; hard links, non-regular files, size excess and changed content fail closed.
- OPA failure denies. Policy digest changes invalidate bonds. Gateway checks each call; modifying policy requires a new reviewed handoff.
- No native model tool may bypass the MCP gateway. Generated Gemini system/admin policy denies native tools and other MCP servers. This is application enforcement; OS/container isolation is needed against a compromised host process.
- Pattern matching is defense in depth. Human review is necessary for sensitive prose not recognized by a deterministic filter. Approved context is sent as data, but natural-language injection cannot be perfectly classified.
- Tool replies and artifacts are untrusted. No automatic memory promotion, execution or installation occurs. No actual user private history is embedded in tests, examples or repositories.

## Deliberate v0.1 limits

No remote A2A authentication/TLS deployment, native ChatGPT integration, automatic subscription reuse, cloud browser, unrestricted shell, provider API call, full AI Council scheduler, distributed revocation or remote forgetting. The user installs/authenticates the desktop runtime. The combined installer and local demo are usable without any provider login.

Future work should first add a verified desktop acceptance run, a structured output-return proposal format, measured policy latency, package-specific installer approvals, and narrowly scoped task runners. Preserve the same purpose/audience/data boundaries when adding another provider.
