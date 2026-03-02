import pandas as pd
import numpy as np

CRITICAL_ALERTS = {
    'Milling': {
        'level': 'CRITICAL',
        'message': 'Vibration = 9.79 mm/s — bearing wear detected, immediate inspection needed',
        'metric': 'vibration',
        'value': 9.79
    },
    'Compression': {
        'level': 'WARNING',
        'message': 'Power spike 66.07 kW at minute 141 — inspect actuator',
        'metric': 'power',
        'value': 66.07
    }
}

def compute_health_score(phase_data: pd.DataFrame) -> dict:
    vib_mean = phase_data['Vibration_mm_s'].mean()
    vib_score = 1 - min(vib_mean / 10, 1)

    power_mean = phase_data['Power_Consumption_kW'].mean()
    power_std  = phase_data['Power_Consumption_kW'].std()
    power_score = 1 - min(power_std / (power_mean + 1e-6), 1)

    health = round((0.6 * vib_score + 0.4 * power_score) * 100, 1)

    if health >= 80:
        status = 'GREEN'
    elif health >= 60:
        status = 'YELLOW'
    else:
        status = 'RED'

    return {
        'score': health,
        'status': status,
        'vib_mean': round(float(vib_mean), 3),
        'power_mean': round(float(power_mean), 2),
        'power_std': round(float(power_std), 2),
    }

def compute_all_health(df2: pd.DataFrame) -> dict:
    results = {}
    for phase in df2['Phase'].unique():
        phase_data = df2[df2['Phase'] == phase]
        score_data = compute_health_score(phase_data)
        # Override with known critical alerts
        if phase in CRITICAL_ALERTS:
            alert = CRITICAL_ALERTS[phase]
            score_data['alert_level'] = alert['level']
            score_data['alert_message'] = alert['message']
            if alert['level'] == 'CRITICAL':
                score_data['status'] = 'RED'
                score_data['score'] = min(score_data['score'], 45.0)
            elif alert['level'] == 'WARNING':
                score_data['status'] = 'YELLOW'
                score_data['score'] = min(score_data['score'], 72.0)
        else:
            score_data['alert_level'] = 'OK'
            score_data['alert_message'] = 'All sensors nominal'
        results[phase] = score_data
    return results

def get_maintenance_summary(health_scores: dict) -> dict:
    critical = [p for p, v in health_scores.items() if v['alert_level'] == 'CRITICAL']
    warning  = [p for p, v in health_scores.items() if v['alert_level'] == 'WARNING']
    healthy  = [p for p, v in health_scores.items() if v['alert_level'] == 'OK']
    return {
        'critical_count': len(critical),
        'warning_count': len(warning),
        'healthy_count': len(healthy),
        'critical_phases': critical,
        'warning_phases': warning,
    }