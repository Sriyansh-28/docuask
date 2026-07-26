"""Shared test fixtures.

Point the telemetry DB at a fresh in-memory SQLite for every test so cases
don't leak interaction rows into one another (and never touch a real file).
"""

import pytest

from app import db


@pytest.fixture(autouse=True)
def fresh_db():
    db.configure(":memory:")
    yield
