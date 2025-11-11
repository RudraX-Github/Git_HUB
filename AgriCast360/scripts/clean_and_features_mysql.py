#!/usr/bin/env python3
# scripts/clean_and_features_mysql.py

import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

# Base directory
BASE = Path(__file__).resolve().parent

# Load environment variables if .env exists
if (BASE / ".env").exists():
    load_dotenv(BASE / ".env")

# Database credentials (with sensible defaults)
USER = os.getenv("MYSQL_USER", "root")
PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
PORT = os.getenv("MYSQL_PORT", "3306")
DB = os.getenv("MYSQL_DB", "agricast")

# SQLAlchemy connection string
CONN_STR = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}?charset=utf8mb4"
engine = create_engine(CONN_STR, pool_pre_ping=True)

# Output path for parquet file
OUT_PARQUET = BASE / "data" / "features.parquet"
OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)

def load_raw():
    """Load raw commodity prices from MySQL"""
    q = "SELECT * FROM commodity_prices"
    return pd.read_sql(q, engine, parse_dates=["date"])

def basic_clean(df):
    """Clean and normalize raw data"""
    df = df.dropna(subset=["date", "market", "commodity"])
    # numeric conversion
    for c in ["min_price", "max_price", "modal_price"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # fill modal_price from min/max when possible
    mask = df["modal_price"].isna() & df["min_price"].notna() & df["max_price"].notna()
    df.loc[mask, "modal_price"] = (df.loc[mask, "min_price"] + df.loc[mask, "max_price"]) / 2
    # remove non-positive and extreme outliers
    df = df[df["modal_price"] > 0]
    upper = df["modal_price"].quantile(0.999)
    df = df[df["modal_price"] <= upper]
    # normalize text fields
    for c in ["market", "commodity", "variety", "state", "district", "unit", "grade"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().replace({"nan": None})
    return df

def make_features(df):
    """Generate lag features, rolling stats, and date parts"""
    df = df.sort_values(["commodity", "market", "date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["weekday"] = df["date"].dt.weekday
    # lag features
    for lag in (1, 7, 14, 30):
        df[f"lag_{lag}"] = df.groupby(["market", "commodity"])["modal_price"].shift(lag)
    # rolling features
    df["rolling_mean_7"] = df.groupby(["market", "commodity"])["modal_price"].transform(
        lambda x: x.rolling(7, min_periods=1).mean()
    )
    df["rolling_std_30"] = df.groupby(["market", "commodity"])["modal_price"].transform(
        lambda x: x.rolling(30, min_periods=1).std()
    ).fillna(0)
    # percentage change
    df["pct_change_1"] = df.groupby(["market", "commodity"])["modal_price"].pct_change(1)
    # drop rows missing lag_1 (common for supervised next-day prediction)
    df = df.dropna(subset=["lag_1"])
    return df

def save_features(df):
    """Save features to parquet and MySQL"""
    df.to_parquet(OUT_PARQUET, index=False)
    df.to_sql("features", engine, if_exists="replace", index=False, method="multi", chunksize=500)

def main():
    print("Loading raw data from MySQL...")
    df = load_raw()
    print("Raw rows:", len(df))
    df = basic_clean(df)
    print("After cleaning:", len(df))
    df = make_features(df)
    print("After features:", len(df))
    save_features(df)
    print("Saved features to", OUT_PARQUET, "and to MySQL table 'features'")

if __name__ == "__main__":
    main()
