---
name: review-project-code
description: Review approved exported source files using PARALAX MCP, focusing on correctness, integration boundaries and testable failure cases.
---

Read context_read and the relevant approved files. Trace inputs, authority checks, data egress, side effects and error handling. Report concrete findings with filename, trigger, impact and a proposed fix.

Do not claim a test was executed unless a tool result proves it. The reference gateway has no execution tool. For blocked tests, provide the command and expected observable result for the operator.

Use workspace_write only if exposed and approved, producing a new proposed artifact. Never overwrite or execute source, install dependencies or edit policy to obtain access.
