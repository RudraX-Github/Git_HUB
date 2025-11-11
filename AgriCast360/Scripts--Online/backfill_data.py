import os
import time
import logging
from datetime import datetime, date, timedelta

import pandas as pd
import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")
CSV_PATH = "Agmarknet_Price_Report.csv"

MARKET_COORDINATES = {
    "Bardoli": (21.1240, 73.1115),
    "Bardoli(Kat)": (21.1255, 73.1132),
    "Bardoli(Ma)": (21.1268, 73.1101),
    "Kosamba": (21.4836, 72.9612),
    "Kosamba(D)": (21.4850, 72.9630),
    "Mahuva": (21.0936, 71.7717),
    "Mahuva(Am)": (21.0952, 71.7733),
    "Mandvi": (21.2553, 73.3041),
    "Nizar": (21.3733, 74.1982),
    "Nizar(Kuka)": (21.3750, 74.2000),
    "Nizar(Pumb)": (21.3765, 74.2020),
    "S.Mandvi": (21.2553, 73.3041),
    "Songadh": (21.1697, 73.5636),
    "Songadh(B)": (21.1712, 73.5650),
    "Songadh(U)": (21.1725, 73.5665),
    "Surat": (21.1702, 72.8311),
    "Uchhal": (21.3850, 73.6330),
    "Valod": (21.1250, 73.2080),
    "Valod(Buh)": (21.1265, 73.2095),
    "Vyara(Pan)": (21.1150, 73.3930),
    "Vyra": (21.1140, 73.3915)
}

# fixed safe date range requested from Open-Meteo
SAFE_START = date(2023, 1, 1)
SAFE_END = date(2024, 1, 1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def ensure_tables(conn):
    CREATE_COMMODITY_DDL = """
    CREATE TABLE IF NOT EXISTS commodity_prices (
        time TIMESTAMP WITHOUT TIME ZONE NOT NULL,
        market TEXT NOT NULL,
        commodity TEXT NOT NULL,
        modal_price NUMERIC,
        min_price NUMERIC,
        max_price NUMERIC,
        PRIMARY KEY (time, market, commodity)
    );"""
    CREATE_WEATHER_DDL = """
    CREATE TABLE IF NOT EXISTS weather_data (
        time DATE NOT NULL,
        market TEXT NOT NULL,
        temp_c DOUBLE PRECISION,
        precipitation_mm DOUBLE PRECISION,
        PRIMARY KEY (time, market)
    );"""
    CREATE_INDEXES = """
    CREATE INDEX IF NOT EXISTS idx_commodity_market ON commodity_prices (market);
    CREATE INDEX IF NOT EXISTS idx_weather_market ON weather_data (market);
    """
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_COMMODITY_DDL)
            cur.execute(CREATE_WEATHER_DDL)
            cur.execute(CREATE_INDEXES)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def bulk_insert_to_db(conn, df: pd.DataFrame, table_name: str):
    if df.empty:
        logger.info("No data to insert into %s.", table_name)
        return
    df_columns = list(df.columns)
    quoted_cols = ",".join([f'"{c}"' for c in df_columns])
    tpls = [tuple(x) for x in df.to_numpy()]
    sql = f"INSERT INTO {table_name} ({quoted_cols}) VALUES %s ON CONFLICT DO NOTHING"
    try:
        with conn.cursor() as cursor:
            execute_values(cursor, sql, tpls)
        conn.commit()
        logger.info("Inserted %d rows into %s.", len(df), table_name)
    except Exception:
        conn.rollback()
        raise


def fetch_historical_weather(lat, lon, start_dt, end_dt, chunk_days=365):
    if isinstance(start_dt, str):
        start_dt = datetime.fromisoformat(start_dt).date()
    if isinstance(end_dt, str):
        end_dt = datetime.fromisoformat(end_dt).date()

    # clamp to SAFE range
    if start_dt < SAFE_START:
        start_dt = SAFE_START
    if end_dt > SAFE_END:
        end_dt = SAFE_END
    if start_dt > end_dt:
        return pd.DataFrame()

    url = "https://archive-api.open-meteo.com/v1/archive"
    cur_start = start_dt
    results = []
    while cur_start <= end_dt:
        cur_end = min(end_dt, cur_start + timedelta(days=chunk_days - 1))
        params = {
            "latitude": float(lat),
            "longitude": float(lon),
            "start_date": cur_start.isoformat(),
            "end_date": cur_end.isoformat(),
            "daily": "temperature_2m_mean,precipitation_sum",
            "timezone": "auto"
        }
        try:
            res = requests.get(url, params=params, timeout=60)
            res.raise_for_status()
            payload = res.json()
            data = payload.get("daily", {})
            if data:
                df = pd.DataFrame(data)
                df.rename(columns={"temperature_2m_mean": "temp_c", "precipitation_sum": "precipitation_mm"}, inplace=True)
                df["time"] = pd.to_datetime(df["time"])
                results.append(df[["time", "temp_c", "precipitation_mm"]])
        except requests.exceptions.HTTPError as he:
            logger.error("HTTP error %s-%s for %s,%s: %s", cur_start, cur_end, lat, lon, he)
            break
        except Exception as e:
            logger.exception("Error fetching weather chunk %s-%s for %s,%s: %s", cur_start, cur_end, lat, lon, e)
        cur_start = cur_end + timedelta(days=1)
        time.sleep(1.0)

    if not results:
        return pd.DataFrame()
    combined = pd.concat(results, ignore_index=True).drop_duplicates(subset=["time"])
    combined.sort_values("time", inplace=True)
    return combined


def detect_columns(df: pd.DataFrame):
    cols = list(df.columns)
    lower = {c: c.lower() for c in cols}
    date_col = None
    for candidate in ["arrival_date", "date", "time", "timestamp"]:
        for c, lc in lower.items():
            if candidate == lc or candidate in lc:
                date_col = c
                break
        if date_col:
            break
    market_col = None
    for candidate in ["market", "mandi", "place", "market_name"]:
        for c, lc in lower.items():
            if candidate == lc or candidate in lc:
                market_col = c
                break
        if market_col:
            break
    commodity_col = None
    for candidate in ["commodity", "product", "item"]:
        for c, lc in lower.items():
            if candidate == lc or candidate in lc:
                commodity_col = c
                break
        if commodity_col:
            break
    modal_col = None
    for c, lc in lower.items():
        if "modal" in lc and "price" in lc:
            modal_col = c
            break
    if not modal_col:
        price_like = [c for c, lc in lower.items() if "price" in lc]
        if price_like:
            for p in price_like:
                plc = p.lower()
                if "min" not in plc and "max" not in plc:
                    modal_col = p
                    break
            if not modal_col:
                modal_col = price_like[0]
    min_col = None
    max_col = None
    for c, lc in lower.items():
        if "min" in lc and "price" in lc:
            min_col = c
        if "max" in lc and "price" in lc:
            max_col = c
    return {"date": date_col, "market": market_col, "commodity": commodity_col, "modal": modal_col, "min": min_col, "max": max_col}


def run_backfill():
    logger.info("Starting backfill")
    try:
        price_df = pd.read_csv(CSV_PATH, low_memory=False)
    except FileNotFoundError:
        logger.error("%s not found", CSV_PATH)
        return
    except Exception as e:
        logger.exception("Error reading CSV: %s", e)
        return

    mapping = detect_columns(price_df)
    logger.info("Detected columns mapping: %s", mapping)
    if not mapping["date"] or not mapping["market"] or not mapping["commodity"] or not mapping["modal"]:
        logger.error("Couldn't detect required columns. CSV headers: %s", list(price_df.columns))
        return

    price_df.rename(columns={
        mapping["date"]: "time",
        mapping["market"]: "market",
        mapping["commodity"]: "commodity",
        mapping["modal"]: "modal_price"
    }, inplace=True)
    if mapping["min"]:
        price_df.rename(columns={mapping["min"]: "min_price"}, inplace=True)
    if mapping["max"]:
        price_df.rename(columns={mapping["max"]: "max_price"}, inplace=True)

    price_df["time"] = pd.to_datetime(price_df["time"], errors="coerce")
    price_df = price_df.dropna(subset=["time"])
    price_df = price_df[price_df["market"].isin(MARKET_COORDINATES.keys())]
    price_df = price_df.dropna(subset=["modal_price"])
    for c in ["min_price", "max_price"]:
        if c not in price_df.columns:
            price_df[c] = pd.NA
    price_df = price_df[["time", "market", "commodity", "modal_price", "min_price", "max_price"]]

    logger.info("Found %d price records after filtering", len(price_df))
    if price_df.empty:
        logger.info("No matching records")
        return

    # Use SAFE range (clamp CSV range into SAFE window)
    csv_min = price_df["time"].min().date()
    csv_max = price_df["time"].max().date()
    min_date = max(SAFE_START, csv_min)
    max_date = min(SAFE_END, csv_max)
    if min_date > max_date:
        logger.error("No overlap between CSV dates (%s-%s) and SAFE range (%s-%s)", csv_min, csv_max, SAFE_START, SAFE_END)
        return

    logger.info("Weather date range used: %s -> %s", min_date.isoformat(), max_date.isoformat())

    all_weather_df = pd.DataFrame()
    for market, (lat, lon) in MARKET_COORDINATES.items():
        weather_df = fetch_historical_weather(lat, lon, min_date, max_date)
        if weather_df.empty:
            logger.info("No weather for %s", market)
            continue
        weather_df["market"] = market
        all_weather_df = pd.concat([all_weather_df, weather_df], ignore_index=True)
        time.sleep(1.0)

    logger.info("Fetched %d total weather records.", len(all_weather_df))

    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        return

    logger.info("Connecting to DB")
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            ensure_tables(conn)

            price_to_insert = price_df.copy()
            price_to_insert["time"] = pd.to_datetime(price_to_insert["time"]).dt.tz_localize(None)
            for col in ["modal_price", "min_price", "max_price"]:
                price_to_insert[col] = pd.to_numeric(price_to_insert[col], errors="coerce")
            bulk_insert_to_db(conn, price_to_insert, "commodity_prices")

            if not all_weather_df.empty:
                weather_to_insert = all_weather_df.copy()
                weather_to_insert["time"] = pd.to_datetime(weather_to_insert["time"]).dt.date
                weather_to_insert["temp_c"] = pd.to_numeric(weather_to_insert["temp_c"], errors="coerce")
                weather_to_insert["precipitation_mm"] = pd.to_numeric(weather_to_insert["precipitation_mm"], errors="coerce")
                weather_to_insert = weather_to_insert[["time", "market", "temp_c", "precipitation_mm"]]
                bulk_insert_to_db(conn, weather_to_insert, "weather_data")

            logger.info("Backfill complete")
    except Exception as e:
        logger.exception("DB error: %s", e)


if __name__ == "__main__":
    run_backfill()
