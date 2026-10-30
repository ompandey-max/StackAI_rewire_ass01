# House Price Model Serving Specification

## Status

Reviewed and approved before implementation.

## Model and schema source

The service wraps the trained `RandomForestRegressor` in
`outputs/artifacts/model.joblib`. Its model card reports held-out test R² of `0.991` and
explicitly warns that prediction input must be a one-row pandas DataFrame with the named,
ordered columns below. The API schema follows the model card's declared types and limits;
integer JSON numbers are accepted for float-valued features, but strings and booleans are not
coerced.

| Field | Type | Required | Inclusive range | Additional rule |
|---|---|---:|---:|---|
| `sqft` | number | yes | 300–8000 | — |
| `bedrooms` | integer | yes | 0–10 | booleans and fractional values rejected |
| `bathrooms` | number | yes | 0.5–8 | increments of 0.5 |
| `age_years` | integer | yes | 0–150 | booleans and fractional values rejected |
| `location_score` | number | yes | 0–10 | — |

Unknown request fields are rejected. The generated model-card example initially represented
the two integer features as decimals; the artifact example has been normalized to the declared
integer schema. The model and training data are unchanged.

## API contract

### `POST /predict`

Accepts a JSON object containing all five fields. A successful response is
`200 application/json`:

```json
{
  "prediction": 740581.66,
  "model_version": "local"
}
```

`prediction` is the model's price estimate in USD. `model_version` identifies the loaded model
build.

### `GET /health`

Returns `200 application/json` when the model is loaded:

```json
{
  "status": "ok",
  "api_version": "1.0.0",
  "model_version": "local"
}
```

The process fails during startup if the model artifact cannot be loaded; it must not accept
traffic with an uninitialized model. A runtime readiness check returns `503` if no model is
available.

### Error responses

All expected request errors use `application/json` with the same shape:

```json
{
  "error": "missing_field",
  "field": "sqft",
  "detail": "A required field is missing."
}
```

`field` is `null` when an error cannot be attributed to one feature. The service does not echo
submitted values.

| Condition | HTTP status | `error` |
|---|---:|---|
| Empty request body | 400 | `empty_payload` |
| Malformed JSON | 400 | `invalid_json` |
| Missing required feature | 422 | `missing_field` |
| Wrong feature type or unsupported field | 422 | `invalid_type` or `invalid_field` |
| Value outside the declared range or bathroom increment | 422 | `out_of_range` |
| Body larger than 16 KiB | 413 | `payload_too_large` |
| Prediction exceeds its configured timeout | 504 | `inference_timeout` |
| Model unavailable after startup | 503 | `model_unavailable` |

## Non-functional requirements

- **Versioning:** `API_VERSION` and `MODEL_VERSION` are environment-driven. API version
  defaults to `1.0.0`; model version defaults to `local`. CI image tags use
  `$CI_COMMIT_SHORT_SHA`, and the QA job sets `MODEL_VERSION` to that same commit identifier.
- **Observability:** Log one completion record per request with a generated request ID, method,
  path, status, and latency. Prediction logs may include feature names/count, never feature
  values. Return the request ID in `X-Request-ID`.
- **Resource limits:** Reject request bodies larger than 16 KiB (configurable via
  `MAX_REQUEST_BYTES`). Bound model inference to 5 seconds (configurable via
  `PREDICTION_TIMEOUT_SECONDS`).
- **Configuration:** Read model path (`MODEL_PATH`), log level (`LOG_LEVEL`), API version,
  model version, allowed CORS origins, request-size limit, prediction timeout, and listener port
  (`PORT`) from environment variables. CORS is disabled unless an explicit origin allowlist is
  configured.
- **Startup:** Load the model once at application startup. Missing, unreadable, or incompatible
  artifacts cause startup to fail with the original error visible in logs.

## Security baseline

- Keep credentials out of code, logs, build arguments, and image layers. Docker Hub credentials
  are supplied only as masked CI/CD variables.
- Do not enable wildcard CORS. If cross-origin access is needed, configure exact trusted origins.
- Pin all application and test dependencies to exact versions in `requirements.txt`; review and
  update those pins deliberately.
- Build a minimal multi-stage Docker image from a tagged Python base image and run the service
  as a non-root user.
- Do not log request feature values. The supplied synthetic dataset is for training-program use,
  not real-world property valuation.
