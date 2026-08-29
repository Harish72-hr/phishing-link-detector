# PhishGuard

PhishGuard is a Flask web application for explainable phishing URL risk analysis. It safely analyzes URL strings without requesting or downloading from submitted websites.

## Features

- Deterministic URL feature extraction shared by training and prediction
- Explainable rule analysis with severity and score contributions
- Optional Random Forest model trained from a real CSV dataset
- SQLite scan history, dashboard, and PDF reports
- Responsive cybersecurity-focused interface
- Helpful behavior when the dataset or model is absent

## Architecture

`app.py` coordinates routes. `scanner/` owns extraction, rules, ML prediction, and risk scoring. `database/` owns SQLite operations. `reports/` owns ReportLab output. Templates and static assets provide the UI.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`. Production uses `gunicorn app:app` (Render start command). Set `PORT` when the host provides one; the app binds to `0.0.0.0`.

## Dataset and model training

Place a real CSV in `dataset/`. It needs a URL column (`url`, `link`, or `domain`) and a label column (`label`, `class`, `type`, or `status`). Labels can be `0/1`, `legitimate/phishing`, `benign/malicious`, or equivalent documented values. Then run:

```powershell
python train_model.py dataset\your-dataset.csv
```

This prints accuracy, precision, recall, F1, and a confusion matrix and creates ignored artifacts in `model/`. No fake dataset or accuracy is included.

## Environment variables

See `.env.example` for `SECRET_KEY`, database/model paths, and optional VirusTotal or Google Safe Browsing keys. External reputation services are intentionally not called by the default implementation; adding them requires explicit product consent and timeout/error handling.

## Testing plan

Exercise valid, invalid, empty, suspicious, and legitimate URLs; missing model and dataset paths; SQLite insertion/history/dashboard; and PDF generation. A Flask test client can cover all routes without opening a submitted URL.

## Deployment

For Render, use a Python web service, build command `pip install -r requirements.txt`, and start command `gunicorn app:app`. Generated SQLite/model files use local disk; use persistent storage or an external database/model artifact for multi-instance production.

## Limitations and future work

Results are probabilistic and not guaranteed. Add authenticated users, pagination, persistent production storage, optional reputation integrations, calibration monitoring, and a broader validated dataset before operational use.
