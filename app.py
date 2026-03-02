import os, json, traceback, shutil
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
from modules.m1_quality_prediction import (
    train_quality_model, predict_quality, check_pass_fail,
    predict_batch_df, get_shap_values, FEATURE_COLS, TARGET_COLS, SPEC_LIMITS
)
from modules.m2_energy_fingerprint import compute_fingerprint
from modules.m3_energy_engineering import add_energy_co2, get_energy_stats, carbon_budget_status
from modules.m4_golden_batch      import score_batches, get_golden_batch_params, DEFAULT_WEIGHTS
from modules.m5_asset_health      import compute_all_health, get_maintenance_summary
from modules.utils                import df_to_json_safe, validate_production_file, validate_process_file

app = Flask(__name__)
app.secret_key = 'batchiq-secret-2024'

BASE_DIR   = os.path.dirname(__file__)
DATA_DIR   = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
PROD_FILE  = os.path.join(DATA_DIR, 'batch_production_data.xlsx')
PROC_FILE  = os.path.join(DATA_DIR, 'batch_process_data.xlsx')
ALLOWED_EXT = {'xlsx', 'xls'}
os.makedirs(DATA_DIR,   exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

state = dict(df1=None,df2=None,model=None,scaler=None,fingerprint=None,
             health_scores=None,energy_stats={},ranked_df=None,
             golden_id='T059',golden_score=0.0,loaded=False)

def load_and_init(force_retrain=False):
    global state
    if not os.path.exists(PROD_FILE):
        print("batch_production_data.xlsx missing"); return False
    if not os.path.exists(PROC_FILE):
        print("batch_process_data.xlsx missing");   return False
    try:
        print("Loading data...")
        df1 = pd.read_excel(PROD_FILE); df1.columns = df1.columns.str.strip()
        df2 = pd.read_excel(PROC_FILE); df2.columns = df2.columns.str.strip()
        df1 = add_energy_co2(df1)
        import joblib
        pkl = os.path.join(MODELS_DIR, 'quality_model.pkl')
        if force_retrain or not os.path.exists(pkl):
            print("Training model..."); model, scaler = train_quality_model(df1, MODELS_DIR)
        else:
            print("Loading cached model")
            model  = joblib.load(os.path.join(MODELS_DIR, 'quality_model.pkl'))
            scaler = joblib.load(os.path.join(MODELS_DIR, 'scaler.pkl'))
        fingerprint   = compute_fingerprint(df2)
        health_scores = compute_all_health(df2)
        energy_stats  = get_energy_stats(df1)
        ranked_df     = score_batches(df1)
        # Merge composite score back into df1
        df1 = df1.merge(ranked_df[['Batch_ID','composite_score']], on='Batch_ID', how='left')
        golden_id    = str(ranked_df.iloc[0]['Batch_ID'])
        golden_score = float(ranked_df.iloc[0]['composite_score'])
        # Compute pass/fail via ML
        avail = [c for c in FEATURE_COLS if c in df1.columns]
        if len(avail) == len(FEATURE_COLS):
            X_sc = scaler.transform(df1[FEATURE_COLS].values)
            preds = model.predict(X_sc)
            pdf   = pd.DataFrame(preds, columns=TARGET_COLS, index=df1.index)
            fail  = pd.Series(False, index=df1.index)
            for col,(lo,hi) in SPEC_LIMITS.items():
                if col in pdf.columns:
                    if lo is not None: fail |= pdf[col] < lo
                    if hi is not None: fail |= pdf[col] > hi
            df1['_pass'] = ~fail
        state.update(df1=df1,df2=df2,model=model,scaler=scaler,
                     fingerprint=fingerprint,health_scores=health_scores,
                     energy_stats=energy_stats,ranked_df=ranked_df,
                     golden_id=golden_id,golden_score=golden_score,loaded=True)
        fc = int((~df1['_pass']).sum()) if '_pass' in df1.columns else '?'
        print(f"Ready | Golden:{golden_id} | Fails:{fc}/{len(df1)}")
        return True
    except Exception as e:
        print(f"Init error: {e}"); traceback.print_exc(); return False

def allowed_file(fn):
    return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED_EXT

def get_fail_info():
    df1 = state['df1']
    if df1 is None: return [],0,0
    if '_pass' in df1.columns:
        fail_ids = df1[~df1['_pass']]['Batch_ID'].astype(str).tolist()
    else:
        fail_ids = []
    total = len(df1)
    return fail_ids, len(fail_ids), total

@app.route('/')
def index():
    s = state
    fail_ids, fail_count, total = get_fail_info()
    fail_rate = round(fail_count/total*100,1) if total else 0
    df1 = s['df1']
    fp  = s['fingerprint']
    hs  = s['health_scores']
    es  = s['energy_stats']
    # Compression share from real fingerprint
    comp_share = 50.4
    if fp:
        total_e = sum(v['energy_kwh'] for v in fp.values()) or 1
        if 'Compression' in fp:
            comp_share = round(fp['Compression']['energy_kwh']/total_e*100,1)
    maint = get_maintenance_summary(hs) if hs else {'critical_count':0,'critical_phases':[],'warning_count':0}
    # Top batches
    top_batches = []
    ranked_df = s['ranked_df']
    if ranked_df is not None:
        for _, row in ranked_df.head(10).iterrows():
            bid = str(row['Batch_ID'])
            top_batches.append({'id':bid,
                'score':      round(float(row['composite_score']),4),
                'hardness':   round(float(row.get('Hardness',0)),1),
                'dissolution':round(float(row.get('Dissolution_Rate',0)),1),
                'energy':     round(float(row.get('Energy_kWh',0)),1),
                'status':     'FAIL' if bid in fail_ids else 'PASS'})
    # Batch chart
    batch_chart = []
    if df1 is not None and 'composite_score' in df1.columns:
        for _, row in df1.iterrows():
            batch_chart.append({'id':str(row['Batch_ID']),
                'score':round(float(row['composite_score']),3),
                'pass': bool(row.get('_pass', True))})
    # Phase energy donut from real data
    phase_energy = {}
    if fp:
        total_e = sum(v['energy_kwh'] for v in fp.values()) or 1
        for ph,v in fp.items():
            phase_energy[ph] = round(v['energy_kwh']/total_e*100,1)
    kpis = dict(loaded=s['loaded'],fail_count=fail_count,total=total,fail_rate=fail_rate,
                golden_id=s['golden_id'],golden_score=round(s['golden_score'],4),
                energy_min=es.get('min_energy',0),energy_max=es.get('max_energy',0),
                energy_mean=es.get('mean_energy',0),
                co2_mean=round(es.get('total_co2',0)/total,1) if total else 0,
                compression_share=comp_share,
                critical_count=maint['critical_count'],
                critical_phases=maint['critical_phases'],
                warning_count=maint['warning_count'])
    return render_template('index.html', kpis=kpis, top_batches=top_batches,
                           batch_chart=json.dumps(batch_chart),
                           phase_energy=json.dumps(phase_energy),
                           fail_ids=fail_ids)

@app.route('/predict', methods=['GET','POST'])
def predict():
    s = state
    if not s['loaded']:
        flash('Upload your data files first.','error'); return redirect(url_for('upload'))
    df1=s['df1']; model=s['model']; scaler=s['scaler']
    ranges = {col:{'min':round(float(df1[col].min()),2),'max':round(float(df1[col].max()),2),
                   'mean':round(float(df1[col].mean()),2)} for col in FEATURE_COLS if col in df1.columns}
    golden_params = get_golden_batch_params(df1, s['golden_id'])
    result=None; shap_data=None; input_vals={}; error=None
    if request.method=='POST':
        try:
            input_vals = {col: float(request.form.get(col, ranges.get(col,{}).get('mean',0))) for col in FEATURE_COLS}
            input_list = [input_vals[c] for c in FEATURE_COLS]
            preds  = predict_quality(model, scaler, input_list)
            result = check_pass_fail(preds)
            try:
                shap_raw  = get_shap_values(model, scaler, input_list, 2)
                shap_data = json.dumps(shap_raw)
            except: shap_data=None
        except Exception as e:
            error=str(e); traceback.print_exc()
    return render_template('predict.html', result=result, shap_data=shap_data,
                           input_vals=input_vals, ranges=ranges,
                           feature_cols=FEATURE_COLS, golden_params=golden_params, error=error)

@app.route('/energy')
def energy():
    s = state
    if not s['loaded']:
        flash('Upload your data files first.','error'); return redirect(url_for('upload'))
    fp=s['fingerprint']; es=s['energy_stats']; df1=s['df1']
    phase_rows=[]
    if fp:
        total_e = sum(v['energy_kwh'] for v in fp.values()) or 1
        for ph,v in fp.items():
            phase_rows.append({'phase':ph,'mean_power':v['mean_power'],'ucl_power':v['ucl_power'],
                'lcl_power':v['lcl_power'],'max_power':v['max_power'],'mean_vib':v['mean_vib'],
                'max_vib':v['max_vib'],'energy_kwh':v['energy_kwh'],
                'energy_pct':round(v['energy_kwh']/total_e*100,1),
                'power_anomalies':v['power_anomalies'],'vib_anomalies':v['vib_anomalies']})
    phase_rows.sort(key=lambda x: x['energy_pct'], reverse=True)
    chart_labels = json.dumps([r['phase'] for r in phase_rows])
    chart_energy = json.dumps([r['energy_pct'] for r in phase_rows])
    chart_power  = json.dumps([r['mean_power'] for r in phase_rows])
    batch_energy = []
    if df1 is not None and 'Energy_kWh' in df1.columns:
        for _,row in df1.iterrows():
            batch_energy.append({'id':str(row['Batch_ID']),
                'energy':round(float(row['Energy_kWh']),2),'co2':round(float(row['CO2_kg']),2)})
    return render_template('energy.html', phase_rows=phase_rows, energy_stats=es,
                           chart_labels=chart_labels, chart_energy=chart_energy,
                           chart_power=chart_power, batch_energy=json.dumps(batch_energy))

@app.route('/golden-batch')
def golden_batch():
    s = state
    if not s['loaded']:
        flash('Upload your data files first.','error'); return redirect(url_for('upload'))
    df1=s['df1']; ranked_df=s['ranked_df']
    top10=[]
    for _,row in ranked_df.head(10).iterrows():
        top10.append({'batch_id':str(row['Batch_ID']),
            'score':      round(float(row['composite_score']),4),
            'hardness':   round(float(row.get('Hardness',0)),1),
            'friability': round(float(row.get('Friability',0)),3),
            'dissolution':round(float(row.get('Dissolution_Rate',0)),1),
            'uniformity': round(float(row.get('Content_Uniformity',0)),1),
            'moisture':   round(float(row.get('Moisture_Content',0)),2),
            'energy':     round(float(row.get('Energy_kWh',0)),1)})
    all_scores = [{'id':str(r['Batch_ID']),'score':round(float(r['composite_score']),4)}
                  for _,r in ranked_df.iterrows()]
    golden_params = get_golden_batch_params(df1, s['golden_id'])
    return render_template('golden_batch.html', golden_id=s['golden_id'],
                           golden_score=round(s['golden_score'],4), top10=top10,
                           all_scores=json.dumps(all_scores), golden_params=golden_params,
                           default_weights=DEFAULT_WEIGHTS)

@app.route('/health')
def health():
    s = state
    if not s['loaded']:
        flash('Upload your data files first.','error'); return redirect(url_for('upload'))
    hs=s['health_scores']; maint=get_maintenance_summary(hs)
    health_chart = {'labels':list(hs.keys()),
        'scores':[v['score'] for v in hs.values()],
        'colors':['#ef4444' if v['score']<60 else '#f59e0b' if v['score']<80 else '#22c55e'
                  for v in hs.values()]}
    return render_template('health.html', health_scores=hs, maint=maint,
                           health_chart=json.dumps(health_chart))

@app.route('/upload', methods=['GET','POST'])
def upload():
    upload_result=None
    if request.method=='POST':
        file      = request.files.get('file')
        file_type = request.form.get('file_type','predict_only')
        if not file or file.filename=='':
            flash('No file selected.','error'); return redirect(request.url)
        if not allowed_file(file.filename):
            flash('Only .xlsx or .xls accepted.','error'); return redirect(request.url)
        save_path = os.path.join(DATA_DIR, secure_filename(file.filename))
        file.save(save_path)
        try:
            new_df = pd.read_excel(save_path); new_df.columns = new_df.columns.str.strip()
            if file_type=='production':
                val = validate_production_file(new_df)
                if not val['valid']:
                    flash(f'Missing columns: {val["missing_columns"]}','error'); return redirect(request.url)
                if os.path.abspath(save_path) != os.path.abspath(PROD_FILE):
                 shutil.copy(save_path, PROD_FILE)
                for f in ['quality_model.pkl','scaler.pkl']:
                    p=os.path.join(MODELS_DIR,f)
                    if os.path.exists(p): os.remove(p)
                ok = load_and_init(force_retrain=True)
                if ok:
                    flash(f'Production data loaded & model retrained on {len(new_df)} batches!','success')
                    preds = predict_batch_df(state['model'],state['scaler'],state['df1'])
                    upload_result={'type':'production','rows':len(new_df),
                                   'predictions':df_to_json_safe(preds) if not preds.empty else []}
                else:
                    flash('Upload ok but init failed — check terminal.','error')
            elif file_type=='process':
                val = validate_process_file(new_df)
                if not val['valid']:
                    flash(f'Missing columns: {val["missing_columns"]}','error'); return redirect(request.url)
                if os.path.abspath(save_path) != os.path.abspath(PROC_FILE):    # ← ADD THIS
                 shutil.copy(save_path, PROC_FILE)
                ok = load_and_init()
                if ok: flash('Process sensor data loaded & analytics refreshed!','success')
                upload_result={'type':'process','rows':len(new_df),'predictions':[]}
            else:
                if not state['loaded']:
                    flash('Load base data first before predict-only mode.','error'); return redirect(request.url)
                new_df = add_energy_co2(new_df)
                preds  = predict_batch_df(state['model'],state['scaler'],new_df)
                flash(f'Predictions generated for {len(new_df)} batches!','success')
                upload_result={'type':'predict_only','rows':len(new_df),
                               'predictions':df_to_json_safe(preds) if not preds.empty else []}
        except Exception as e:
            flash(f'Error: {e}','error'); traceback.print_exc()
    return render_template('upload.html', upload_result=upload_result, loaded=state['loaded'])

@app.route('/api/predict', methods=['POST'])
def api_predict():
    try:
        data=[float(request.json.get(c,0)) for c in FEATURE_COLS]
        return jsonify({'ok':True,'predictions':check_pass_fail(predict_quality(state['model'],state['scaler'],data))})
    except Exception as e:
        return jsonify({'ok':False,'error':str(e)}),400

@app.route('/api/golden-batch', methods=['POST'])
def api_golden_batch():
    try:
        ranked=score_batches(state['df1'],request.json or None)
        t=ranked.head(10)[['Batch_ID','composite_score']].copy()
        t['composite_score']=t['composite_score'].round(4)
        return jsonify({'golden_batch':str(ranked.iloc[0]['Batch_ID']),
                        'score':round(float(ranked.iloc[0]['composite_score']),4),
                        'top10':df_to_json_safe(t)})
    except Exception as e:
        return jsonify({'ok':False,'error':str(e)}),400

@app.route('/api/health')
def api_health():
    return jsonify(state['health_scores'] or {})

@app.route('/api/status')
def api_status():
    s=state
    return jsonify({'loaded':s['loaded'],'golden_id':s['golden_id'],
                    'golden_score':s['golden_score'],
                    'total_batches':len(s['df1']) if s['df1'] is not None else 0})

if __name__=='__main__':
    load_and_init()
    app.run(debug=True, port=5000, use_reloader=False)