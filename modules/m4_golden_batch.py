import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

DEFAULT_WEIGHTS = {
    'hardness': 0.20,
    'friability': 0.20,
    'dissolution': 0.25,
    'uniformity': 0.20,
    'moisture': 0.10,
    'energy': 0.05
}

def _safe_norm(series: pd.Series) -> pd.Series:
    rng = series.max() - series.min()
    if rng == 0:
        return pd.Series([0.5] * len(series), index=series.index)
    return (series - series.min()) / rng

def score_batches(df: pd.DataFrame, weights: dict = None) -> pd.DataFrame:
    if weights is None:
        weights = DEFAULT_WEIGHTS

    df = df.copy()
    df['Hardness_norm']         = _safe_norm(df['Hardness'])
    df['Dissolution_Rate_norm'] = _safe_norm(df['Dissolution_Rate'])
    df['Content_Uniformity_norm'] = _safe_norm(df['Content_Uniformity'])
    df['Friability_norm']    = 1 - _safe_norm(df['Friability'])
    df['Moisture_Content_norm'] = 1 - _safe_norm(df['Moisture_Content'])

    if 'Energy_kWh' in df.columns:
        df['Energy_kWh_norm'] = 1 - _safe_norm(df['Energy_kWh'])
    else:
        df['Energy_kWh_norm'] = 0.5

    df['composite_score'] = (
        weights.get('hardness', 0.20)    * df['Hardness_norm'] +
        weights.get('friability', 0.20)  * df['Friability_norm'] +
        weights.get('dissolution', 0.25) * df['Dissolution_Rate_norm'] +
        weights.get('uniformity', 0.20)  * df['Content_Uniformity_norm'] +
        weights.get('moisture', 0.10)    * df['Moisture_Content_norm'] +
        weights.get('energy', 0.05)      * df['Energy_kWh_norm']
    )
    return df.sort_values('composite_score', ascending=False).reset_index(drop=True)

def check_golden_update(new_score: float, current_golden_score: float) -> dict:
    if new_score > current_golden_score:
        return {
            'update_proposed': True,
            'improvement_pct': round((new_score - current_golden_score) / current_golden_score * 100, 2)
        }
    return {'update_proposed': False, 'improvement_pct': 0}

def log_golden_decision(batch_id: str, action: str, score: float, history_path: str):
    history = []
    if os.path.exists(history_path):
        with open(history_path) as f:
            try:
                history = json.load(f)
            except:
                history = []
    history.append({
        'timestamp': datetime.now().isoformat(),
        'batch_id': batch_id,
        'action': action,
        'score': score
    })
    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2)

def get_golden_batch_params(df: pd.DataFrame, batch_id: str) -> dict:
    row = df[df['Batch_ID'] == batch_id]
    if row.empty:
        return {}
    row = row.iloc[0]
    return {
        'Granulation_Time': round(float(row['Granulation_Time']), 2),
        'Binder_Amount': round(float(row['Binder_Amount']), 2),
        'Drying_Temp': round(float(row['Drying_Temp']), 2),
        'Drying_Time': round(float(row['Drying_Time']), 2),
        'Compression_Force': round(float(row['Compression_Force']), 2),
        'Machine_Speed': round(float(row['Machine_Speed']), 2),
        'Lubricant_Conc': round(float(row['Lubricant_Conc']), 2),
    }