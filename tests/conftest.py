from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client
