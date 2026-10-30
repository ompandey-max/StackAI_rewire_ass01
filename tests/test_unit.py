import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schema import PredictionRequest

VALID_PAYLOAD = {
    "sqft": 1500,
    "bedrooms": 3,
    "bathrooms": 2.0,
    "age_years": 10,
    "location_score": 7.5,
}


def test_request_schema_accepts_declared_feature_types() -> None:
    parsed = PredictionRequest.model_validate(VALID_PAYLOAD)

    assert parsed.sqft == 1500.0
    assert parsed.bedrooms == 3
    assert parsed.bathrooms == 2.0


@pytest.mark.parametrize(
    "payload",
    [
        {
            "sqft": 300,
            "bedrooms": 0,
            "bathrooms": 0.5,
            "age_years": 0,
            "location_score": 0,
        },
        {
            "sqft": 8000,
            "bedrooms": 10,
            "bathrooms": 8,
            "age_years": 150,
            "location_score": 10,
        },
    ],
)
def test_request_schema_accepts_inclusive_boundaries(payload: dict) -> None:
    assert PredictionRequest.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sqft", 299),
        ("sqft", 8001),
        ("bedrooms", -1),
        ("bedrooms", 11),
        ("bathrooms", 0.25),
        ("bathrooms", 2.25),
        ("bathrooms", 8.5),
        ("age_years", -1),
        ("age_years", 151),
        ("location_score", -0.1),
        ("location_score", 10.1),
    ],
)
def test_request_schema_rejects_out_of_range_values(
    field: str, value: float | int
) -> None:
    payload = {**VALID_PAYLOAD, field: value}

    with pytest.raises(ValidationError):
        PredictionRequest.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sqft", "1500"),
        ("bedrooms", 3.0),
        ("bedrooms", True),
        ("bathrooms", "2.0"),
        ("age_years", 10.5),
        ("location_score", False),
    ],
)
def test_request_schema_rejects_coerced_or_wrong_types(
    field: str, value: object
) -> None:
    payload = {**VALID_PAYLOAD, field: value}

    with pytest.raises(ValidationError):
        PredictionRequest.model_validate(payload)


def test_request_schema_requires_every_field() -> None:
    payload = {key: value for key, value in VALID_PAYLOAD.items() if key != "sqft"}

    with pytest.raises(ValidationError):
        PredictionRequest.model_validate(payload)


def test_request_schema_rejects_unknown_fields() -> None:
    payload = {**VALID_PAYLOAD, "currency": "USD"}

    with pytest.raises(ValidationError):
        PredictionRequest.model_validate(payload)


def test_settings_reject_wildcard_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(ValueError, match="wildcard"):
        Settings.from_env()
