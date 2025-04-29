# app.py
import os
import json
import pandas as pd
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
CSV_PATH = os.path.join(app.root_path, 'static', 'data_short.csv')

def load_df():
    df = pd.read_csv(CSV_PATH)

    for col in df.columns:
        if df[col].dtype == 'object':
            cleaned = (
                df[col]
                .astype(str)
                .str.replace(r'[\$,]', '', regex=True)
                .str.strip()
            )
            try:
                df[col] = pd.to_numeric(cleaned)
            except Exception:
                pass

    # Keep dates as strings for JSON
    df['MostRecentSaleDate'] = df['MostRecentSaleDate'].astype(str)
    return df

@app.route('/')
def home():
    return render_template('main.html')

@app.route('/chart')
def chart():
    df = load_df()

    numeric_cols     = df.select_dtypes(include='number').columns.tolist()
    categorical_cols = [c for c in df.columns if c not in numeric_cols]
    all_cols         = numeric_cols + categorical_cols

    payload = {
        'x': df['MostRecentSaleDate'].tolist(),
        'y': [
            None if pd.isna(v) else float(v)
            for v in df['MostRecentSalePrice'].tolist()
        ],
        'y_col': 'MostRecentSalePrice',
        'numeric_cols': numeric_cols,
        'all_cols': all_cols
    }

    return render_template('chart.html', payload=json.dumps(payload))

@app.route('/data')
def data():
    df        = load_df()
    ycol      = request.args.get('ycol')
    chart_typ = request.args.get('chart_type', 'ts')

    if ycol not in df.columns:
        return jsonify(error=f"column {ycol!r} not found"), 400

    #Time‐series
    if chart_typ == 'ts':
        if not pd.api.types.is_numeric_dtype(df[ycol]):
            return jsonify(error=f"column {ycol!r} not numeric"), 400
        df['dt']  = pd.to_datetime(df['MostRecentSaleDate'])
        monthly   = df.set_index('dt')[ycol].resample('M').mean().dropna()
        x         = monthly.index.strftime('%Y-%m').tolist()
        y         = [float(v) for v in monthly.tolist()]
        return jsonify(x=x, y=y, y_col=ycol)

    #Histogram
    if chart_typ == 'hist':
        if not pd.api.types.is_numeric_dtype(df[ycol]):
            return jsonify(error=f"column {ycol!r} not numeric"), 400
        raw_y = df[ycol].dropna().tolist()
        return jsonify(raw_y=[float(v) for v in raw_y])

    #Counts by field
    if chart_typ == 'bar_counts':
        grp = df[ycol].dropna().value_counts()
        return jsonify(x=grp.index.tolist(), y=grp.tolist())

    #Average by neighborhood
    if chart_typ == 'bar_nbhd':
        if not pd.api.types.is_numeric_dtype(df[ycol]):
            return jsonify(error=f"column {ycol!r} not numeric"), 400
        grp = df.groupby('nbhd')[ycol].mean().dropna()
        x   = grp.index.tolist()
        y   = [float(v) for v in grp.tolist()]
        return jsonify(x=x, y=y)

    return jsonify(error="unknown chart_type"), 400

if __name__ == '__main__':
    app.run(debug=True)
