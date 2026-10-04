"""AnimalShelter CRUD for the AAC animals collection.

Credentials come from the environment. There are no default username/password
values in this file. Staff may read and filter. Admin may write.
"""
from __future__ import annotations

import os
from typing import Any, Mapping, Optional
from urllib.parse import quote_plus

from pymongo import MongoClient
from pymongo.errors import PyMongoError
import logging

logger = logging.getLogger(__name__)

ROLE_STAFF = "staff"
ROLE_ADMIN = "admin"

ALLOWED_FILTER_FIELDS = {
    "animal_id",
    "animal_type",
    "breed",
    "sex_upon_outcome",
    "age_upon_outcome_in_weeks",
    "outcome_type",
    "outcome_subtype",
}

ALLOWED_OPS = {"$gte", "$lte", "$in", "$eq"}

NUMERIC_FIELDS = {"age_upon_outcome_in_weeks"}


class ConfigurationError(RuntimeError):
    pass


class QueryError(ValueError):
    pass


class PermissionDenied(PermissionError):
    pass


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name, default)
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def sanitize_lookup(lookup: Any) -> dict:
    """Reject operator keys and unknown fields. Empty dict means 'no filter'."""
    if lookup is None or not isinstance(lookup, dict):
        raise QueryError("lookup must be a dict")
    clean: dict[str, Any] = {}
    for key, value in lookup.items():
        if key.startswith("$"):
            raise QueryError("operator keys are not allowed at the top level")
        if key not in ALLOWED_FILTER_FIELDS:
            raise QueryError(f"field not allowed: {key}")
        if isinstance(value, dict):
            for op, op_val in value.items():
                if op not in ALLOWED_OPS:
                    raise QueryError(f"operator not allowed: {op}")
                if key in NUMERIC_FIELDS and op in {"$gte", "$lte"}:
                    if not isinstance(op_val, (int, float)):
                        raise QueryError(f"{key} {op} needs a number")
                if op == "$in" and not isinstance(op_val, (list, tuple)):
                    raise QueryError("$in needs a list")
        clean[key] = value
    return clean


class AnimalShelter:
    """CRUD operations for the Animal collection in MongoDB."""

    def __init__(
        self,
        role: str,
        *,
        client: Any = None,
        db: Optional[str] = None,
        col: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ) -> None:
        if role not in {ROLE_STAFF, ROLE_ADMIN}:
            raise ConfigurationError("role must be 'staff' or 'admin'")
        self.role = role

        db_name = db or _env("MONGO_DB", "aac")
        col_name = col or _env("MONGO_COL", "animals")

        if client is not None:
            self.client = client
        else:
            user = user if user is not None else _env("MONGO_USER")
            password = password if password is not None else _env("MONGO_PASS")
            host = host if host is not None else _env("MONGO_HOST", "localhost")
            port_s = _env("MONGO_PORT", "27017") if port is None else str(port)
            if not user or not password:
                raise ConfigurationError(
                    "MONGO_USER and MONGO_PASS are required. Set them in the environment."
                )
            try:
                port_i = int(port_s)
            except (TypeError, ValueError) as e:
                raise ConfigurationError("MONGO_PORT must be an integer") from e
            uri = "mongodb://%s:%s@%s:%d" % (quote_plus(user), quote_plus(password), host, port_i)
            try:
                self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
                self.client.admin.command("ping")
            except PyMongoError:
                logger.error("Failed to connect to MongoDB at %s:%s as %s", host, port_i, user)
                raise
            logger.info("Connected to MongoDB at %s:%s db=%s as %s", host, port_i, db_name, user)

        self.database = self.client[db_name]
        self.collection = self.database[col_name]

    def _require_write(self) -> None:
        if self.role != ROLE_ADMIN:
            raise PermissionDenied("staff can read and filter; admin is required to write")

    def ensure_indexes(self) -> None:
        self.collection.create_index("animal_id", unique=True, name="animal_id_unique")
        self.collection.create_index("breed", name="breed_idx")
        self.collection.create_index("age_upon_outcome_in_weeks", name="age_weeks_idx")
        self.collection.create_index("sex_upon_outcome", name="sex_idx")
        logger.info("Indexes ensured on animal_id (unique), breed, age, sex")

    def create(self, data: Optional[Mapping[str, Any]]) -> bool:
        self._require_write()
        if data is None or not isinstance(data, dict) or not data:
            raise QueryError("Nothing to save: data is empty")
        try:
            result = self.collection.insert_one(dict(data))
            if result.acknowledged and result.inserted_id:
                logger.info("Inserted document id=%s", result.inserted_id)
                return True
            logger.error("Insert not acknowledged")
            return False
        except PyMongoError as e:
            logger.error("Error during insert: %s", type(e).__name__)
            return False

    def read(self, lookup: Optional[dict] = None) -> list:
        try:
            filt = sanitize_lookup(lookup if lookup is not None else {})
        except QueryError as e:
            logger.warning("Invalid lookup: %s", e)
            return []
        try:
            results = list(self.collection.find(filt))
            logger.info("Read %d documents role=%s", len(results), self.role)
            return results
        except PyMongoError as e:
            logger.error("Error during query: %s", type(e).__name__)
            return []

    def update(self, lookup: dict, update_data: dict, many: bool = False) -> int:
        self._require_write()
        try:
            filt = sanitize_lookup(lookup)
        except QueryError as e:
            logger.warning("Invalid lookup for update: %s", e)
            return 0
        if not filt:
            logger.warning("Refusing update with empty lookup")
            return 0
        if update_data is None or not isinstance(update_data, dict) or not update_data:
            logger.warning("Invalid update_data: must be a non-empty dict")
            return 0
        try:
            if many:
                result = self.collection.update_many(filt, update_data)
            else:
                result = self.collection.update_one(filt, update_data)
            if result.acknowledged:
                logger.info("Updated %d documents", result.modified_count)
                return result.modified_count
            logger.error("Update not acknowledged")
            return 0
        except PyMongoError as e:
            logger.error("Error during update: %s", type(e).__name__)
            return 0

    def delete(self, lookup: dict, many: bool = False) -> int:
        self._require_write()
        try:
            filt = sanitize_lookup(lookup)
        except QueryError as e:
            logger.warning("Invalid lookup for delete: %s", e)
            return 0
        if not filt:
            logger.warning("Refusing delete with empty lookup")
            return 0
        try:
            if many:
                result = self.collection.delete_many(filt)
            else:
                result = self.collection.delete_one(filt)
            if result.acknowledged:
                logger.info("Deleted %d documents", result.deleted_count)
                return result.deleted_count
            logger.error("Delete not acknowledged")
            return 0
        except PyMongoError as e:
            logger.error("Error during delete: %s", type(e).__name__)
            return 0

    def counts_by_breed_and_outcome(self, limit: int = 20) -> list:
        """Analysis aggregation: counts by breed and outcome_type. Not a unique index."""
        pipeline = [
            {
                "$group": {
                    "_id": {"breed": "$breed", "outcome_type": "$outcome_type"},
                    "n": {"$sum": 1},
                }
            },
            {"$sort": {"n": -1}},
            {"$limit": limit},
        ]
        try:
            rows = list(self.collection.aggregate(pipeline))
            logger.info("Aggregation returned %d groups", len(rows))
            return rows
        except PyMongoError as e:
            logger.error("Error during aggregation: %s", type(e).__name__)
            return []

    def close(self) -> None:
        try:
            if getattr(self, "client", None) is not None:
                self.client.close()
        except PyMongoError as e:
            logger.error("Error closing MongoDB client: %s", type(e).__name__)

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
