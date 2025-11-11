#!/usr/bin/env python3
# scripts/eda.py
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

BASE = Path(__file__).resolve().parent
FP = BASE / "data" / "features.parquet"
OUT = BASE / "data" / "eda_outputs"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(FP)
print("Loaded features:", len(df))

# Top commodities
top_comms = df["commodity"].value_counts().index[:6].tolist()

# 1) time series PNG per commodity
for comm in top_comms:
    d = df[df["commodity"]==comm].sort_values("date")
    plt.figure(figsize=(12,4))
    sns.lineplot(data=d, x="date", y="modal_price", hue="market", legend=False)
    plt.title(f"{comm} — modal_price over time (markets overlay)")
    plt.xlabel("date")
    plt.ylabel("modal_price")
    plt.tight_layout()
    fname = OUT / f"ts_{comm.replace('/','_')}.png"
    plt.savefig(fname)
    plt.close()
    print("Saved", fname)

# 2) distribution
plt.figure(figsize=(8,5))
sns.histplot(df["modal_price"], bins=100, kde=True)
plt.title("Modal price distribution (all records)")
plt.savefig(OUT / "modal_price_dist.png")
plt.close()

# 3) interactive plotly per commodity
for comm in top_comms:
    d = df[df["commodity"]==comm].sort_values("date")
    fig = px.line(d, x="date", y="modal_price", color="market", title=f"{comm} — modal_price")
    html_file = OUT / f"interactive_{comm.replace('/','_')}.html"
    fig.write_html(html_file)
    print("Saved interactive", html_file)

# 4) ACF plots (optional) -- simple autocorrelation for one market/commodity
try:
    import statsmodels.api as sm
    sample = df[(df["commodity"]==top_comms[0]) & (df["market"].notnull())]
    if not sample.empty:
        s = sample.sort_values("date")["modal_price"].dropna()
        fig = sm.graphics.tsa.plot_acf(s, lags=30)
        fig.savefig(OUT / f"acf_{top_comms[0].replace('/','_')}.png")
        print("Saved ACF plot")
except Exception:
    print("statsmodels not installed or ACF failed; skip ACF.")
