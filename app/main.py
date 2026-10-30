import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.middleware import RequestContextMiddleware, RequestSizeLimitMiddleware
from app.schema import HealthResponse, PredictionRequest, PredictionResponse

FEATURES = ["sqft", "bedrooms", "bathrooms", "age_years", "location_score"]
logger = logging.getLogger(__name__)


def _validation_error(error: dict[str, Any]) -> tuple[str, str | None, str]:
    error_type = error["type"]
    location = error.get("loc", ())
    field = ".".join(str(part) for part in location if part != "body") or None

    if error_type == "missing":
        return "missing_field", field, "A required field is missing."
    if error_type == "extra_forbidden":
        return "invalid_field", field, "Unknown fields are not allowed."
    if error_type in {
        "greater_than",
        "greater_than_equal",
        "less_than",
        "less_than_equal",
        "multiple_of",
    }:
        return "out_of_range", field, "Value is outside the allowed range or increment."
    return "invalid_type", field, "Value has an invalid type."


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings or Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, configured.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        logger.info("loading_model path=%s", configured.model_path)
        model = joblib.load(configured.model_path)
        if not callable(getattr(model, "predict", None)):
            raise TypeError("Loaded model artifact does not provide predict()")
        application.state.model = model
        application.state.model_version = configured.model_version
        logger.info("model_loaded model_version=%s", configured.model_version)
        yield
        application.state.model = None

    application = FastAPI(
        title="House Price Model Serving",
        version=configured.api_version,
        lifespan=lifespan,
    )

    if configured.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(configured.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    application.add_middleware(
        RequestSizeLimitMiddleware,
        max_body_bytes=configured.max_request_bytes,
    )
    application.add_middleware(RequestContextMiddleware)

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        errors = exception.errors()
        first_error = errors[0] if errors else {"type": "value_error", "loc": ()}
        body = exception.body

        if body is None or body == "" or body == b"":
            error_code = "empty_payload"
            field = None
            detail = "Request body must not be empty."
            status_code = 400
        elif first_error["type"] == "json_invalid":
            error_code = "invalid_json"
            field = None
            detail = "Request body must contain valid JSON."
            status_code = 400
        else:
            error_code, field, detail = _validation_error(first_error)
            status_code = 422

        return JSONResponse(
            status_code=status_code,
            content={"error": error_code, "field": field, "detail": detail},
        )

    @application.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse | JSONResponse:
        model = getattr(request.app.state, "model", None)
        if model is None:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "model_unavailable",
                    "field": None,
                    "detail": "The prediction model is unavailable.",
                },
            )
        return HealthResponse(
            status="ok",
            api_version=configured.api_version,
            model_version=request.app.state.model_version,
        )

    @application.post("/predict", response_model=PredictionResponse)
    async def predict(
        payload: PredictionRequest, request: Request
    ) -> PredictionResponse | JSONResponse:
        model = getattr(request.app.state, "model", None)
        if model is None:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "model_unavailable",
                    "field": None,
                    "detail": "The prediction model is unavailable.",
                },
            )

        frame = pd.DataFrame([payload.model_dump()], columns=FEATURES)
        logger.debug(
            "prediction_input request_id=%s fields=%s",
            request.state.request_id,
            ",".join(FEATURES),
        )

        try:
            predictions = await asyncio.wait_for(
                asyncio.to_thread(model.predict, frame),
                timeout=configured.prediction_timeout_seconds,
            )
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={
                    "error": "inference_timeout",
                    "field": None,
                    "detail": "Prediction exceeded the configured time limit.",
                },
            )

        return PredictionResponse(
            prediction=float(predictions[0]),
            model_version=request.app.state.model_version,
        )

    return application


app = create_app()
