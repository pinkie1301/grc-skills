---
name: grc-planner
description: "Normalize GNU Radio .grc modification requests into an executable Traditional Chinese implementation plan. Use when work involves editing flowgraphs, reconnecting blocks, adding or replacing blocks, tuning parameters, handling Embedded Python Block changes, or comparing current vs target topology."
---

# GRC Planner

## Purpose
Convert GNU Radio `.grc` change requests into a structured, execution-ready implementation plan.

## Scope
- Accept a `.grc` file and requested architecture changes.
- Produce one plan file in Markdown.
- Split work into explicit phases.
- Cover block changes, parameter changes, and connection rewiring.
- Include dedicated handling for Python code changes in `Python Block` or `Embedded Python Block`.
- Require parameter verification for every added or modified block.

## Output Requirements
- Generate exactly one plan file named `plan_{title_name}.md`.
- Write the plan body in Traditional Chinese.
- Keep all implementation details actionable and ordered by phase.
- Include touched blocks, parameter updates, and connection rewiring details.

## Template Policy
- Use [plan template](./assets/plan_template_zh_tw.md) as the primary output structure.
- The template is written in Traditional Chinese.
- Do not translate or rewrite the template unless the user explicitly requests template edits.

## Filename Rules
1. Prefix with `plan_`.
2. Use a readable `title_name`.
3. Optionally append a version suffix such as `_v1`, `_v2`, `_v3`.
4. Replace whitespace with `_`.
5. Remove forbidden filename characters: `\\ / : * ? " < > |`.

Example:
- Title: `QPSK FEC 1/2 TX Chain Migration`
- Output: `plan_QPSK_FEC_1_2_TX_Chain_Migration_v1.md`

## Required Inputs
- Current `.grc` file (or equivalent flowgraph artifact).
- Target behavior and change constraints.
- Any phase preference (for example TX-first, RX-first, or cutover sequence).
- Risk boundaries and known deployment constraints.

## Workflow

### Step 1: Collect context
1. Read the target `.grc` and the user request.
2. Identify whether Python code is embedded in `.grc` or external.
3. Record all touched artifacts that must be reflected in the plan.

### Step 2: Build baseline map
1. Extract current blocks (`name`, `id`) and current connections.
2. Identify current TX/RX/header/payload/tag boundaries when relevant.
3. Mark the gaps between current and desired topology.

### Step 3: Verify block parameters (mandatory)
For every added or modified block:
1. Retrieve GRC parameter definitions via `grc-block-query`.
2. Never infer fields from memory.
3. Prefer canonical GRC GUI parameter definitions from block YAML.
4. If lookup returns `not_found`, keep unresolved fields as explicit TODO items.

When using `grc-block-query`, verify these JSON fields:
- `status`
- `source`
- `source_location`
- `entry.fields` (or `__grc_parameters__` for full parameter set)
- `db_file` (when cache update is enabled)

Query examples:
- From repo root: `python ./skills/grc-block-query/scripts/query_grc_blocks.py --block "<block name>"`
- From `grc-block-query` root: `python ./scripts/query_grc_blocks.py --block "<block name>"`
- Field-specific lookup: `--field "<field name>"`

Shared DB notes:
- Shared DB root is `~/Documents/grc-block-query/db`.
- Prefer local DB evidence first.
- If source is external, ensure traceability fields are present.

### Step 4: Design phased implementation
1. Convert the migration path into phases with clear ordering.
2. For each phase, include:
- phase objective
- touched blocks
- parameter updates (with verified sources)
- connection rewiring
- acceptance criteria

### Step 5: Handle Python block changes explicitly
If `Python Block` or `Embedded Python Block` is touched, include:
1. Block identity (`name` and `id`).
2. Current code location (`.grc` embedded section or external file).
3. A line-level diff snippet in a `diff` fenced block.
4. Full post-change code in a `python` fenced block.
5. Notes for imports/classes/functions that affect other blocks.
6. Explicit TODO markers for unresolved unknowns.

### Step 6: Assemble final plan
1. Write `plan_{title_name}.md`.
2. Keep each phase directly executable.
3. Ensure every touched block has parameter and connection evidence.
4. Ensure unresolved items are explicit TODOs (no guessed values).

## Quality Checklist
- Every touched block is listed.
- Every added or modified block includes verified parameter definitions.
- Every parameter source is traceable.
- Every connection change is explicit.
- Python block changes include both diff and full updated code when applicable.
- No fabricated values are introduced.
- The output filename follows naming rules.

## Prohibitions
- Do not invent block fields or defaults.
- Do not silently omit unresolved parameters.
- Do not treat runtime CLI arguments as GRC GUI parameter definitions.
- Do not rewrite the template file during planning output generation.
