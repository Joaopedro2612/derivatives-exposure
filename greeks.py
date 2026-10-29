"""Precificação e gregas de opções europeias de câmbio (modelo Garman-Kohlhagen).

Convenções:
  spot, strike : BRL por 1 USD
  t            : prazo em anos (dias corridos / 365)
  r_dom, r_for : taxas contínuas (doméstica = BRL, estrangeira = USD)
  vol          : volatilidade anualizada (0.15 = 15%)
"""
from __future__ import annotations

import math

import numpy as np

_erf = np.vectorize(math.erf)


def norm_cdf(x):
    return 0.5 * (1.0 + _erf(np.asarray(x, dtype=float) / math.sqrt(2.0)))


def norm_pdf(x):
    x = np.asarray(x, dtype=float)
    return np.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)


def _d1_d2(spot, strike, t, r_dom, r_for, vol):
    vol_sqrt_t = np.asarray(vol, dtype=float) * np.sqrt(np.asarray(t, dtype=float))
    d1 = (np.log(spot / strike) + (r_dom - r_for + 0.5 * np.asarray(vol, dtype=float) ** 2) * t) / vol_sqrt_t
    return d1, d1 - vol_sqrt_t


def price(kind, spot, strike, t, r_dom, r_for, vol):
    """Prêmio (BRL por USD de principal). `kind` é 'call' ou 'put' (escalar ou array)."""
    d1, d2 = _d1_d2(spot, strike, t, r_dom, r_for, vol)
    df_dom, df_for = np.exp(-r_dom * np.asarray(t, dtype=float)), np.exp(-r_for * np.asarray(t, dtype=float))
    call = spot * df_for * norm_cdf(d1) - strike * df_dom * norm_cdf(d2)
    put = strike * df_dom * norm_cdf(-d2) - spot * df_for * norm_cdf(-d1)
    return np.where(np.asarray(kind) == "call", call, put)


def greeks(kind, spot, strike, t, r_dom, r_for, vol):
    """Retorna (delta, gamma, vega) por unidade de principal.

    delta : variação do prêmio por variação unitária do spot (adimensional)
    gamma : variação do delta por variação unitária do spot
    vega  : variação do prêmio por variação de 1,00 (100 pontos) na vol
    """
    d1, _ = _d1_d2(spot, strike, t, r_dom, r_for, vol)
    t = np.asarray(t, dtype=float)
    df_for = np.exp(-r_for * t)
    is_call = np.asarray(kind) == "call"
    delta = np.where(is_call, df_for * norm_cdf(d1), -df_for * norm_cdf(-d1))
    gamma = df_for * norm_pdf(d1) / (spot * np.asarray(vol, dtype=float) * np.sqrt(t))
    vega = spot * df_for * norm_pdf(d1) * np.sqrt(t)
    return delta, gamma, vega
