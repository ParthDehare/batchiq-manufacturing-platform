import pandas as pd
import numpy as np

PHASE_ENERGY_SHARE = {
    'Compression': 50.4,
    'Drying': 13.1,
    'Milling': 11.7,
    'Coating': 8.8,
    'Blending': 6.0,
    'Granulation': 4.9,
    'Quality_Testing': 3.8,
    'Preparation': 1.2
}

def compute_fingerprint(df2: pd.DataFrame) -> dict:
    results = {}
    for phase in df2['Phase'].unique():
        ph = df2[df2['Phase'] == phase]
        mean_p = ph['Power_Consumption_kW'].mean()
        std_p  = ph['Power_Consumption_kW'].std()
        mean_v = ph['Vibration_mm_s'].mean()
        std_v  = ph['Vibration_mm_s'].std()

        power_series = ph['Power_Consumption_kW'].tolist()
        vib_series   = ph['Vibration_mm_s'].tolist()
        time_series  = ph['Time_Minutes'].tolist()

        results[phase] = {
            'mean_power':      round(float(mean_p), 2),
            'ucl_power':       round(float(mean_p + 3 * std_p), 2),
            'lcl_power':       round(float(max(0, mean_p - 3 * std_p)), 2),
            'mean_vib':        round(float(mean_v), 3),
            'ucl_vib':         round(float(mean_v + 3 * std_v), 3),
            'energy_kwh':      round(float((ph['Power_Consumption_kW'] / 60).sum()), 3),
            'energy_share':    PHASE_ENERGY_SHARE.get(phase, 0),
            'power_anomalies': int((ph['Power_Consumption_kW'] > mean_p + 3*std_p).sum()),
            'vib_anomalies':   int((ph['Vibration_mm_s'] > mean_v + 3*std_v).sum()),
            'power_series':    [round(v, 2) for v in power_series],
            'vib_series':      [round(v, 3) for v in vib_series],
            'time_series':     time_series,
            'max_power':       round(float(ph['Power_Consumption_kW'].max()), 2),
            'max_vib':         round(float(ph['Vibration_mm_s'].max()), 3),
        }
    return results

def get_total_anomalies(fingerprint: dict) -> int:
    return sum(v['power_anomalies'] + v['vib_anomalies'] for v in fingerprint.values())

def get_phase_energy_chart_data(fingerprint: dict) -> dict:
    phases = list(PHASE_ENERGY_SHARE.keys())
    shares = [PHASE_ENERGY_SHARE[p] for p in phases]
    return {'labels': phases, 'data': shares}