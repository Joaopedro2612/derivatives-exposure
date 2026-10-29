"""Relatório de exposição (Delta, Gamma, Vega), cenários e limites de uma carteira de opções USD/BRL."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import greeks

BUCKET_EDGES = [0, 30, 90, 180, 10_000]
BUCKET_LABELS = ["até 30d", "31-90d", "91-180d", ">180d"]
REQUIRED = {"trade_id", "kind", "strike", "days_to_maturity", "vol", "quantity_usd"}


def load_portfolio(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Colunas ausentes no arquivo: {sorted(missing)}")
    df["t"] = df["days_to_maturity"] / 365.0
    return df


def add_exposures(df, spot, r_dom, r_for) -> pd.DataFrame:
    args = (df["kind"], spot, df["strike"], df["t"], r_dom, r_for, df["vol"])
    delta, gamma, vega = greeks.greeks(*args)
    out = df.copy()
    out["premium_brl"] = greeks.price(*args) * out["quantity_usd"]
    out["delta_usd"] = delta * out["quantity_usd"]                       # exposição em USD
    out["gamma_usd_1pct"] = gamma * 0.01 * spot * out["quantity_usd"]    # variação do delta (USD) para +1% no spot
    out["vega_brl_1pt"] = vega * 0.01 * out["quantity_usd"]              # P&L (BRL) para +1 ponto de vol
    out["bucket"] = pd.cut(out["days_to_maturity"], BUCKET_EDGES, labels=BUCKET_LABELS)
    return out


def exposure_by_bucket(pos) -> pd.DataFrame:
    cols = ["delta_usd", "gamma_usd_1pct", "vega_brl_1pt"]
    return pos.groupby("bucket", observed=False)[cols].sum().round(0)


def scenario_pnl(df, spot, r_dom, r_for, spot_shocks, vol_shocks) -> pd.DataFrame:
    """P&L (BRL) por reavaliação completa: choque de spot (linhas) x choque de vol (colunas)."""
    base = greeks.price(df["kind"], spot, df["strike"], df["t"], r_dom, r_for, df["vol"])
    cols = {}
    for dv in vol_shocks:
        pnl = []
        for s in spot_shocks:
            new = greeks.price(df["kind"], spot * (1 + s), df["strike"], df["t"], r_dom, r_for, df["vol"] + dv)
            pnl.append(float(((new - base) * df["quantity_usd"]).sum()))
        cols[f"vol {dv * 100:+.0f}pt"] = pnl
    return pd.DataFrame(cols, index=[f"{s:+.0%}" for s in spot_shocks]).round(0)


def check_limits(totals: dict, limits: dict) -> pd.DataFrame:
    rows = []
    for metric, limit in limits.items():
        value = totals[metric]
        use = abs(value) / limit
        status = "ESTOURO" if use > 1 else ("ATENÇÃO" if use >= 0.8 else "OK")
        rows.append({"métrica": metric, "valor": round(value), "limite": limit, "uso": f"{use:.0%}", "status": status})
    return pd.DataFrame(rows)


def plot_report(by_bucket, scen, path):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].bar(by_bucket.index.astype(str), by_bucket["delta_usd"] / 1e6, color="#3b6ea8")
    axes[0].axhline(0, color="black", lw=0.8)
    axes[0].set(title="Delta por faixa de vencimento", ylabel="USD milhões")
    x = np.arange(len(scen))
    for col in scen.columns:
        axes[1].plot(x, scen[col] / 1e6, marker="o", label=col)
    axes[1].set_xticks(x, scen.index)
    axes[1].axhline(0, color="black", lw=0.8)
    axes[1].set(title="P&L por cenário (reavaliação completa)", xlabel="choque no spot", ylabel="BRL milhões")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", default="data/sample_portfolio.csv")
    p.add_argument("--limits", default="limits.json")
    p.add_argument("--spot", type=float, default=5.50, help="spot USD/BRL (ilustrativo)")
    p.add_argument("--r-dom", type=float, default=0.14, help="taxa BRL contínua (ilustrativa)")
    p.add_argument("--r-for", type=float, default=0.04, help="taxa USD contínua (ilustrativa)")
    p.add_argument("--out", default="outputs")
    a = p.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    df = load_portfolio(a.input)
    pos = add_exposures(df, a.spot, a.r_dom, a.r_for)
    by_bucket = exposure_by_bucket(pos)
    scen = scenario_pnl(df, a.spot, a.r_dom, a.r_for, [-0.10, -0.05, 0.0, 0.05, 0.10], [-0.03, 0.0, 0.03])
    totals = pos[["delta_usd", "gamma_usd_1pct", "vega_brl_1pt"]].sum().to_dict()
    limits = check_limits(totals, json.loads(Path(a.limits).read_text()))

    pos.drop(columns="t").to_csv(out / "positions.csv", index=False)
    by_bucket.to_csv(out / "exposure_by_bucket.csv")
    scen.to_csv(out / "scenarios.csv")
    limits.to_csv(out / "limits_check.csv", index=False)
    plot_report(by_bucket, scen, out / "exposure_report.png")

    print("\n== Exposição por faixa de vencimento ==\n", by_bucket.to_string())
    print("\n== P&L por cenário (BRL) ==\n", scen.to_string())
    print("\n== Limites ==\n", limits.to_string(index=False))
    print(f"\nArquivos gerados em {out}/")


if __name__ == "__main__":
    main()
