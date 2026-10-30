# Project instructions

This project serves the provided synthetic house-price model. Treat the dataset and training
script as read-only inputs. Keep request validation aligned with the feature schema in
`outputs/artifacts/model_card.md`, and pass predictions a one-row pandas DataFrame with the
named columns in the model's training order.

Keep runtime configuration environment-driven, do not place secrets in source or images, and
keep generated evidence under `outputs/artifacts/`. Before considering a code change complete,
run the relevant Ruff checks and pytest suites. Do not claim a registry push, GitLab pipeline,
or deployment succeeded unless its actual result is available.
