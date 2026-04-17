# Cross-Project Plan: Shared Skill + Shared Database

This document describes how to reuse the GRC query skill and database across multiple projects.

## Target Architecture

- One project skill source: `skills/grc-block-query`
- Optional user-scope install targets for Codex, Copilot, and Claude Code
- One local database location initialized outside the published repo

## Recommended Layout (Windows)

- Project skill source: `skills/grc-block-query/`
- Codex skill home: `C:/Users/<username>/.codex/skills/grc-block-query/`
- Legacy Copilot mirror: `C:/Users/<username>/.copilot/skills/grc-block-query/`
- Claude Code skill home: `C:/Users/<username>/.claude/skills/grc-block-query/`
- Local DB: `C:/Users/<username>/Documents/grc-block-query/db/`
- radioconda: `C:/Users/<username>/radioconda/Library/share/gnuradio`

The skill should contain:
- `SKILL.md`
- `scripts/query_grc_blocks.py`
- `scripts/validate_grc_field_format.py`

The local DB should contain:
- `blocks/`
- `sources/sources-manifest.json`
- `index.json`
- `audit-log.jsonl`
- `conflicts/`

The published repository should not include generated DB cache files.

## Environment Variables

Set these once (user/session level), so all projects use the same paths:

- `GRC_RADIOCONDA_PATH`: radioconda GNU Radio share root

PowerShell example:

```powershell
$env:GRC_RADIOCONDA_PATH = "$env:USERPROFILE/radioconda/Library/share/gnuradio"
```

Persistent user-level example:

```powershell
setx GRC_RADIOCONDA_PATH "$env:USERPROFILE/radioconda/Library/share/gnuradio"
```

Bootstrap script (recommended for repeat setup):

```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/bootstrap_shared_grc_skill.ps1
```

Install to multiple agent targets:

```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/bootstrap_shared_grc_skill.ps1 -Targets codex,copilot,claude-code
```

Persist a non-default radioconda path:

```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/bootstrap_shared_grc_skill.ps1 -RadiocondaPath "$env:USERPROFILE/radioconda/Library/share/gnuradio" -PersistEnv
```

## Why this works

The scripts resolve paths with deterministic defaults:

1. DB root is fixed to `~/Documents/grc-block-query/db`
2. On first run, missing folders/files are auto-initialized
3. radioconda path still supports CLI/env override (`--radioconda-path`, `GRC_RADIOCONDA_PATH`)
4. The installer copies only `skills/grc-block-query`; it does not copy `db`

So each cloned project can install the same skill while reading/writing the user's local DB.

## Per-Project Integration (Minimal)

Option A (recommended):
- No local database copy
- Install the project skill source to the Codex user skill directory
- Let the query script initialize the local DB on first use

Option B (multi-agent):
- Install the same project skill source to Codex, Copilot, and Claude Code user skill directories
- Keep runtime DB at fixed local root under `Documents/grc-block-query`

## Hooks Strategy

Keep hooks lightweight and project-local.
Only enforce field format validation. Avoid policy-heavy hooks for portability.

## Operations

- Refresh from sources:
  - `python ./skills/grc-block-query/scripts/query_grc_blocks.py --block "FEC Extended Encoder" --refresh`
- Query specific GUI parameter:
  - `python ./skills/grc-block-query/scripts/query_grc_blocks.py --block "FEC Extended Encoder" --field "Threading Type"`
- Validate DB format:
  - `python ./skills/grc-block-query/scripts/validate_grc_field_format.py`

## Governance

- Use one `sources-manifest.json` in the local DB as source policy truth.
- Review `audit-log.jsonl` periodically.
- Keep conflicts under `conflicts/` and resolve manually when needed.
