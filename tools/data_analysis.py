"""
TOM Data Analysis Suite — automated insight generation with BI-style HTML reports.
(Honest scope: produces matplotlib charts + an HTML dashboard, NOT Power BI .pbix files.)
Full pipeline: auto-clean, auto-visualize, statistical analysis, insights, reporting.
"""
import io
import json
import os
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from tools.project_paths import PROJECT_ROOT, project_path_str

try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False

try:
    import seaborn as sns
    _HAS_SNS = True
except ImportError:
    _HAS_SNS = False

try:
    from scipy import stats as scipy_stats
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


class DataAnalysisEngine:
    """
    Enterprise-grade data analysis engine.
    Handles CSV, Excel, JSON, SQL, Parquet, and more.
    Generates insights that rival (and beat) Power BI.
    """

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".parquet", ".feather", ".tsv", ".txt"}

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or project_path_str("output", "analysis")
        os.makedirs(self.output_dir, exist_ok=True)
        self._last_results: Dict[str, Any] = {}

    def load_data(self, filepath: str) -> Optional[pd.DataFrame]:
        """Load data from any supported file format."""
        if not _HAS_PANDAS:
            raise ImportError("pandas is required for data analysis. pip install pandas")

        ext = Path(filepath).suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {ext}. Supported: {self.SUPPORTED_EXTENSIONS}")

        loaders = {
            ".csv": lambda: pd.read_csv(filepath),
            ".tsv": lambda: pd.read_csv(filepath, sep="\t"),
            ".txt": lambda: pd.read_csv(filepath, sep=None, engine="python"),
            ".xlsx": lambda: pd.read_excel(filepath, engine="openpyxl"),
            ".xls": lambda: pd.read_excel(filepath, engine="xlrd"),
            ".json": lambda: pd.read_json(filepath),
            ".parquet": lambda: pd.read_parquet(filepath),
            ".feather": lambda: pd.read_feather(filepath),
        }
        df = loaders[ext]()
        self._last_results["loaded"] = df
        return df

    def load_data_from_text(self, text: str, format: str = "csv") -> pd.DataFrame:
        """Load data from a text string (e.g., clipboard content)."""
        if format == "csv":
            return pd.read_csv(io.StringIO(text))
        elif format == "json":
            return pd.read_json(io.StringIO(text))
        elif format == "tsv":
            return pd.read_csv(io.StringIO(text), sep="\t")
        raise ValueError(f"Unsupported text format: {format}")

    def auto_clean(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Automatically clean a dataframe.
        Returns (cleaned_df, cleaning_report).
        """
        report = {"operations": [], "warnings": []}
        df = df.copy()

        # Remove empty rows/cols
        before = df.shape
        df = df.dropna(how="all")
        df = df.dropna(axis=1, how="all")
        if df.shape != before:
            report["operations"].append(f"Removed empty rows/cols: {before} -> {df.shape}")

        # Detect and remove duplicates
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            df = df.drop_duplicates()
            report["operations"].append(f"Removed {dup_count} duplicate rows")

        # Handle missing values
        null_counts = df.isnull().sum()
        null_cols = null_counts[null_counts > 0]
        for col in null_cols.index:
            pct = null_counts[col] / len(df) * 100
            if pct > 50:
                report["warnings"].append(f"{col}: {pct:.1f}% missing — consider dropping")
            elif df[col].dtype in (np.number,):
                # pandas 3.x: chained inplace fill is a silent no-op — assign instead.
                df[col] = df[col].fillna(df[col].median())
                report["operations"].append(f"{col}: filled {null_counts[col]} NaN with median")
            else:
                df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else "Unknown")
                report["operations"].append(f"{col}: filled {null_counts[col]} NaN with mode")

        # Detect and cap outliers (IQR method for numeric columns)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        outlier_info = {}
        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            outliers = ((df[col] < lower) | (df[col] > upper)).sum()
            if outliers > 0:
                outlier_info[col] = int(outliers)
                df[col] = df[col].clip(lower, upper)
        if outlier_info:
            report["operations"].append(f"Capped outliers: {outlier_info}")

        # Standardize column names
        old_cols = list(df.columns)
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        renamed = [(o, n) for o, n in zip(old_cols, df.columns) if o != n]
        if renamed:
            report["operations"].append(f"Standardized {len(renamed)} column names")

        self._last_results["cleaning"] = report
        return df, report

    def auto_visualize(self, df: pd.DataFrame, prefix: str = "analysis") -> List[str]:
        """
        Auto-generate visualizations for a dataframe.
        Returns list of saved image file paths.
        """
        if not _HAS_MPL:
            raise ImportError("matplotlib required for visualization. pip install matplotlib")

        files = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns[:8]
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns[:6]
        ts_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]

        sns_style = "darkgrid" if _HAS_SNS else "default"

        # 1. Distribution plots for numeric columns
        if len(numeric_cols) > 0:
            n_cols = min(4, len(numeric_cols))
            n_rows = (len(numeric_cols) + n_cols - 1) // n_cols
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
            axes = axes.flatten() if n_rows * n_cols > 1 else [axes]
            for i, col in enumerate(numeric_cols[:8]):
                if _HAS_SNS:
                    sns.histplot(df[col].dropna(), kde=True, ax=axes[i], color="#3b82f6")
                else:
                    axes[i].hist(df[col].dropna(), bins=30, color="#3b82f6", alpha=0.7, edgecolor="white")
                axes[i].set_title(f"{col} Distribution", color="white", fontsize=10)
                axes[i].tick_params(colors="gray")
                axes[i].set_facecolor("#0f1624")
                axes[i].spines["bottom"].set_color("#1e2d45")
                axes[i].spines["top"].set_color("#1e2d45")
                axes[i].spines["left"].set_color("#1e2d45")
                axes[i].spines["right"].set_color("#1e2d45")
            for j in range(len(numeric_cols[:8]), len(axes)):
                axes[j].set_visible(False)
            fig.patch.set_facecolor("#080c14")
            fig.tight_layout()
            path = os.path.join(self.output_dir, f"{prefix}_distributions.png")
            fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig)
            files.append(path)

        # 2. Correlation heatmap
        if len(numeric_cols) > 1:
            fig, ax = plt.subplots(figsize=(min(10, len(numeric_cols) * 1.2),
                                             min(8, len(numeric_cols) * 1.0)))
            corr = df[numeric_cols].corr()
            if _HAS_SNS:
                sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r",
                            center=0, ax=ax, cbar_kws={"shrink": 0.8})
            else:
                im = ax.imshow(corr, cmap="RdBu_r", aspect="auto")
                plt.colorbar(im, ax=ax)
            ax.set_title("Correlation Matrix", color="white", fontsize=12)
            ax.tick_params(colors="gray")
            fig.patch.set_facecolor("#080c14")
            fig.tight_layout()
            path = os.path.join(self.output_dir, f"{prefix}_correlation.png")
            fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig)
            files.append(path)

        # 3. Categorical bar charts
        for col in categorical_cols[:3]:
            fig, ax = plt.subplots(figsize=(8, 4))
            counts = df[col].value_counts().head(15)
            colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(counts)))
            counts.plot(kind="barh", color=colors, ax=ax)
            ax.set_title(f"Top {col} Values", color="white", fontsize=10)
            ax.tick_params(colors="gray")
            ax.set_facecolor("#0f1624")
            for spine in ax.spines.values():
                spine.set_color("#1e2d45")
            fig.patch.set_facecolor("#080c14")
            fig.tight_layout()
            path = os.path.join(self.output_dir, f"{prefix}_{col}_top.png")
            fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig)
            files.append(path)

        # 4. Time series if date column found
        if ts_cols and len(numeric_cols) > 0:
            date_col = ts_cols[0]
            try:
                ts = pd.to_datetime(df[date_col])
                fig, ax = plt.subplots(figsize=(10, 4))
                for nc in numeric_cols[:3]:
                    ax.plot(ts, df[nc], label=nc, alpha=0.8)
                ax.set_title(f"Trends over {date_col}", color="white", fontsize=10)
                ax.legend()
                ax.tick_params(colors="gray")
                ax.set_facecolor("#0f1624")
                for spine in ax.spines.values():
                    spine.set_color("#1e2d45")
                fig.patch.set_facecolor("#080c14")
                fig.tight_layout()
                path = os.path.join(self.output_dir, f"{prefix}_timeseries.png")
                fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
                plt.close(fig)
                files.append(path)
            except Exception:
                pass

        self._last_results["visualizations"] = files
        return files

    def generate_insights(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate comprehensive insights from the data.
        Returns structured dict with statistics, correlations, anomalies, and recommendations.
        """
        insights = {
            "overview": {},
            "statistics": {},
            "correlations": [],
            "anomalies": [],
            "trends": [],
            "recommendations": [],
        }

        # Overview
        insights["overview"] = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB",
            "missing_cells": int(df.isnull().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum()),
        }

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns

        # Statistics for numeric columns
        for col in numeric_cols:
            stats = {
                "mean": round(df[col].mean(), 2),
                "median": round(df[col].median(), 2),
                "std": round(df[col].std(), 2),
                "min": round(df[col].min(), 2),
                "max": round(df[col].max(), 2),
                "q1": round(df[col].quantile(0.25), 2),
                "q3": round(df[col].quantile(0.75), 2),
                "skewness": round(df[col].skew(), 3) if _HAS_SCIPY else "N/A",
                "kurtosis": round(df[col].kurtosis(), 3) if _HAS_SCIPY else "N/A",
            }
            # Normality test
            if _HAS_SCIPY and len(df[col].dropna()) > 3:
                _, p_val = scipy_stats.normaltest(df[col].dropna())
                stats["normality_p_value"] = round(p_val, 4)
                stats["is_normal"] = p_val > 0.05
            insights["statistics"][col] = stats

        # Correlation analysis
        if len(numeric_cols) > 1:
            corr = df[numeric_cols].corr()
            for i in range(len(corr.columns)):
                for j in range(i + 1, len(corr.columns)):
                    val = corr.iloc[i, j]
                    if abs(val) > 0.5:
                        insights["correlations"].append({
                            "col1": corr.columns[i],
                            "col2": corr.columns[j],
                            "correlation": round(val, 3),
                            "strength": "strong" if abs(val) > 0.7 else "moderate",
                            "direction": "positive" if val > 0 else "negative",
                        })

        # Anomaly detection (z-score)
        for col in numeric_cols:
            mean = df[col].mean()
            std = df[col].std()
            if std > 0:
                z_scores = (df[col] - mean) / std
                anomalies = df[z_scores.abs() > 3]
                if len(anomalies) > 0:
                    insights["anomalies"].append({
                        "column": col,
                        "count": len(anomalies),
                        "threshold": "z-score > 3",
                        "example_values": anomalies[col].head(3).tolist(),
                    })

        # Categorical value distribution
        for col in categorical_cols[:5]:
            top = df[col].value_counts().head(5)
            if len(top) > 1:
                insights["trends"].append({
                    "column": col,
                    "unique_values": int(df[col].nunique()),
                    "top_values": {str(k): int(v) for k, v in top.items()},
                })

        # Auto-recommendations
        if insights["overview"]["missing_cells"] > 0:
            insights["recommendations"].append(
                "Data has missing values — consider imputation or row removal"
            )
        if insights["overview"]["duplicate_rows"] > 0:
            insights["recommendations"].append(
                f"Found {insights['overview']['duplicate_rows']} duplicate rows — consider removing"
            )
        for corr_item in insights["correlations"]:
            if abs(corr_item["correlation"]) > 0.8:
                insights["recommendations"].append(
                    f"Strong {corr_item['direction']} correlation between "
                    f"'{corr_item['col1']}' and '{corr_item['col2']}' "
                    f"({corr_item['correlation']:.2f}) — investigate causality"
                )
        if insights["anomalies"]:
            total_anom = sum(a["count"] for a in insights["anomalies"])
            insights["recommendations"].append(
                f"Detected {total_anom} outlier(s) across {len(insights['anomalies'])} column(s)"
            )

        self._last_results["insights"] = insights
        return insights

    def generate_report(self, df: pd.DataFrame, title: str = "Data Analysis Report") -> str:
        """
        Generate a comprehensive HTML report with visualizations.
        Returns path to the generated HTML file.
        """
        insights = self.generate_insights(df)
        viz_files = self.auto_visualize(df)

        overview = insights["overview"]
        stats = insights["statistics"]
        corrs = insights["correlations"]
        anomalies = insights["anomalies"]
        trends = insights["trends"]
        recommendations = insights["recommendations"]

        # Build HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ background:#080c14; color:#e2e8f0; font-family:'Segoe UI',sans-serif; padding:40px; max-width:1200px; margin:auto; }}
  h1 {{ color:#3b82f6; border-bottom:2px solid #1e2d45; padding-bottom:12px; }}
  h2 {{ color:#06b6d4; margin-top:36px; }}
  h3 {{ color:#8b5cf6; }}
  .card {{ background:#0f1624; border:1px solid #1e2d45; border-radius:8px; padding:20px; margin:16px 0; }}
  .stat-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:12px; }}
  .stat-item {{ background:#161f30; padding:12px; border-radius:6px; }}
  .stat-label {{ color:#94a3b8; font-size:12px; }}
  .stat-value {{ color:#e2e8f0; font-size:18px; font-weight:bold; }}
  .corr-item {{ padding:8px; margin:4px 0; border-left:3px solid #3b82f6; }}
  .anomaly-item {{ padding:8px; margin:4px 0; border-left:3px solid #ef4444; }}
  .recommendation {{ padding:10px; margin:6px 0; border-left:3px solid #f59e0b; background:#1a1a2e; }}
  img {{ max-width:100%; border-radius:8px; margin:12px 0; border:1px solid #1e2d45; }}
  table {{ width:100%; border-collapse:collapse; margin:12px 0; }}
  th, td {{ padding:8px 12px; text-align:left; border-bottom:1px solid #1e2d45; }}
  th {{ color:#3b82f6; }}
  td {{ color:#94a3b8; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold; }}
  .badge-green {{ background:#065f46; color:#10b981; }}
  .badge-red {{ background:#7f1d1d; color:#ef4444; }}
  .badge-yellow {{ background:#78350f; color:#f59e0b; }}
</style></head>
<body>
<h1>{title}</h1>
<div class="card">
  <h3>Dataset Overview</h3>
  <div class="stat-grid">
    <div class="stat-item"><div class="stat-label">Rows</div><div class="stat-value">{overview['rows']:,}</div></div>
    <div class="stat-item"><div class="stat-label">Columns</div><div class="stat-value">{overview['columns']}</div></div>
    <div class="stat-item"><div class="stat-label">Memory</div><div class="stat-value">{overview['memory_usage']}</div></div>
    <div class="stat-item"><div class="stat-label">Missing Cells</div><div class="stat-value">{overview['missing_cells']:,}</div></div>
    <div class="stat-item"><div class="stat-label">Duplicates</div><div class="stat-value">{overview['duplicate_rows']:,}</div></div>
  </div>
</div>
"""
        if viz_files:
            html += "<h2>Visualizations</h2>"
            for vf in viz_files:
                rel = os.path.relpath(vf, str(PROJECT_ROOT))
                html += f'<img src="{rel}" alt="Visualization">\n'

        if stats:
            html += "<h2>Statistical Summary</h2><div class='card'>"
            html += """<table><tr><th>Column</th><th>Mean</th><th>Median</th><th>Std</th><th>Min</th><th>Max</th><th>Q1</th><th>Q3</th></tr>"""
            for col, s in stats.items():
                html += f"<tr><td>{col}</td><td>{s['mean']}</td><td>{s['median']}</td><td>{s['std']}</td><td>{s['min']}</td><td>{s['max']}</td><td>{s['q1']}</td><td>{s['q3']}</td></tr>"
            html += "</table></div>"

        if corrs:
            html += "<h2>Key Correlations</h2><div class='card'>"
            for c in corrs:
                cls = "badge-green" if c['direction'] == 'positive' else "badge-red"
                html += f'<div class="corr-item"><span class="badge {cls}">{c["strength"]} {c["direction"]}</span> <strong>{c["col1"]}</strong> vs <strong>{c["col2"]}</strong>: {c["correlation"]:.2f}</div>'
            html += "</div>"

        if anomalies:
            html += "<h2>Anomalies Detected</h2><div class='card'>"
            for a in anomalies:
                html += f'<div class="anomaly-item"><strong>{a["column"]}</strong>: {a["count"]} outliers (z > 3). Examples: {a["example_values"]}</div>'
            html += "</div>"

        if trends:
            html += "<h2>Trends & Patterns</h2><div class='card'>"
            for t in trends:
                html += f"<h3>{t['column']}</h3><p>{t['unique_values']} unique values. "
                html += "Top: " + ", ".join(f"{k}: {v}" for k, v in t['top_values'].items()) + "</p>"
            html += "</div>"

        if recommendations:
            html += "<h2>Recommendations</h2><div class='card'>"
            for r in recommendations:
                html += f'<div class="recommendation">{r}</div>'
            html += "</div>"

        # Sample data
        html += "<h2>Sample Data (first 10 rows)</h2><div class='card'>"
        html += df.head(10).to_html(classes="table", index=False)
        html += "</div>"
        html += f"<p style='color:#475569;font-size:12px;margin-top:40px'>Generated by TOM Data Analysis Engine at {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</p>"
        html += "</body></html>"

        path = os.path.join(self.output_dir, f"{title.replace(' ', '_').lower()[:40]}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

        self._last_results["report_path"] = path
        return path

    def compare_datasets(self, df1: pd.DataFrame, df2: pd.DataFrame,
                         key_column: str = None) -> Dict[str, Any]:
        """Compare two dataframes and return differences."""
        result = {
            "shape_diff": (df1.shape, df2.shape),
            "column_diff": {
                "only_in_first": list(set(df1.columns) - set(df2.columns)),
                "only_in_second": list(set(df2.columns) - set(df1.columns)),
                "common": list(set(df1.columns) & set(df2.columns)),
            },
        }
        common_cols = result["column_diff"]["common"]
        if common_cols:
            row_diff = []
            merged = df1.merge(df2, on=common_cols[:min(3, len(common_cols))],
                               how="outer", indicator=True)
            counts = merged["_merge"].value_counts().to_dict()
            result["row_comparison"] = {
                "both": int(counts.get("both", 0)),
                "only_in_first": int(counts.get("left_only", 0)),
                "only_in_second": int(counts.get("right_only", 0)),
            }
        # Value differences in common columns
        val_diffs = {}
        for col in common_cols[:5]:
            if df1[col].dtype == df2[col].dtype:
                try:
                    diff_count = (df1[col] != df2[col]).sum()
                    if diff_count > 0:
                        val_diffs[col] = int(diff_count)
                except Exception:
                    pass
        if val_diffs:
            result["value_differences"] = val_diffs

        self._last_results["comparison"] = result
        return result

    def time_series_analysis(self, df: pd.DataFrame, date_col: str,
                             value_col: str = None) -> Dict[str, Any]:
        """Analyze time series data for trends, seasonality, and forecasting."""
        result = {"error": None}

        try:
            ts = pd.to_datetime(df[date_col])
            df = df.copy()
            df["_date"] = ts

            if not value_col:
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                numeric_cols = [c for c in numeric_cols if c != date_col]
                if numeric_cols:
                    value_col = numeric_cols[0]
                else:
                    result["error"] = "No numeric column found for time series analysis"
                    return result

            # Resample by month
            ts_df = df.set_index("_date")[[value_col]].sort_index()
            monthly = ts_df.resample("ME").mean()

            result["summary"] = {
                "date_range": f"{ts.min().date()} to {ts.max().date()}",
                "total_periods": len(monthly),
                "overall_mean": round(monthly[value_col].mean(), 2),
                "overall_median": round(monthly[value_col].median(), 2),
                "overall_std": round(monthly[value_col].std(), 2),
            }

            # Trend direction
            if len(monthly) > 2:
                x = np.arange(len(monthly))
                y = monthly[value_col].values
                slope, intercept, r_val, p_val, std_err = scipy_stats.linregress(x, y)
                result["trend"] = {
                    "direction": "upward" if slope > 0 else "downward",
                    "slope": round(slope, 4),
                    "r_squared": round(r_val ** 2, 4),
                    "p_value": round(p_val, 4),
                    "significant": p_val < 0.05,
                }

            # Seasonality (simple monthly pattern)
            monthly["month"] = monthly.index.month
            seasonal = monthly.groupby("month")[value_col].mean()
            peak_month = seasonal.idxmax()
            trough_month = seasonal.idxmin()
            result["seasonality"] = {
                "peak_month": int(peak_month),
                "trough_month": int(trough_month),
                "monthly_avg": {int(m): round(v, 2) for m, v in seasonal.items()},
                "amplitude": round(seasonal.max() - seasonal.min(), 2),
            }

            # Generate visualization
            if _HAS_MPL:
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
                ax1.plot(monthly.index, monthly[value_col], color="#3b82f6", linewidth=2)
                ax1.fill_between(monthly.index, monthly[value_col], alpha=0.1, color="#3b82f6")
                ax1.set_title(f"{value_col} over Time", color="white")
                ax1.tick_params(colors="gray")
                ax1.set_facecolor("#0f1624")
                for spine in ax1.spines.values():
                    spine.set_color("#1e2d45")

                months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
                ax2.bar([months[m-1] for m in seasonal.index], seasonal.values,
                        color="#06b6d4", alpha=0.7)
                ax2.set_title("Monthly Seasonality", color="white")
                ax2.tick_params(colors="gray")
                ax2.set_facecolor("#0f1624")
                for spine in ax2.spines.values():
                    spine.set_color("#1e2d45")
                fig.patch.set_facecolor("#080c14")
                fig.tight_layout()
                path = os.path.join(self.output_dir, "timeseries_analysis.png")
                fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
                plt.close(fig)
                result["chart_path"] = path

        except Exception as e:
            result["error"] = str(e)

        self._last_results["timeseries"] = result
        return result

    def forecast(self, df: pd.DataFrame, date_col: str, value_col: str,
                 periods: int = 12) -> Dict[str, Any]:
        """
        Simple forecasting using linear regression / moving average.
        For production, replace with Prophet, ARIMA, or LSTM.
        """
        result = {}
        try:
            ts = pd.to_datetime(df[date_col])
            ts_df = pd.DataFrame({"_date": ts, "value": df[value_col]}).set_index("_date").sort_index()
            monthly = ts_df.resample("ME").mean().dropna()

            x = np.arange(len(monthly))
            y = monthly["value"].values
            slope, intercept, _, _, _ = scipy_stats.linregress(x, y)

            forecast_x = np.arange(len(monthly), len(monthly) + periods)
            forecast_y = slope * forecast_x + intercept

            last_date = monthly.index[-1]
            forecast_dates = pd.date_range(start=last_date + pd.DateOffset(months=1),
                                            periods=periods, freq="ME")

            result["forecast"] = [
                {"date": d.strftime("%Y-%m-%d"), "predicted": round(float(v), 2)}
                for d, v in zip(forecast_dates, forecast_y)
            ]
            result["model"] = "linear_regression"
            result["confidence"] = "low"  # upgrade to Prophet for production

            if _HAS_MPL:
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(monthly.index, monthly["value"], color="#3b82f6", label="Historical")
                ax.plot(forecast_dates, forecast_y, color="#f59e0b", linestyle="--", label="Forecast")
                ax.fill_between(forecast_dates,
                                forecast_y - monthly["value"].std(),
                                forecast_y + monthly["value"].std(),
                                alpha=0.1, color="#f59e0b")
                ax.set_title(f"{value_col} Forecast ({periods} months)", color="white")
                ax.legend()
                ax.tick_params(colors="gray")
                ax.set_facecolor("#0f1624")
                for spine in ax.spines.values():
                    spine.set_color("#1e2d45")
                fig.patch.set_facecolor("#080c14")
                fig.tight_layout()
                path = os.path.join(self.output_dir, "forecast.png")
                fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
                plt.close(fig)
                result["chart_path"] = path

        except Exception as e:
            result["error"] = str(e)

        self._last_results["forecast"] = result
        return result

    def get_last_results(self) -> Dict[str, Any]:
        return self._last_results
