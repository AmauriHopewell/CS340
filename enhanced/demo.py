"""In-memory AnimalShelter used when live Mongo credentials are missing.

AnimalShelter itself stays fail-closed. This module injects mongomock and a
small seed set so dashboard.py and the tests can run from the zip.
"""
from __future__ import annotations

import os
import sys

from animal_shelter import AnimalShelter, ROLE_ADMIN, ROLE_STAFF

DEMO_ANIMALS = [
    {"animal_id": "A100", "animal_type": "Dog", "breed": "Labrador Retriever Mix",
     "sex_upon_outcome": "Intact Female", "age_upon_outcome_in_weeks": 52, "outcome_type": "Adoption"},
    {"animal_id": "A101", "animal_type": "Dog", "breed": "Newfoundland",
     "sex_upon_outcome": "Intact Female", "age_upon_outcome_in_weeks": 80, "outcome_type": "Transfer"},
    {"animal_id": "A102", "animal_type": "Dog", "breed": "German Shepherd",
     "sex_upon_outcome": "Intact Male", "age_upon_outcome_in_weeks": 60, "outcome_type": "Adoption"},
    {"animal_id": "A103", "animal_type": "Dog", "breed": "Siberian Husky",
     "sex_upon_outcome": "Intact Male", "age_upon_outcome_in_weeks": 40, "outcome_type": "Adoption"},
    {"animal_id": "A104", "animal_type": "Dog", "breed": "Doberman Pinscher",
     "sex_upon_outcome": "Intact Male", "age_upon_outcome_in_weeks": 30, "outcome_type": "Adoption"},
    {"animal_id": "A105", "animal_type": "Dog", "breed": "Bloodhound",
     "sex_upon_outcome": "Intact Male", "age_upon_outcome_in_weeks": 200, "outcome_type": "Transfer"},
    {"animal_id": "A106", "animal_type": "Dog", "breed": "Pug",
     "sex_upon_outcome": "Spayed Female", "age_upon_outcome_in_weeks": 12, "outcome_type": "Adoption"},
]


def role_from_env() -> str:
    role = os.environ.get("DASH_ROLE", ROLE_STAFF).strip().lower()
    return role if role in {ROLE_STAFF, ROLE_ADMIN} else ROLE_STAFF


def use_demo_backend() -> bool:
    backend = os.environ.get("DASH_BACKEND", "").strip().lower()
    if backend == "live":
        return False
    if backend == "mock":
        return True
    user = (os.environ.get("MONGO_USER") or "").strip()
    password = (os.environ.get("MONGO_PASS") or "").strip()
    return not user or not password


def seed_demo(shelter: AnimalShelter) -> None:
    admin = AnimalShelter(ROLE_ADMIN, client=shelter.client, db="aac", col="animals")
    try:
        admin.ensure_indexes()
    except Exception:
        pass
    if admin.read({}):
        return
    for doc in DEMO_ANIMALS:
        admin.create(doc)


def build_shelter() -> AnimalShelter:
    role = role_from_env()
    if use_demo_backend():
        import mongomock
        shelter = AnimalShelter(role, client=mongomock.MongoClient(), db="aac", col="animals")
        seed_demo(shelter)
        print(
            "Demo mode (in-memory). Set MONGO_USER and MONGO_PASS for a live database.",
            file=sys.stderr,
        )
        return shelter
    shelter = AnimalShelter(role)
    try:
        shelter.ensure_indexes()
    except Exception:
        # Unique index fails if AAC data already has duplicate animal_id values.
        pass
    return shelter
