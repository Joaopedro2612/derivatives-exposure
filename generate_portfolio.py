"""Gera uma carteira FICTÍCIA de opções USD/BRL para demonstração (reprodutível via seed)."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def generate(n=40, spot=5.50, seed=42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    side = rng.choice([-1, 1], size=n)
    notional = np.round(rng.uniform(100_000, 2_000_000, size=n), -4)
    return pd.DataFrame(
        {
            "trade_id": [f"OPT{i + 1:03d}" for i in range(n)],
            "kind": rng.choice(["call", "put"], size=n),
            "strike": np.round(spot * rng.uniform(0.92, 1.08, size=n), 2),
            "days_to_maturity": rng.integers(10, 361, size=n),
            "vol": np.round(rng.uniform(0.10, 0.20, size=n), 3),
            "quantity_usd": side * notional,  # positivo = comprado, negativo = vendido
        }
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default="data/sample_portfolio.csv")
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    generate(a.n, seed=a.seed).to_csv(a.out, index=False)
    print(f"Carteira fictícia salva em {a.out}")
