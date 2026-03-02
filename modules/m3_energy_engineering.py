import pandas as pd

CO2_FACTOR = 0.82

def estimate_energy(row):
    return (0.8*(row['Drying_Temp']*row['Drying_Time']/60) +
            2.5*(row['Machine_Speed']/100) +
            0.3*row['Compression_Force'] +
            1.2*(row['Granulation_Time']/60*15))

def add_energy_co2(df):
    df = df.copy()
    required = ['Drying_Temp','Drying_Time','Machine_Speed','Compression_Force','Granulation_Time']
    if all(c in df.columns for c in required):
        df['Energy_kWh'] = df.apply(estimate_energy, axis=1)
        df['CO2_kg']     = df['Energy_kWh'] * CO2_FACTOR
    return df

def get_energy_stats(df):
    if 'Energy_kWh' not in df.columns:
        return {'min_energy':0,'max_energy':0,'mean_energy':0,'total_energy':0,'total_co2':0}
    return {
        'min_energy':  round(float(df['Energy_kWh'].min()),1),
        'max_energy':  round(float(df['Energy_kWh'].max()),1),
        'mean_energy': round(float(df['Energy_kWh'].mean()),1),
        'total_energy':round(float(df['Energy_kWh'].sum()),1),
        'total_co2':   round(float(df['CO2_kg'].sum()),1) if 'CO2_kg' in df.columns else 0,
    }

def carbon_budget_status(df, budget):
    used = float(df['CO2_kg'].sum()) if 'CO2_kg' in df.columns else 0
    avg  = float(df['CO2_kg'].mean()) if 'CO2_kg' in df.columns else 1
    return {'budget':budget,'used':round(used,1),
            'remaining_kg':round(budget-used,1),
            'batches_remaining':int(max(0,(budget-used)/avg)),
            'status':'ON_TRACK' if used < budget*0.8 else 'AT_RISK'}