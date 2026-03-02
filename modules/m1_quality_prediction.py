import os, joblib
import pandas as pd
import numpy as np
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

FEATURE_COLS = ['Granulation_Time','Binder_Amount','Drying_Temp','Drying_Time',
                'Compression_Force','Machine_Speed','Lubricant_Conc']
TARGET_COLS  = ['Moisture_Content','Tablet_Weight','Hardness','Friability',
                'Disintegration_Time','Dissolution_Rate','Content_Uniformity']
SPEC_LIMITS  = {
    'Hardness':          (50,  130),
    'Friability':        (None, 1.0),
    'Dissolution_Rate':  (80,  None),
    'Content_Uniformity':(95,  105),
    'Moisture_Content':  (None, 3.0),
}

def train_quality_model(df, models_dir):
    missing = [c for c in FEATURE_COLS+TARGET_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    X = df[FEATURE_COLS].values
    y = df[TARGET_COLS].values
    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X)
    model  = MultiOutputRegressor(
        XGBRegressor(n_estimators=200, max_depth=4, learning_rate=0.05,
                     random_state=42, verbosity=0))
    model.fit(X_sc, y)
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(model,  os.path.join(models_dir,'quality_model.pkl'))
    joblib.dump(scaler, os.path.join(models_dir,'scaler.pkl'))
    return model, scaler

def predict_quality(model, scaler, input_list):
    X    = scaler.transform([input_list])
    pred = model.predict(X)[0]
    return dict(zip(TARGET_COLS, pred))

def check_pass_fail(predictions):
    out = {}
    for metric, value in predictions.items():
        value = float(value)
        if metric not in SPEC_LIMITS:
            out[metric] = {'value': round(value,3), 'status':'N/A'}
            continue
        lo, hi = SPEC_LIMITS[metric]
        passed = True
        if lo is not None and value < lo: passed = False
        if hi is not None and value > hi: passed = False
        out[metric] = {'value': round(value,3), 'status':'PASS' if passed else 'FAIL'}
    return out

def predict_batch_df(model, scaler, df):
    miss = [c for c in FEATURE_COLS if c not in df.columns]
    if miss:
        return pd.DataFrame()
    X_sc = scaler.transform(df[FEATURE_COLS].values)
    preds = model.predict(X_sc)
    out = pd.DataFrame(preds, columns=TARGET_COLS, index=df.index)
    if 'Batch_ID' in df.columns:
        out.insert(0,'Batch_ID', df['Batch_ID'].values)
    return out

def get_shap_values(model, scaler, input_list, target_index=2):
    import shap
    X_sc      = scaler.transform([input_list])
    explainer = shap.TreeExplainer(model.estimators_[target_index])
    shap_vals = explainer.shap_values(X_sc)
    vals      = shap_vals[0] if hasattr(shap_vals,'__len__') else shap_vals
    return {col: float(v) for col,v in zip(FEATURE_COLS, vals)}