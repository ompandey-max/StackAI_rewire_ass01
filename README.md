# AI-Native House Price Model Serving

A production-shaped FastAPI wrapper around a synthetic house-price model. The project
includes strict input validation, health and prediction endpoints, tests, a non-root Docker
image, and a GitLab CI/CD pipeline definition.

> **Model limitation:** The model was trained on synthetic training-program data. Do not use
> its predictions for real property valuation.

## Quick start

Run these commands from the repository root in WSL/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/ruff check app tests
.venv/bin/python -m pytest -q
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The trained model is included at `outputs/artifacts/model.joblib`. Once Uvicorn is running,
open another terminal and try:

```bash
curl http://localhost:8000/health
curl --request POST http://localhost:8000/predict \
  --header 'Content-Type: application/json' \
  --data '{"sqft":1500,"bedrooms":3,"bathrooms":2.0,"age_years":10,"location_score":7.5}'
```

`/health` returns the API and model versions. `/predict` returns a `prediction` (USD) and
`model_version`. Each request also receives an `X-Request-ID` response header.

## Model and input contract

| Feature | Type | Accepted values |
|---|---|---|
| `sqft` | number | 300–8000 |
| `bedrooms` | integer | 0–10 |
| `bathrooms` | number | 0.5–8, in 0.5 increments |
| `age_years` | integer | 0–150 |
| `location_score` | number | 0–10 |

All fields are required. The service rejects strings/coercion, fractional integers, and
unknown fields. Request errors use the JSON shape `{"error":"...","field":null,"detail":"..."}`:
malformed/empty JSON is 400, invalid schema is 422, oversized requests are 413, and inference
timeouts are 504.

The model was trained on synthetic training-program data with train R² `0.9985` and test R²
`0.9913`. The model card and serving specification are under `outputs/artifacts/`. The source
dataset, training script, assignment handout, and evaluation rubric are intentionally not
included in this public repository.

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `MODEL_PATH` | `outputs/artifacts/model.joblib` | Model artifact path |
| `API_VERSION` | `1.0.0` | API version |
| `MODEL_VERSION` | `local` | Model/build version returned by the API |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `PORT` | `8000` | Uvicorn port |
| `MAX_REQUEST_BYTES` | `16384` | Maximum request body size |
| `PREDICTION_TIMEOUT_SECONDS` | `5` | Inference deadline |
| `CORS_ORIGINS` | empty | Comma-separated allowlist; CORS is off by default |

Wildcard CORS is rejected. Request logs include request ID, method, path, status, and latency;
feature values are not logged. Model loading is performed once at startup and a bad/missing
artifact causes startup failure.

## Docker

Build and run locally:

```bash
docker build -t house-price-serving:local .
docker run --rm -p 8000:8000 house-price-serving:local
```

The multi-stage image installs pinned production dependencies, includes the model artifact,
and runs as the non-root `app` user. It also defines a Docker health check.

## GitLab CI/CD

`.gitlab-ci.yml` defines `lint`, `unit`, `contract`, `integration`, `build`, `push`, and `qa`
stages. Push and QA run on the `qa` or default branch and use `$CI_COMMIT_SHORT_SHA` as the
image tag. Before enabling those jobs:

1. Create a Docker Hub repository named `house-price-serving`.
2. Configure `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` as masked GitLab CI/CD variables.
3. Use a GitLab runner that permits Docker-in-Docker.
4. Run the pipeline and verify the real push and QA smoke-test results.

No registry push or GitLab pipeline result is included as completed evidence in this repository.

## Project map

- `app/` — settings, Pydantic schemas, middleware, FastAPI application.
- `tests/` — unit, contract, edge-case, and integration tests.
- `outputs/artifacts/` — model, model card, and serving specification.
- `Dockerfile`, `.dockerignore`, `.gitlab-ci.yml` — container and delivery configuration.
- `CLAUDE.md` — project-level AI coding context.

The GitLab pipeline configuration does not run automatically on GitHub. No registry push,
GitLab pipeline, or deployment is claimed as completed.
