"""generate_report() must never crash and every chart it embeds must actually load.

Two real bugs, found by physically generating a report:
  1. auto_visualize() classified datetime64 columns as "categorical" and tried to bar-chart
     value_counts() of raw timestamps, which pandas/matplotlib reject with
     "Must supply freq for datetime value" -- crashing the whole report for any DataFrame
     with a real (non-string) date column, a completely ordinary case.
  2. generate_report() wrote <img src> as a path relative to the project root instead of
     the report's own directory (where every chart is actually saved as a sibling file),
     so no chart image ever resolved in a browser, in any report TOM ever generated.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

pytest.importorskip("numpy")
pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

import numpy as np
import pandas as pd

from tools.data_analysis import DataAnalysisEngine


def _sample_df():
    rng = np.random.RandomState(1)
    n = 60
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n, freq="D"),
        "sales": (rng.rand(n) * 1000).round(2),
        "region": rng.choice(["North", "South", "East", "West"], n),
        "units": rng.randint(1, 50, n),
    })


def test_report_does_not_crash_on_a_real_datetime64_column(tmp_path):
    df = _sample_df()
    engine = DataAnalysisEngine(output_dir=str(tmp_path))
    cleaned, _ = engine.auto_clean(df)
    report_path = engine.generate_report(cleaned, title="Sales Report")
    assert os.path.isfile(report_path)


def test_every_chart_image_src_resolves_next_to_the_report(tmp_path):
    df = _sample_df()
    engine = DataAnalysisEngine(output_dir=str(tmp_path))
    cleaned, _ = engine.auto_clean(df)
    report_path = engine.generate_report(cleaned, title="Sales Report")

    html = open(report_path, encoding="utf-8").read()
    srcs = re.findall(r'<img src="([^"]+)"', html)
    assert srcs, "expected at least one chart in the report"
    report_dir = os.path.dirname(report_path)
    for src in srcs:
        assert os.path.isfile(os.path.join(report_dir, src)), f"broken image src: {src}"


def test_a_string_date_column_still_gets_its_own_top_values_chart(tmp_path):
    # When dates arrive as plain strings (e.g. after a CSV round-trip without
    # parse_dates), they are still fine to show as a categorical bar chart.
    df = _sample_df()
    df["date"] = df["date"].astype(str)
    engine = DataAnalysisEngine(output_dir=str(tmp_path))
    files = engine.auto_visualize(df)
    assert any("date" in os.path.basename(f) for f in files)
