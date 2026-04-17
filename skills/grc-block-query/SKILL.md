---
name: grc-block-query
description: "Query GNU Radio GRC block and variable field definitions (e.g. constellation object). Use when you need reusable block-field lookup for manual requests or automation workflows, with strict source traceability and local database updates."
---

# GRC Block Query

## Purpose
Provide a reusable lookup workflow for GNU Radio GRC block field data.

## Allowed sources
- `${GRC_RADIOCONDA_PATH}` or `$HOME/radioconda/Library/share/gnuradio`
- https://github.com/gnuradio/gnuradio
- https://wiki.gnuradio.org/
- https://www.ettus.com/

## Query order
1. local-db
2. radioconda
3. gnuradio-github
4. gnuradio-wiki
5. ettus

## Rules
- Never invent field values.
- If no evidence is found, return not_found.
- If local-db misses, query external sources in order.
- Save verified hits back to local-db unless `--no-update-db` is set.
- Hooks only enforce field-format validation.
- For GRC block parameters, prefer `*.block.yml` / `*.block.yaml` `parameters:` definitions.
- Do not use Python or C++ CLI argument semantics as GUI parameter fields.

## Procedure
1. Run [query script](./scripts/query_grc_blocks.py) with `--block` and optional `--field`.
2. Check JSON output for `status`, `source`, and `source_location`.
3. If result is `found` from external sources, confirm `db_file` is returned (when update is enabled).
4. If result is `not_found`, do not infer values.
5. When `--field` is omitted, expect `__grc_parameters__` with the full parameter list from YAML.
6. Use `--refresh` when you need to rebuild data from upstream sources instead of local cache.
7. For cross-project reuse, DB root is fixed to `~/Documents/grc-block-query/db` and is auto-initialized on first query.
8. Set `GRC_RADIOCONDA_PATH` only when your radioconda installation is non-default.

## Examples
- `python ./skills/grc-block-query/scripts/query_grc_blocks.py --block "Constellation Object"`
- `python ./skills/grc-block-query/scripts/query_grc_blocks.py --block "Constellation Object" --field "Constellation Type"`
- `python ./skills/grc-block-query/scripts/query_grc_blocks.py --block "USRP Source" --field "samp_rate" --no-update-db`
- `python ./skills/grc-block-query/scripts/query_grc_blocks.py --block "Constellation Object" --refresh`
