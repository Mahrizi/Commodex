import os, datetime as dt
from typing import Optional
from fastapi import FastAPI
import pandas as pd
from sklearn.linear_model import Ridge
import psycopg2, psycopg2.extras

# Get DB connection URL from environment variable set in Render
DATABASE_URL = os.environ.get("DATABASE_URL")

app = FastAPI(title="Price Tracker API", version="1.0")

def query(sql, params=None):
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or [])
            if cur.description:
                return cur.fetchall()
            return []
    finally:
        conn.close()

@app.get("/api/v1/materials")
def list_materials():
    rows = query("SELECT id, name, unit FROM materials ORDER BY id;")
    return {"materials": rows}

@app.get("/api/v1/prices")
def get_prices(material_id: int, date_from: Optional[str] = None, date_to: Optional[str] = None):
    conditions = ["material_id=%s"]
    params = [material_id]
    if date_from:
        conditions.append("recorded_at >= %s"); params.append(date_from)
    if date_to:
        conditions.append("recorded_at <= %s"); params.append(date_to)
    sql = f"SELECT recorded_at, price, currency, unit, source FROM price_points WHERE {' AND '.join(conditions)} ORDER BY recorded_at;"
    rows = query(sql, params)
    return {"prices": rows}

@app.get("/api/v1/forecast")
def forecast(material_id: int, horizon: int = 30):
    hist = query("SELECT recorded_at, price FROM price_points WHERE material_id=%s ORDER BY recorded_at;", [material_id])
    if len(hist) < 7:
        return {"material_id": material_id, "horizon_days": horizon, "predictions": []}

    df = pd.DataFrame(hist)
    df["ds"] = pd.to_datetime(df["recorded_at"])
    df["t"] = (df["ds"] - df["ds"].min()).dt.days
    X, y = df[["t"]].values, df["price"].values
    model = Ridge(alpha=1.0).fit(X, y)

    last_t = int(df["t"].max())
    preds = []
    for d in range(1, horizon+1):
        t = last_t + d
        yhat = float(model.predict([[t]])[0])
        preds.append({
            "date": (df["ds"].max() + pd.Timedelta(days=d)).date().isoformat(),
            "yhat": round(yhat, 2),
            "yhat_lower": round(yhat * 0.97, 2),
            "yhat_upper": round(yhat * 1.03, 2)
        })
    return {"material_id": material_id, "horizon_days": horizon, "predictions": preds}

@app.get("/health")
def health():
    try:
        query("SELECT 1;")
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
