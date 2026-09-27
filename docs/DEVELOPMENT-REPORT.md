# Context carrier return-path development report

Date: 2026-09-27  
Status: experimental, locally verified, non-promoting

## Outcome

The initial two-way governed context-carrier path is now implemented as a complete local review loop:

```text
reviewed candidate
  -> Axionorm/OPA
  -> signed Parabiont capsule
  -> accepted bond
  -> PARALAX MCP context_read
  -> model workspace_write
  -> quarantined context-delta
  -> JSON Schema validation
  -> provenance-preserving adapter
  -> Axionorm review digest
  -> OPA decision diagnostics
```

The path stops before authoritative promotion. That boundary is intentional.

## Acceptance evidence

A local acceptance run confirmed that approved context could be read through `paralax-gateway/context_read` and that a return artifact could be created through `workspace_write`.

The first proposal demonstrated transport but failed schema validation because it used unsupported fields and confidence values. The second corrected those fields but encoded `provenance` as a string instead of an array. The third proposal passed Draft 2020-12 validation and privacy canary checks.

Direct Axionorm review exposed two integration gaps:

1. Axionorm v0.1 accepts `parabiont-candidate/v0.1`, not the richer delta schema.
2. Effective Rego requires the `technical` label even though that requirement is not represented in the YAML context policy.

The official adapter now handles the first gap and diagnoses the second. Label augmentation is possible only through explicit `--add-label`, and every addition is recorded in `provenance.json`.

## Delivered implementation

- `paralax-delta validate`: bundled-schema validation with precise JSON paths.
- `paralax-delta review`: create-only review bundle and non-promoting exit status.
- Byte-preserved source delta and SHA-256 binding.
- Per-item preservation of provenance, confidence, and supersedes metadata.
- Source/candidate item digests and explicit transformation records.
- Axionorm review manifests generated only for explicitly approved IDs.
- Per-item policy checks plus the authoritative OPA/Axionorm audit.
- Explicit `authoritative_promotion: false` markers.
- Packaged Draft 2020-12 schema and `jsonschema` runtime dependency.
- Real MCP stdio round-trip integration coverage.

## Verification

The repository suite completed with:

```text
8 passed
```

The command was also exercised against the locally generated acceptance delta. Approved synthetic items returned `allowed: true`; source and policy digests matched the earlier verification.

## Tool flow toward PARALAX Fleet

### Axionorm

Current role: policy authority for context release, tool access, review digests, sensitive-pattern defense, and fail-closed OPA evaluation.

Fleet direction: signed/versioned policy bundles, machine-readable effective requirements, tenant/purpose/audience inheritance, decision attestations, and centrally observable—but locally enforceable—policy outcomes. Fleet nodes must pin the same policy digest used by a bond.

### Parabiont Protocol

Current role: signed, purpose-bound, audience-bound, expiring carrier for already reviewed state; local replay/revocation protection and SQLite bond storage.

Fleet direction: issuer trust chains, node identities, route-aware capsules, distributed revocation propagation, lease renewal semantics, schema negotiation, and a clear distinction between transport acceptance and semantic promotion.

### PARALAX MCP gateway

Current role: provider-neutral capability boundary exposing only `context_read`, approved workspace reads, and create-only artifact writes.

Fleet direction: per-node capability descriptors, gateway health/lease status, isolated workspace mounts, provider-host adapters, rate and byte budgets, and auditable tool-call envelopes. A Fleet controller should schedule against declared capabilities rather than provider brand names.

### `paralax-delta`

Current role: quarantine boundary for model output, schema validator, provenance-preserving projection into Axionorm candidate form, and policy diagnostics producer.

Fleet direction: schema/adapter registry, signed transformation recipes, multi-hop provenance, conflict/supersedes resolution, partial approvals, and a dedicated promotion controller. The adapter must remain separate from promotion authority.

### OPA

Current role: deterministic local evaluation behind Axionorm.

Fleet direction: versioned bundle distribution, digest pinning, conformance tests, decision latency metrics, and explicit exposure of effective requirements such as mandatory labels. Fleet must fail closed when a policy bundle is unavailable or mismatched.

### Model runtime adapters

Current role: Gemini has a live acceptance run; the MCP protocol and generated `mcp.json` are provider-neutral, but each host still needs its own authentication, permission, and tool-isolation verification.

Fleet direction: a conformance contract based on MCP transport, permission UX, structured output fidelity, create-only write behavior, and disablement of bypass tools. A model/provider compatibility matrix is intentionally deferred until those tests are automated; marketing claims or nominal MCP support are not sufficient evidence.

## Deferred work

- authoritative promotion command and signed return capsule;
- effective-policy contract that exposes Rego-only requirements;
- schema and adapter version negotiation;
- Fleet controller, node registry, and distributed revocation;
- provider/model conformance matrix;
- plug-and-play third-party MCP packaging, signing, permission manifests, and marketplace governance.

The future marketplace should list only packages that pass reproducible capability, isolation, provenance, and policy-conformance tests. Installation metadata alone must never grant runtime authority.
