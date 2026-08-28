import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.db import get_connection


class FakeConnection:
    pass


@pytest.fixture
def client():
    app.dependency_overrides[get_connection] = lambda: FakeConnection()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
