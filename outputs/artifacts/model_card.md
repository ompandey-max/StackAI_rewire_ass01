# Model Card — House Price Predictor

## What this model does
Predicts a house sale price (USD, float) from five structural/location features. Trained on
a synthetic dataset (`data/house_prices.csv`) for training-program use — do not use for real
valuation.

## Artifact
`model.joblib` — a scikit-learn `RandomForestRegressor`, loadable with:
```python
import joblib
model = joblib.load("model.joblib")
```
Held-out test R^2: 0.991

## Input schema (this is what your spec's request body should be built from)
```json
{
  "sqft": {
    "type": "float",
    "min": 300,
    "max": 8000,
    "description": "Living area in square feet"
  },
  "bedrooms": {
    "type": "int",
    "min": 0,
    "max": 10,
    "description": "Number of bedrooms"
  },
  "bathrooms": {
    "type": "float",
    "min": 0.5,
    "max": 8,
    "description": "Number of bathrooms (0.5 increments allowed)"
  },
  "age_years": {
    "type": "int",
    "min": 0,
    "max": 150,
    "description": "Age of the property in years"
  },
  "location_score": {
    "type": "float",
    "min": 0.0,
    "max": 10.0,
    "description": "Composite location desirability score, 0 (worst) to 10 (best)"
  }
}
```
All five fields are required. Call `model.predict(df)` with a single-row `pandas.DataFrame`
whose columns are named and ordered exactly `sqft, bedrooms, bathrooms, age_years,
location_score` — the model was fit on named columns and will warn (and may silently
mis-map values) if you pass a raw list/array instead. This is a real gap to account for in
your wrapper, not a hypothetical one.

## Output
A single float: predicted price in USD. No confidence interval or additional metadata is
produced by the model itself — if your spec wants one, that's something your serving layer
adds, not the model.

## Example input/output
Input:
```json
{
  "sqft": 3619.94,
  "bedrooms": 3,
  "bathrooms": 3.5,
  "age_years": 13,
  "location_score": 6.13
}
```
Predicted price: 740,581.66

## Things the model does NOT validate for you
- It will not reject out-of-range values (e.g. negative sqft, 400 bedrooms) — it will just
  produce a nonsense prediction. Input validation is the serving layer's job, not the model's.
- It will not reject wrong types gracefully — passing a string where a float is expected will
  raise inside `predict`, not return a clean error. This is deliberate: it's exactly the gap
  your spec's error-handling section needs to cover.
