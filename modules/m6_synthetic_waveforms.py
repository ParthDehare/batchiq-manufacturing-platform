import pandas as pd
import numpy as np

PARAM_COLS = ['Granulation_Time','Drying_Temp','Machine_Speed','Compression_Force']

def generate_waveform(batch_row: pd.Series, template_df: pd.DataFrame, baseline_params: dict) -> pd.DataFrame:
    deltas = {
        col: (batch_row[col] - baseline_params[col]) / (baseline_params[col] + 1e-6)
        for col in PARAM_COLS if col in batch_row.index
    }

    synthetic = template_df.copy()
    scale = (
        1
        + 0.3 * deltas.get('Compression_Force', 0)
        + 0.2 * deltas.get('Machine_Speed', 0)
        + 0.1 * deltas.get('Drying_Temp', 0)
    )

    np.random.seed(abs(hash(str(batch_row.get('Batch_ID', 0)))) % (2**31))
    synthetic['Power_Consumption_kW'] = (
        synthetic['Power_Consumption_kW'] * scale
        + np.random.normal(0, 1.5, len(synthetic))
    ).clip(lower=0)

    synthetic['Vibration_mm_s'] = (
        synthetic['Vibration_mm_s'] * (1 + 0.15 * deltas.get('Machine_Speed', 0))
        + np.random.normal(0, 0.1, len(synthetic))
    ).clip(lower=0)

    synthetic['Batch_ID'] = batch_row.get('Batch_ID', 'Unknown')
    return synthetic

def generate_all_waveforms(df1: pd.DataFrame, df2: pd.DataFrame) -> dict:
    t001 = df1[df1['Batch_ID'] == 'T001']
    if t001.empty:
        t001 = df1.iloc[[0]]

    baseline = {}
    for col in PARAM_COLS:
        if col in t001.columns:
            baseline[col] = float(t001.iloc[0][col])

    waveforms = {}
    for _, row in df1.iterrows():
        try:
            waveforms[row['Batch_ID']] = generate_waveform(row, df2, baseline)
        except Exception:
            pass
    return waveforms

def waveform_to_chart_data(waveform_df: pd.DataFrame, phase: str = None) -> dict:
    if phase:
        df = waveform_df[waveform_df['Phase'] == phase]
    else:
        df = waveform_df
    return {
        'time': df['Time_Minutes'].tolist(),
        'power': [round(v, 2) for v in df['Power_Consumption_kW'].tolist()],
        'vibration': [round(v, 3) for v in df['Vibration_mm_s'].tolist()],
        'phase': df['Phase'].tolist() if 'Phase' in df.columns else []
    }