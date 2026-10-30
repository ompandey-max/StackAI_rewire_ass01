from dataclasses import replace
from pathlib import Path
import time

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

FEATURES = ["sqft", "bedrooms", "bathrooms", "age_years", "location_score"]
ARTIFACT = Path("outputs/artifacts/model.joblib")
VALID_PAYLOAD = {
    "location_score": 7.5,
    "age_years": 10,
    "bathrooms": 2.0,
    "bedrooms": 3,
    "sqft": 1500,
}


def test_prediction_matches_named_dataframe_inference(client) -> None:
    response = client.post("/predict", json=VALID_PAYLOAD)
    model = joblib.load(ARTIFACT)
    frame = pd.DataFrame(
        [[VALID_PAYLOAD[field] for field in FEATURES]],
        columns=FEATURES,
    )
    expected = float(model.predict(frame)[0])

    assert response.status_code == 200
    assert response.json()["prediction"] == pytest.approx(expected)


def test_model_load_failure_stops_application_startup(tmp_path: Path) -> None:
    settings = replace(
        Settings.from_env(),
        model_path=tmp_path / "missing-model.joblib",
    )

    with pytest.raises(FileNotFoundError):
        with TestClient(create_app(settings)):
            pass


def test_prediction_timeout_has_explicit_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = replace(Settings.from_env(), prediction_timeout_seconds=0.01)

    with TestClient(create_app(settings)) as slow_client:
        def slow_predict(_frame: pd.DataFrame) -> list[float]:
            time.sleep(0.05)
            return [1.0]

        monkeypatch.setattr(slow_client.app.state.model, "predict", slow_predict)
        response = slow_client.post("/predict", json=VALID_PAYLOAD)

    assert response.status_code == 504
    assert response.json()["error"] == "inference_timeout"
