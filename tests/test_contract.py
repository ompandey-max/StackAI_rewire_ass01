import pytest
from fastapi.testclient import TestClient

VALID_PAYLOAD = {
    "sqft": 1500,
    "bedrooms": 3,
    "bathrooms": 2.0,
    "age_years": 10,
    "location_score": 7.5,
}


def _assert_error(response, status_code: int, error: str) -> None:
    assert response.status_code == status_code
    assert set(response.json()) == {"error", "field", "detail"}
    assert response.json()["error"] == error
    assert isinstance(response.json()["detail"], str)


def test_health_contract(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "api_version": "1.0.0",
        "model_version": "local",
    }


def test_predict_contract(client: TestClient) -> None:
    response = client.post("/predict", json=VALID_PAYLOAD)

    assert response.status_code == 200
    assert set(response.json()) == {"prediction", "model_version"}
    assert isinstance(response.json()["prediction"], float)
    assert response.json()["model_version"] == "local"


def test_empty_body_has_explicit_error(client: TestClient) -> None:
    response = client.post(
        "/predict", content=b"", headers={"content-type": "application/json"}
    )

    _assert_error(response, 400, "empty_payload")


def test_malformed_json_has_explicit_error(client: TestClient) -> None:
    response = client.post(
        "/predict", content="{", headers={"content-type": "application/json"}
    )

    _assert_error(response, 400, "invalid_json")


def test_empty_object_is_missing_required_fields(client: TestClient) -> None:
    response = client.post("/predict", json={})

    _assert_error(response, 422, "missing_field")


def test_missing_field_has_explicit_error(client: TestClient) -> None:
    payload = {key: value for key, value in VALID_PAYLOAD.items() if key != "sqft"}

    response = client.post("/predict", json=payload)

    _assert_error(response, 422, "missing_field")
    assert response.json()["field"] == "sqft"


def test_wrong_type_has_explicit_error(client: TestClient) -> None:
    response = client.post("/predict", json={**VALID_PAYLOAD, "bedrooms": "3"})

    _assert_error(response, 422, "invalid_type")
    assert response.json()["field"] == "bedrooms"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sqft", 299),
        ("sqft", 8001),
        ("bedrooms", 11),
        ("bathrooms", 2.25),
        ("age_years", 151),
        ("location_score", 10.1),
    ],
)
def test_out_of_range_values_have_explicit_error(
    client: TestClient, field: str, value: float | int
) -> None:
    response = client.post("/predict", json={**VALID_PAYLOAD, field: value})

    _assert_error(response, 422, "out_of_range")
    assert response.json()["field"] == field


def test_unknown_field_has_explicit_error(client: TestClient) -> None:
    response = client.post("/predict", json={**VALID_PAYLOAD, "currency": "USD"})

    _assert_error(response, 422, "invalid_field")
    assert response.json()["field"] == "currency"


def test_large_payload_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/predict",
        content=b'{"sqft": "' + b"x" * 17000 + b'"}',
        headers={"content-type": "application/json"},
    )

    _assert_error(response, 413, "payload_too_large")


def test_responses_include_request_id(client: TestClient) -> None:
    response = client.get("/health")

    assert response.headers["x-request-id"]


def test_cors_is_disabled_by_default(client: TestClient) -> None:
    response = client.get("/health", headers={"origin": "https://example.invalid"})

    assert "access-control-allow-origin" not in response.headers
