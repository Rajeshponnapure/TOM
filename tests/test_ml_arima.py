"""ARIMA must use statsmodels when it is available (it used to fall back silently)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import types

import pytest

pytest.importorskip("numpy")
pytest.importorskip("pandas")

from tools import ml_engine


def _fake_statsmodels(monkeypatch, calls):
    class Fitted:
        aic, bic, mse = 1.5, 2.5, 0.1

        def forecast(self, steps):
            import numpy as np
            return np.arange(steps, dtype=float)

    class ARIMA:
        def __init__(self, data, order=None, seasonal_order=None):
            calls.append({"order": order, "seasonal_order": seasonal_order})

        def fit(self):
            return Fitted()

    for name in ("statsmodels", "statsmodels.tsa", "statsmodels.tsa.arima"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    model_mod = types.ModuleType("statsmodels.tsa.arima.model")
    model_mod.ARIMA = ARIMA
    monkeypatch.setitem(sys.modules, "statsmodels.tsa.arima.model", model_mod)
    monkeypatch.setattr(ml_engine, "_HAS_STATS", True)


@pytest.mark.parametrize("algorithm", ["arima", "sarima"])
def test_statsmodels_is_used_when_installed(monkeypatch, algorithm):
    calls = []
    _fake_statsmodels(monkeypatch, calls)
    data = [float(i % 7) + i * 0.1 for i in range(40)]
    result = ml_engine.MLEngine().time_series(algorithm, data, forecast_steps=3)
    assert result["status"] == "success", result
    assert "(statsmodels)" in result["message"]
    assert result["forecast"] == [0.0, 1.0, 2.0]
    assert len(calls) == 1


def test_scratch_implementation_still_works_without_statsmodels(monkeypatch):
    monkeypatch.setattr(ml_engine, "_HAS_STATS", False)
    data = [float(i % 7) + i * 0.1 for i in range(40)]
    result = ml_engine.MLEngine().time_series("arima", data, forecast_steps=3)
    assert result["status"] == "success" and "statsmodels" not in result["message"]
