# Configuration Guide

## Overview

`config.py` centralises all mutable parameters for MatriskAI:

- Risk thresholds
- Feature engineering toggles
- Paths to data directories
- Logging configuration

## Editing the File

1. Open `config.py` in your editor.
2. Locate the section you want to modify (see inline comments).
3. Save the file; the changes are reflected the next time a script runs.

## Key Sections

### Thresholds

```python
RISK_THRESHOLD = 0.7          # Default risk alert level (0-1)
LOW_RISK_THRESHOLD = 0.3      # Below this value, risk is considered low
```

Adjust these values to make the dashboard more or less sensitive.

### Feature Flags

```python
ENABLE_FEATURE_ENGINEERING = True   # Toggle heavy feature creation
USE_CUSTOM_FEATURES = False         # Set to True to load custom_features.py
```

If you add new features, set `USE_CUSTOM_FEATURES = True` and place the script in `Scripts/`.

### Data Paths

```python
RAW_DATA_DIR = Path("../data/raw")
CLEANED_DATA_DIR = Path("../data/cleaned")
```

Change the paths if your repository layout differs.

### Logging

```python
LOG_LEVEL = "INFO"   # Options: DEBUG, INFO, WARNING, ERROR
LOG_FILE = Path("../logs/matrisk.log")
```

For more verbose output during debugging, set `LOG_LEVEL = "DEBUG"`.

## Environment Variables

Sensitive values (e.g., `GROQ_API_KEY`) are stored in `.env`.
Do **not** hard-code them in `config.py`. Add any new secret keys to `.env` and reference them with `os.getenv("KEY_NAME")`.

## Applying Changes

After editing, re-run the relevant step or the full pipeline:

```bash
python run_pipeline.py
# or individual steps:
python Scripts/matrisk_step2_train.py
```

The updated configuration will be automatically picked up.
