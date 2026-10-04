# CS-340 AnimalShelter (enhanced)

CS-499 Milestone Four. Original files stay at the CS-340 repo root (and in `original/` in the Brightspace zip). This folder is the same AAC CRUD module with secrets out of source, indexes, an allow-list, roles, and a dashboard you run as a Python process.

## How to run (no Mongo required)

Python 3. From this `enhanced` folder:

```
python -m pip install -r requirements.txt
python -m pytest tests -q
python dashboard.py
```

Open http://127.0.0.1:8050. Tests and the dashboard both use mongomock (`demo.py` seeds seven sample dogs so Water / Mountain / Disaster filters return rows). AnimalShelter still fails closed if you construct it without a client and without `MONGO_USER` / `MONGO_PASS`.

## Live Mongo

```
copy .env.example .env
```

Set `MONGO_USER` and `MONGO_PASS` (and host/port if needed). Do not commit `.env`. Then `python dashboard.py` talks to that host. `DASH_BACKEND=live` forces a live connection and still fails closed if those two variables are missing.

Default `DASH_ROLE=staff` is read-only. Admin is required for create/update/delete.

`ensure_indexes` creates a unique index on `animal_id` plus indexes on breed, age, and sex. If the AAC dump already has duplicate `animal_id` values, unique index creation fails until those rows are cleaned. That is the trade-off: a dirty import is rejected instead of folded in a `$group`.

## What changed

- No default username/password in source. Missing env vars fail closed.
- `read` uses `find` plus a unique index, not aggregation-as-dedup.
- Lookup dicts are allow-listed. `$where` / `$ne` / unknown fields are rejected.
- Staff = read/filter. Admin = write. `many` defaults to false.
- Analysis aggregation: counts by breed and outcome type.
- Dashboard is `dashboard.py`, not the notebook. Missing credentials open a seeded in-memory copy so the UI can be run without a cluster.
- Duplicate `import logging` removed. `__del__` logs a close error, not "Error during delete". `create(None)` raises `QueryError` without interpolating an undefined `e`.
