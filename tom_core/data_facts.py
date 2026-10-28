"""Exact facts about a CSV/Excel file, computed — not estimated by a language model.

Live check 2026-10-22: asked "which month had the highest total sales, and what is the trend?", the model
named April correctly and then claimed sales "peak in March and decline in April". Small models do
arithmetic badly, so the numbers are computed here and the model only explains them.
"""
from __future__ import annotations

from typing import List


def compute(path: str, max_groups: int = 24) -> str:
    import pandas as pd
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, sep=None, engine="python")
    df.columns = [str(c).strip() for c in df.columns]
    lines: List[str] = [f"Rows: {len(df)}. Columns: {', '.join(df.columns)}."]
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat = [c for c in df.columns if c not in num and 1 < df[c].nunique() <= max_groups]
    for c in num[:6]:
        s = df[c].dropna()
        if len(s):
            lines.append(f"{c}: total {s.sum():,.2f}, average {s.mean():,.2f}, min {s.min():,.2f}, max {s.max():,.2f}.")
    for g in cat[:2]:
        order = list(dict.fromkeys(df[g].dropna().tolist()))            # keep the file's order (Jan, Feb, ...)
        for c in num[:3]:
            totals = df.groupby(g, sort=False)[c].sum().reindex(order)
            top, low = totals.idxmax(), totals.idxmin()
            lines.append(f"Total {c} by {g}: " + "; ".join(f"{k} {v:,.2f}" for k, v in totals.items())
                         + f". Highest: {top} ({totals[top]:,.2f}). Lowest: {low} ({totals[low]:,.2f}).")
            if len(totals) >= 3:
                changes = [(order[i], totals.iloc[i] - totals.iloc[i - 1]) for i in range(1, len(order))]
                lines.append(f"Change in total {c} from one {g} to the next: "
                             + "; ".join(f"{k} {d:+,.2f}" for k, d in changes)
                             + f". Overall from {order[0]} to {order[-1]}: {totals.iloc[-1] - totals.iloc[0]:+,.2f}.")
        if len(cat) >= 2 and g == cat[0] and num:
            other = cat[1]
            pivot = df.pivot_table(index=g, columns=other, values=num[0], aggfunc="sum").reindex(order)
            for col in pivot.columns[:6]:
                series = pivot[col].dropna()
                if len(series) >= 2:
                    lines.append(f"{num[0]} for {other}={col} by {g}: " +
                                 "; ".join(f"{k} {v:,.2f}" for k, v in series.items()) +
                                 f" (highest {series.idxmax()}).")
    return "\n".join(lines)
