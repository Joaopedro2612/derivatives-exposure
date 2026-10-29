import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import greeks  # noqa: E402

S, K, T, RD, RF, VOL = 5.50, 5.60, 0.5, 0.14, 0.04, 0.15


class TestGreeks(unittest.TestCase):
    def test_put_call_parity(self):
        c = greeks.price("call", S, K, T, RD, RF, VOL)
        p = greeks.price("put", S, K, T, RD, RF, VOL)
        self.assertAlmostEqual(float(c - p), S * np.exp(-RF * T) - K * np.exp(-RD * T), places=10)

    def test_delta_call_minus_put(self):
        dc, _, _ = greeks.greeks("call", S, K, T, RD, RF, VOL)
        dp, _, _ = greeks.greeks("put", S, K, T, RD, RF, VOL)
        self.assertAlmostEqual(float(dc - dp), np.exp(-RF * T), places=10)

    def test_gamma_and_vega_positive(self):
        _, g, v = greeks.greeks("call", S, K, T, RD, RF, VOL)
        self.assertGreater(float(g), 0)
        self.assertGreater(float(v), 0)

    def test_delta_matches_finite_difference(self):
        h = 1e-5
        up = greeks.price("call", S + h, K, T, RD, RF, VOL)
        dn = greeks.price("call", S - h, K, T, RD, RF, VOL)
        d, _, _ = greeks.greeks("call", S, K, T, RD, RF, VOL)
        self.assertAlmostEqual(float((up - dn) / (2 * h)), float(d), places=6)


if __name__ == "__main__":
    unittest.main()
