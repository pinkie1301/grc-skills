# Field Format

This project validates only field format in hooks.

## Block file format
Each block file under `db/blocks/*.json` must include:
- block_name: string
- canonical_id: string
- updated_at: ISO8601 string
- query_order: list of source IDs
- sources: list of source records
- fields: list of field records

## Source record
- id: one of `local-db`, `radioconda`, `gnuradio-github`, `gnuradio-wiki`, `ettus`
- location: string
- fetched_at: ISO8601 string

## Field record
- name: string
- value: any JSON value (for GUI parameters this is typically an object with `id`, `label`, `dtype`, and optional defaults/options)
- value_type: one of `string`, `number`, `boolean`, `json`, `null`
- source: one of allowed source IDs
- reference: string
- fetched_at: ISO8601 string
- status: one of `verified`, `pending`, `conflict`
- evidence: string
- aliases: optional list of alternate lookup names (for example parameter id + label)
