# CS-340 AnimalShelter (enhanced)

CS-499 Milestone Four. Original files stay at the CS-340 repo root (and in `original/` in the Brightspace zip). This folder is the same AAC CRUD module with secrets out of source, indexes, an allow-list, roles, and a dashboard you run as a Python process.

## Setup

```
python -m pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with a real Mongo user. Do not commit `.env`.

## Tests (no live Mongo)

```
python -m pytest tests -q
```

Uses mongomock. Covers fail-closed constructor, unique `animal_id`, staff cannot write, operator keys rejected, `create(None)` no longer throws a `NameError`, delete does not default to wiping the collection.

## Live Mongo + dashboard

Set `MONGO_USER` and `MONGO_PASS` (and host/port if needed), then:

```
python dashboard.py
```

Open http://127.0.0.1:8050. Default `DASH_ROLE=staff` is read-only. Admin is required for create/update/delete.

`ensure_indexes` creates a unique index on `animal_id` plus indexes on breed, age, and sex. If the AAC dump already has duplicate `animal_id` values, unique index creation fails until those rows are cleaned. That is the trade-off: a dirty import is rejected instead of folded in a `$group`.

## What changed

- No default username/password in source. Missing env vars fail closed.
- `read` uses `find` plus a unique index, not aggregation-as-dedup.
- Lookup dicts are allow-listed. `$where` / `$ne` / unknown fields are rejected.
- Staff = read/filter. Admin = write. `many` defaults to false.
- Analysis aggregation: counts by breed and outcome type.
- Dashboard is `dashboard.py`, not the notebook.
- Duplicate `import logging` removed. `__del__` logs a close error, not "Error during delete". `create(None)` raises `QueryError` without interpolating an undefined `e`.
