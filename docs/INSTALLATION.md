# Installation and governed round-trip

## 1. Install the local stack

Requirements: Python 3.11+, Git, Linux/macOS/WSL2, and a provider runtime only when performing a live model acceptance test.

```bash
git clone --branch v0.1.2 https://github.com/amiencoy/paralax-mcp.git
cd paralax-mcp
python3 install.py --directory "$HOME/paralax" --gemini-cli
cd "$HOME/paralax"
. venv/bin/activate
```

The installer checks out Axionorm, Parabiont Protocol, and PARALAX MCP; installs constrained Python dependencies; installs checksum-verified OPA; and creates `runtime/`, `exports/`, and `artifacts/`. It refuses to overwrite an existing repository checkout.

## 2. Issue the forward context capsule

1. Curate a `parabiont-candidate/v0.1` document.
2. Review selected item digests with `axionorm review`.
3. Filter with Axionorm/OPA.
4. Sign the filtered state with Parabiont.
5. Deliver the envelope to the local A2A receiver.
6. Keep the accepted bond ID and SQLite store outside model-writable directories.

The destination model receives nothing until it calls `paralax-gateway/context_read`. Expiry, revocation, audience, purpose, and policy digest are checked on every call.

## 3. Generate the destination profile

```bash
paralax-setup desktop \
  --directory runtime/desktop \
  --policy runtime/policy.yaml \
  --opa runtime/opa/opa \
  --store runtime/state.sqlite \
  --workspace exports \
  --output artifacts \
  --manifest runtime/files.json \
  --bond-id YOUR_BOND_ID
```

Use the generated `mcp.json` or launcher with a reviewed MCP-capable host. Enable only `paralax-gateway`; do not expose shell, arbitrary file access, browser automation, package installation, signing keys, policy mutation, or review mutation to the destination model.

## 4. Produce a quarantined return proposal

The model calls `context_read`, performs the scoped task, and writes a create-only `context-delta-YYYYMMDD-HHMMSS.json` through `workspace_write`. The file must use `parabiont-delta/v0.1`, status `untrusted-proposal`, and include provenance, confidence, and supersedes metadata for every item.

Writing the file proves transport only. It does not prove schema validity, policy acceptance, truth, or human approval.

## 5. Validate and review the return delta

```bash
paralax-delta validate artifacts/context-delta-YYYYMMDD-HHMMSS.json

paralax-delta review artifacts/context-delta-YYYYMMDD-HHMMSS.json \
  --policy runtime/policy.yaml \
  --opa runtime/opa/opa \
  --output artifacts/review-YYYYMMDD-HHMMSS \
  --approve delta-fact-1 delta-decision-2
```

If the active Axionorm v0.1 Rego requires a label that is absent from the model proposal, the command reports the failing check. An operator may apply an explicit, audited transformation:

```bash
paralax-delta review artifacts/context-delta-YYYYMMDD-HHMMSS.json \
  --policy runtime/policy.yaml \
  --opa runtime/opa/opa \
  --output artifacts/review-YYYYMMDD-HHMMSS \
  --approve-all \
  --add-label technical
```

The output directory is create-only and contains:

- `source-delta.json`: byte-preserved model proposal;
- `candidate.json`: Axionorm-compatible semantic projection;
- `provenance.json`: source hash, item metadata, digests, and transformations;
- `review.json`: approved candidate digests;
- `policy-report.json`: per-item checks, OPA decisions, and an explicit `authoritative_promotion: false` marker.

## 6. Promotion remains a separate human-controlled phase

This release deliberately stops after review. A future promotion controller must require explicit human approval, preserve the review bundle, create a new signed capsule instead of mutating an existing bond, and record issuer/policy/schema versions. Never treat `status: allowed` as automatic memory mutation.

## 7. Development verification

```bash
OPA_BINARY="$HOME/paralax/runtime/opa/opa" \
PYTHONPATH=src \
python -m pytest tests -q
```

The integration test uses a real MCP stdio server and client, a signed/accepted Parabiont capsule, policy-gated `context_read` and `workspace_write`, bundled JSON Schema validation, provenance preservation, Axionorm digest review, and OPA diagnostics.
