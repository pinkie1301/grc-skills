# GRC Block Query Workflow

This repository contains a reusable workflow for querying GNU Radio GRC block field data.

## Implemented MVP
- Local database runtime: `~/Documents/grc-block-query/db` (auto-initialized, not published)
- Skill source: `skills/grc-block-query`
- Query script with source order, GUI parameter extraction from block YAML `parameters:`, and db update behavior
- Hook config for field-format validation only

## Source priority
1. local-db
2. radioconda
3. gnuradio-github
4. gnuradio-wiki
5. ettus

## Quick start

Run these commands from the repository root:

1. Query a block:
   - `python ./skills/grc-block-query/scripts/query_grc_blocks.py --block "Constellation Object"`
2. Query a specific field:
   - `python ./skills/grc-block-query/scripts/query_grc_blocks.py --block "Constellation Object" --field "Constellation Type"`
3. Validate field format manually:
   - `python ./skills/grc-block-query/scripts/validate_grc_field_format.py`
4. Rebuild from upstream sources (skip local cache):
   - `python ./skills/grc-block-query/scripts/query_grc_blocks.py --block "Constellation Object" --refresh`

From the skill root (`skills/grc-block-query`), use the shorter script paths:

- `python ./scripts/query_grc_blocks.py --block "Constellation Object"`
- `python ./scripts/query_grc_blocks.py --block "Constellation Object" --field "Constellation Type"`
- `python ./scripts/validate_grc_field_format.py`
- `python ./scripts/query_grc_blocks.py --block "Constellation Object" --refresh`

## Cross-project reuse
- See `./CROSS_PROJECT_PLAN.md` for shared skill + shared database architecture.
- Codex skill home:
   - `C:/Users/<username>/.codex/skills/grc-block-query`
- Optional targets:
   - `codex`
   - `copilot`
   - `claude-code`
- Fixed local DB root (auto-initialize on first query):
   - `C:/Users/<username>/Documents/grc-block-query/db`
- Supported env vars:
   - `GRC_RADIOCONDA_PATH`
- One-command bootstrap from the repository root:
   - `powershell -ExecutionPolicy Bypass -File ./skills/grc-block-query/scripts/bootstrap_shared_grc_skill.ps1`
- Multi-agent bootstrap from the repository root:
   - `powershell -ExecutionPolicy Bypass -File ./skills/grc-block-query/scripts/bootstrap_shared_grc_skill.ps1 -Targets codex,copilot,claude-code`
- From the skill root (`skills/grc-block-query`):
   - `powershell -ExecutionPolicy Bypass -File ./scripts/bootstrap_shared_grc_skill.ps1`
