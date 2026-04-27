---
name: grc-planner
description: "Normalize GNU Radio .grc modification requests into an executable Traditional Chinese implementation plan with an interactive readiness gate before writing files. Use when work involves editing flowgraphs, reconnecting blocks, adding or replacing blocks, tuning parameters, handling Embedded Python Block changes, or comparing current vs target topology."
---

# GRC Planner

## Purpose
Convert GNU Radio `.grc` change requests into a structured, execution-ready implementation plan.

## Scope
- Accept a `.grc` file and requested architecture changes.
- First run an interactive readiness check.
- Produce one Markdown plan file only after all planning blockers are resolved, or after the user explicitly asks for a draft with TODOs.
- Split work into explicit phases.
- Cover block changes, parameter changes, and connection rewiring.
- Include dedicated handling for Python code changes in `Python Block` or `Embedded Python Block`.
- Require parameter verification for every added or modified block.

## Output Requirements
- Determine `READY_TO_WRITE` before creating or writing any plan file.
- Generate exactly one plan file named `plan_{title_name}.md` only when `READY_TO_WRITE` is true.
- Write the plan body in Traditional Chinese.
- Keep all implementation details actionable and ordered by phase.
- Include touched blocks, parameter updates, and connection rewiring details.
- If `READY_TO_WRITE` is false, respond only with a concise blocker summary and at most 3 clarification questions. Do not include a partial plan, template body, phase table, or Markdown plan file.
- Do not write the final plan file until interaction blockers are resolved, unless the user explicitly asks for a draft with TODOs.

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

## Interactive Planning Policy
- Treat the readiness gate as a hard stop, not a suggestion.
- Use an interactive planning loop when missing or ambiguous information could change topology, block selection, verified parameters, connection rewiring, Python block behavior, phase ordering, or deployment risk.
- Ask concise clarification questions before writing `plan_{title_name}.md` when required inputs are missing.
- Ask at most 3 questions at a time.
- After asking clarification questions, stop the current response. Do not continue into plan generation in the same response.
- Prefer concrete implementation questions over broad discussion.
- State safe assumptions and continue when the assumption does not change architecture, runtime behavior, or risk boundaries.
- If the user asks for a draft despite unresolved questions, continue with explicit `TODO` markers for each unresolved decision.
- Do not use unresolved assumptions as verified block parameters or connection facts.
- After each user answer, update the working plan state and continue from the first still-blocked workflow step.

## Workflow

### Step 0: Interactive clarification gate
1. Before writing any file or plan body, decide whether the plan is `READY_TO_WRITE`.
2. Set `READY_TO_WRITE=true` only when all of these are satisfied:
   - Current `.grc` file or equivalent flowgraph artifact is available.
   - Target behavior is concrete enough to determine topology.
   - Touched blocks can be identified.
   - Ambiguous block choices are resolved.
   - Phase ordering risk is resolved, explicitly specified, or safely irrelevant.
   - Required block parameters can be verified, or unresolved parameters are allowed because the user explicitly requested a draft with TODOs.
3. Set `READY_TO_WRITE=false` when any missing or ambiguous detail could change architecture, runtime behavior, verified parameters, connection facts, phase ordering, or deployment risk.
4. If `READY_TO_WRITE=false`, stop and ask only the questions needed to unblock the next planning step.
5. Ask at most 3 questions and do not generate a plan body, template body, or output file in that response.
6. Continue without asking only when missing details can be safely represented as explicit TODOs and the user has requested a draft.
7. Repeat this gate after baseline mapping and parameter verification if new blockers appear.

### Step 1: Collect context
1. Read the target `.grc` and the user request.
2. Identify whether Python code is embedded in `.grc` or external.
3. Record all touched artifacts that must be reflected in the plan.

### Step 2: Build baseline map
1. Extract current blocks (`name`, `id`) and current connections.
2. Identify current TX/RX/header/payload/tag boundaries when relevant.
3. Mark the gaps between current and desired topology.
4. If the target topology cannot be determined from the request, ask follow-up questions before designing phases.

### Step 3: Verify block parameters (mandatory)
For every added or modified block:
1. Retrieve GRC parameter definitions via `grc-block-query`.
2. Never infer fields from memory.
3. Prefer canonical GRC GUI parameter definitions from block YAML.
4. If lookup returns `not_found`, keep unresolved fields as explicit TODO items.
5. If multiple plausible GRC blocks match the requested behavior, ask the user to choose before planning rewiring.

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
3. If phase order affects risk or deployment continuity and no preference is provided, ask before finalizing the plan.

### Step 5: Handle Python block changes explicitly
If `Python Block` or `Embedded Python Block` is touched, include:
1. Block identity (`name` and `id`).
2. Current code location (`.grc` embedded section or external file).
3. A line-level separated comparison with `修改前` and `修改後` sections. Do not use `diff` fenced blocks, `+` prefixes, or `-` prefixes for code changes.
4. Full post-change code in a `python` fenced block.
5. Notes for imports/classes/functions that affect other blocks.
6. Explicit TODO markers for unresolved unknowns.

### Step 6: Assemble final plan
1. Re-run Step 0 and confirm `READY_TO_WRITE=true`.
2. If `READY_TO_WRITE=false`, return to Step 0 and stop after asking clarification questions.
3. Write `plan_{title_name}.md`.
4. Keep each phase directly executable.
5. Ensure every touched block has parameter and connection evidence.
6. Ensure unresolved items are explicit TODOs (no guessed values).

## Quality Checklist
- Every touched block is listed.
- Every added or modified block includes verified parameter definitions.
- Every parameter source is traceable.
- Every connection change is explicit.
- Python block changes include separated before/after code comparison and full updated code when applicable.
- Interaction blockers were resolved, or unresolved decisions are marked as TODOs because the user requested a draft.
- No fabricated values are introduced.
- The output filename follows naming rules.

## Prohibitions
- Do not invent block fields or defaults.
- Do not silently omit unresolved parameters.
- Do not treat runtime CLI arguments as GRC GUI parameter definitions.
- Do not rewrite the template file during planning output generation.
