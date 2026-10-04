import os
import pytest
import mongomock

from animal_shelter import (
    AnimalShelter,
    ConfigurationError,
    PermissionDenied,
    QueryError,
    ROLE_ADMIN,
    ROLE_STAFF,
    sanitize_lookup,
)


def admin_shelter():
    client = mongomock.MongoClient()
    return AnimalShelter(ROLE_ADMIN, client=client, db="aac", col="animals")


def staff_shelter(client):
    return AnimalShelter(ROLE_STAFF, client=client, db="aac", col="animals")


def sample_dog(animal_id="A1", breed="Labrador Retriever Mix"):
    return {
        "animal_id": animal_id,
        "animal_type": "Dog",
        "breed": breed,
        "sex_upon_outcome": "Intact Female",
        "age_upon_outcome_in_weeks": 52,
        "outcome_type": "Adoption",
    }


def test_fail_closed_without_env(monkeypatch):
    monkeypatch.delenv("MONGO_USER", raising=False)
    monkeypatch.delenv("MONGO_PASS", raising=False)
    with pytest.raises(ConfigurationError):
        AnimalShelter(ROLE_ADMIN)


def test_create_none_raises_without_nameerror():
    s = admin_shelter()
    with pytest.raises(QueryError):
        s.create(None)


def test_staff_cannot_write():
    s = admin_shelter()
    staff = staff_shelter(s.client)
    with pytest.raises(PermissionDenied):
        staff.create(sample_dog())
    with pytest.raises(PermissionDenied):
        staff.delete({"animal_id": "A1"})


def test_admin_create_read_unique_index():
    s = admin_shelter()
    s.ensure_indexes()
    assert s.create(sample_dog("A1")) is True
    assert s.create(sample_dog("A1")) is False
    rows = s.read({"animal_id": "A1"})
    assert len(rows) == 1
    assert rows[0]["breed"] == "Labrador Retriever Mix"


def test_allow_list_rejects_operator_key():
    with pytest.raises(QueryError):
        sanitize_lookup({"$where": "1 == 1"})
    with pytest.raises(QueryError):
        sanitize_lookup({"breed": {"$ne": "x"}})
    with pytest.raises(QueryError):
        sanitize_lookup({"password": "secret"})


def test_allow_list_accepts_rescue_filter():
    filt = sanitize_lookup({
        "breed": {"$in": ["Labrador Retriever Mix", "Newfoundland"]},
        "sex_upon_outcome": "Intact Female",
        "age_upon_outcome_in_weeks": {"$gte": 26, "$lte": 156},
    })
    assert "$in" in filt["breed"]


def test_staff_can_read_filtered():
    s = admin_shelter()
    s.create(sample_dog("A1", "Labrador Retriever Mix"))
    s.create(sample_dog("A2", "Pug"))
    staff = staff_shelter(s.client)
    rows = staff.read({"breed": "Pug"})
    assert len(rows) == 1
    assert rows[0]["animal_id"] == "A2"


def test_delete_defaults_to_one_and_refuses_empty_lookup():
    s = admin_shelter()
    s.create(sample_dog("A1"))
    s.create(sample_dog("A2"))
    assert s.delete({}) == 0
    assert s.delete({"animal_id": "A1"}) == 1
    assert len(s.read({})) == 1


def test_aggregation_counts():
    s = admin_shelter()
    s.create(sample_dog("A1", "Pug"))
    s.create(sample_dog("A2", "Pug"))
    s.create(sample_dog("A3", "Beagle"))
    groups = s.counts_by_breed_and_outcome()
    pug = [g for g in groups if g["_id"]["breed"] == "Pug"]
    assert pug and pug[0]["n"] == 2


def test_read_invalid_lookup_returns_empty():
    s = admin_shelter()
    assert s.read({"$match": {}}) == []


def test_dashboard_demo_mode_without_mongo(monkeypatch):
    monkeypatch.delenv("MONGO_USER", raising=False)
    monkeypatch.delenv("MONGO_PASS", raising=False)
    monkeypatch.delenv("DASH_BACKEND", raising=False)
    from demo import build_shelter

    s = build_shelter()
    rows = s.read({})
    assert len(rows) == 7
    water = s.read({
        "breed": {"$in": ["Labrador Retriever Mix", "Chesapeake Bay Retriever", "Newfoundland"]},
        "sex_upon_outcome": "Intact Female",
        "age_upon_outcome_in_weeks": {"$gte": 26, "$lte": 156},
    })
    assert {r["animal_id"] for r in water} == {"A100", "A101"}
    pug_only = [r for r in rows if r["animal_id"] == "A106"]
    assert pug_only and pug_only[0]["breed"] == "Pug"


def test_dashboard_live_backend_still_fail_closed(monkeypatch):
    monkeypatch.setenv("DASH_BACKEND", "live")
    monkeypatch.delenv("MONGO_USER", raising=False)
    monkeypatch.delenv("MONGO_PASS", raising=False)
    from demo import build_shelter

    with pytest.raises(ConfigurationError):
        build_shelter()
