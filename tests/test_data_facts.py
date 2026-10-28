"""Data Analysis numbers are computed, not estimated by the model (live check 2026-10-22)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tom_core.data_facts import compute  # noqa: E402


def test_totals_peak_and_trend_are_exact(tmp_path):
    p = tmp_path / "sales.csv"
    p.write_text("month,region,sales\nJan,North,1200\nFeb,North,1350\nMar,North,1720\nApr,North,1610\n"
                 "Jan,South,900\nFeb,South,950\nMar,South,1100\nApr,South,1480\n")
    facts = compute(str(p))
    assert "Total sales by month: Jan 2,100.00; Feb 2,300.00; Mar 2,820.00; Apr 3,090.00. Highest: Apr" in facts
    assert "Overall from Jan to Apr: +990.00" in facts
    assert "region=North by month" in facts and "(highest Mar)" in facts


def test_excel_files_work_too(tmp_path):
    import pandas as pd
    p = tmp_path / "x.xlsx"
    pd.DataFrame({"team": ["A", "B", "A"], "points": [3, 5, 4]}).to_excel(p, index=False)
    assert "Total points by team: A 7.00; B 5.00. Highest: A" in compute(str(p))
