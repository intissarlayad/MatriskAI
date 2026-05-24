# Pipeline Overview

## Step 1 – Data Cleaning & Feature Engineering

- Reads raw Excel/CSV files.
- Handles missing values, normalizes column names, and creates engineered features.
- Stores intermediate results in `data/cleaned/`.

## Step 2 – Model Training & Calibration

- Trains an XGBoost regressor on the cleaned dataset.
- Performs hyper‑parameter tuning using grid search.
- Calibrates the model probabilities with `sklearn.calibration.CalibratedClassifierCV`.

## Step 3 – Forecasting with Prophet

- Generates time‑series forecasts for each risk metric.
- Combines forecasted values with XGBoost predictions to improve robustness.

## Step 4 – Prescriptive Engine

- Applies business rules and risk thresholds to produce actionable recommendations.
- Outputs a summary CSV and feeds the Streamlit dashboard.

Each step is implemented as a separate Python script under `Scripts/` and can be run independently via:

```bash
python Scripts/matrisk_step1_cleaning.py
python Scripts/matrisk_step2_train.py
python Scripts/matrisk_step3_forecast.py
python Scripts/matrisk_step4_prescriptif.py
```

For a full end‑to‑end run, execute the master pipeline script:

```bash
python run_pipeline.py
```
