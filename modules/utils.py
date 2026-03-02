import pandas as pd
import numpy as np

def df_to_json_safe(df):
    records = []
    for _, row in df.iterrows():
        rec = {}
        for k, v in row.items():
            if isinstance(v, (np.integer,)): rec[k] = int(v)
            elif isinstance(v, (np.floating,)):
                rec[k] = None if (np.isnan(v) or np.isinf(v)) else round(float(v),4)
            elif isinstance(v, float):
                rec[k] = None if (np.isnan(v) or np.isinf(v)) else round(v,4)
            else: rec[k] = v
        records.append(rec)
    return records

def validate_production_file(df):
    required = ['Batch_ID','Granulation_Time','Binder_Amount','Drying_Temp',
                'Drying_Time','Compression_Force','Machine_Speed','Lubricant_Conc']
    missing = [c for c in required if c not in df.columns]
    return {'valid': len(missing)==0, 'missing_columns': missing, 'row_count': len(df)}

def validate_process_file(df):
    required = ['Batch_ID','Time_Minutes','Phase','Power_Consumption_kW','Vibration_mm_s']
    missing = [c for c in required if c not in df.columns]
    return {'valid': len(missing)==0, 'missing_columns': missing, 'row_count': len(df)}