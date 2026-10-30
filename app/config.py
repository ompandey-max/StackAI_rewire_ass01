import math
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    model_path: Path
    api_version: str
    model_version: str
    log_level: str
    port: int
    max_request_bytes: int
    prediction_timeout_seconds: float
    cors_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        port = int(os.getenv("PORT", "8000"))
        if not 1 <= port <= 65535:
            raise ValueError("PORT must be between 1 and 65535")

        max_request_bytes = int(os.getenv("MAX_REQUEST_BYTES", "16384"))
        if max_request_bytes < 1:
            raise ValueError("MAX_REQUEST_BYTES must be positive")

        prediction_timeout_seconds = float(
            os.getenv("PREDICTION_TIMEOUT_SECONDS", "5")
        )
        if (
            not math.isfinite(prediction_timeout_seconds)
            or prediction_timeout_seconds <= 0
        ):
            raise ValueError("PREDICTION_TIMEOUT_SECONDS must be positive and finite")

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        if log_level not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError("LOG_LEVEL must be a standard Python logging level")

        cors_origins = tuple(
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "").split(",")
            if origin.strip()
        )
        if "*" in cors_origins:
            raise ValueError("CORS_ORIGINS must not contain a wildcard")

        return cls(
            model_path=Path(
                os.getenv("MODEL_PATH", "outputs/artifacts/model.joblib")
            ),
            api_version=os.getenv("API_VERSION", "1.0.0"),
            model_version=os.getenv("MODEL_VERSION", "local"),
            log_level=log_level,
            port=port,
            max_request_bytes=max_request_bytes,
            prediction_timeout_seconds=prediction_timeout_seconds,
            cors_origins=cors_origins,
        )
