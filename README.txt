# BatchIQ — Manufacturing Intelligence Platform
# STEP-BY-STEP SETUP GUIDE

======================================================
STEP 1: CREATE PROJECT FOLDER
======================================================

Copy the entire "manufacturing-platform" folder to your computer.
The structure should look like this:

manufacturing-platform/
├── app.py
├── config.py
├── requirements.txt
├── README.txt  (this file)
├── data/               ← PUT YOUR .xlsx FILES HERE
│   ├── batch_production_data.xlsx
│   └── batch_process_data.xlsx
├── modules/
│   ├── m1_quality_prediction.py
│   ├── m2_energy_fingerprint.py
│   ├── m3_energy_engineering.py
│   ├── m4_golden_batch.py
│   ├── m5_asset_health.py
│   ├── m6_synthetic_waveforms.py
│   └── utils.py
├── models/             ← auto-created, stores trained models
└── templates/
    ├── base.html
    ├── index.html
    ├── predict.html
    ├── energy.html
    ├── golden_batch.html
    ├── health.html
    └── upload.html


======================================================
STEP 2: INSTALL PYTHON (if not already installed)
======================================================

Download Python 3.10 or newer from:
https://www.python.org/downloads/

During installation on Windows, check "Add Python to PATH"


======================================================
STEP 3: OPEN TERMINAL / COMMAND PROMPT
======================================================

Windows: Press Win+R, type "cmd", press Enter
Mac: Press Cmd+Space, type "Terminal", press Enter
VS Code: Open the project folder, then Terminal > New Terminal


======================================================
STEP 4: NAVIGATE TO PROJECT FOLDER
======================================================

In your terminal, type:

    cd path/to/manufacturing-platform

Example on Windows:
    cd C:\Users\YourName\Desktop\manufacturing-platform

Example on Mac:
    cd ~/Desktop/manufacturing-platform


======================================================
STEP 5: CREATE VIRTUAL ENVIRONMENT (recommended)
======================================================

    python -m venv venv

Activate it:
  Windows:  venv\Scripts\activate
  Mac/Linux: source venv/bin/activate

You should see (venv) in your terminal prompt.


======================================================
STEP 6: INSTALL DEPENDENCIES
======================================================

    pip install -r requirements.txt

This installs: Flask, pandas, xgboost, scikit-learn, shap, scipy, etc.
This may take 2–5 minutes.


======================================================
STEP 7: ADD YOUR DATA FILES
======================================================

Place your Excel files in the "data/" folder:

  data/batch_production_data.xlsx   ← 60 rows, 15 columns
  data/batch_process_data.xlsx      ← 211 rows, 11 columns (time-series)

If you don't have these files yet, the app will run in "demo mode"
showing the real known values from your analysis.


======================================================
STEP 8: RUN THE APPLICATION
======================================================

    python app.py

You should see output like:
  ✅ Platform initialized | Golden Batch: T059 | Score: 0.8934
  * Running on http://127.0.0.1:5000


======================================================
STEP 9: OPEN IN BROWSER
======================================================

Open your web browser and go to:

    http://localhost:5000

That's it! The dashboard will load.


======================================================
HOW TO USE THE UPLOAD FEATURE
======================================================

Option A — "Predict Only" mode (default, recommended for new files):
  1. Click "Upload Data" in the sidebar
  2. Keep mode as "Predict Only"
  3. Drag and drop your .xlsx file OR click to browse
  4. Click "Upload & Process"
  5. The platform generates quality predictions for every batch in your file
  6. Results shown in a table below

Option B — "Replace & Retrain" mode:
  1. Click "Upload Data" in the sidebar
  2. Click "Replace & Retrain" tab
  3. Upload your new batch_production_data.xlsx
  4. The platform replaces the dataset AND retrains all ML models
  5. Wait ~20-40 seconds for retraining to complete
  6. Dashboard refreshes with new data


======================================================
PAGES OVERVIEW
======================================================

/ (Dashboard)       — 4 KPI cards, batch overview, quick stats
/predict            — Enter parameters, get quality predictions + SHAP
/energy             — Energy by phase, anomaly detection, CO2 stats
/golden-batch       — Golden batch ranking, adaptive weight sliders
/health             — Asset health scores, maintenance alerts
/upload             — Upload Excel files, bulk predictions

API Endpoints:
/api/predict        — POST JSON → quality predictions
/api/golden-batch   — POST JSON weights → recalculate rankings
/api/health         — GET → all health scores
/api/inverse-predict — POST desired targets → recommended params
/api/carbon-budget  — POST budget → CO2 status


======================================================
TROUBLESHOOTING
======================================================

Error: "ModuleNotFoundError"
  → Make sure you ran: pip install -r requirements.txt

Error: "Port already in use"
  → Change port: python app.py --port 5001
  → Or find/kill process on port 5000

Error: "FileNotFoundError" for .xlsx files
  → Make sure files are in the "data/" subfolder
  → Filenames must match exactly

Models don't exist yet:
  → The app auto-trains models on first run when data files are present
  → Trained models saved to "models/" folder for faster reloads

SHAP values fail:
  → Ignore this — SHAP has compatibility issues with some XGBoost versions
  → All other features work normally


======================================================
KNOWN REAL VALUES (for reference)
======================================================

Batch failure rate:       18 / 60 batches (30%) fail quality specs
Failing batches:          T005,T008,T014,T018,T020,T025,T029,T031,
                          T034,T036,T040,T042,T045,T049,T051,T054,T056,T060
Golden batch:             T059 (highest composite score)
Worst batch:              T056
Energy range:             21.4 – 46.1 kWh per batch
CO2 range:                17.6 – 37.8 kg per batch
Compression energy share: 50.4% of total batch energy
Milling max vibration:    9.79 mm/s (CRITICAL)
Compression max power:    66.07 kW at minute 141 (WARNING)
Strongest correlation:    Granulation Time → Hardness (r = 0.993)