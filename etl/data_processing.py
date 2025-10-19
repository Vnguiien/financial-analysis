# etl/data_processing.py
import pandas as pd
import numpy as np
import sqlite3
from typing import Dict

# map tên cột phổ biến sang key chuẩn (giúp nếu cần map server-side)
COMMON_MAP = {
    "tổng tài sản": "total_assets", "total assets": "total_assets", "tong tai san": "total_assets",
    "tài sản ngắn hạn": "current_assets", "current assets": "current_assets", "tai san ngan han": "current_assets",
    "hàng tồn kho": "inventory", "inventory": "inventory", "hang ton kho": "inventory",
    "tiền": "cash_and_equivalents", "cash": "cash_and_equivalents", "cash equivalents": "cash_and_equivalents",
    "tổng nợ": "total_liabilities", "total liabilities": "total_liabilities", "tong no": "total_liabilities",
    "nợ ngắn hạn": "current_liabilities", "current liabilities": "current_liabilities", "no ngan han": "current_liabilities",
    "nợ dài hạn": "long_term_liabilities", "long-term liabilities": "long_term_liabilities", "no dai han": "long_term_liabilities",
    "vốn chủ sở hữu": "equity", "equity": "equity", "von chu so huu": "equity",
    "doanh thu": "revenue", "revenue": "revenue", "doanh thu thuần": "revenue",
    "ebit": "ebit", "lợi nhuận trước lãi và thuế": "ebit",
    "lợi nhuận sau thuế": "net_income", "net income": "net_income", "loi nhuan": "net_income",
    "phải thu": "accounts_receivable", "accounts receivable": "accounts_receivable", "phai thu": "accounts_receivable",
    "phải trả": "accounts_payable", "accounts payable": "accounts_payable", "phai tra": "accounts_payable",
    "dòng tiền từ hoạt động": "operating_cash_flow", "operating cash flow": "operating_cash_flow", "dong tien": "operating_cash_flow",
}

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa tên cột: loại khoảng trắng, chuyển sang chữ thường và map nếu có"""
    cols = []
    for c in df.columns:
        key = str(c).strip().lower()
        if key in COMMON_MAP:
            cols.append(COMMON_MAP[key])
        else:
            # giữ nguyên nếu không map được
            cols.append(key)
    df.columns = cols
    return df

def to_numeric_safe(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(',','').str.replace(' ',''),
                         errors='coerce')

def compute_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nhận dataframe (mỗi dòng là 1 kỳ/công ty). Trả về df có thêm các chỉ số:
    debt_to_equity, debt_to_revenue, current_ratio, quick_ratio, short_term_debt_ratio,
    receivables_turnover, payables_turnover, cash_flow_margin, equity_ratio, liabilities_ratio,
    roa, roe, altman_z_prime, altman_z_interpretation
    """
    df = df.copy()
    # normalize column names
    df = normalize_columns(df)

    # numeric conversion for known fields
    numeric_fields = [
        'total_assets','current_assets','inventory','cash_and_equivalents',
        'total_liabilities','current_liabilities','long_term_liabilities','equity','revenue','ebit','net_income',
        'accounts_receivable','accounts_payable','operating_cash_flow'
    ]
    for f in numeric_fields:
        if f in df.columns:
            df[f] = to_numeric_safe(df[f])
        else:
            df[f] = np.nan

    # compute ratios safely
    df['debt_to_equity'] = np.where(df['equity'] != 0, df['total_liabilities'] / df['equity'], np.nan)
    df['debt_to_revenue'] = np.where(df['revenue'] != 0, df['total_liabilities'] / df['revenue'], np.nan)
    df['current_ratio'] = np.where(df['current_liabilities'] != 0, df['current_assets'] / df['current_liabilities'], np.nan)
    df['quick_ratio'] = np.where(df['current_liabilities'] != 0, (df['current_assets'] - df['inventory']) / df['current_liabilities'], np.nan)
    df['short_term_debt_ratio'] = np.where(df['total_liabilities'] != 0, df['current_liabilities'] / df['total_liabilities'], np.nan)
    df['long_term_debt_ratio'] = np.where(df['total_liabilities'] != 0, df['long_term_liabilities'] / df['total_liabilities'], np.nan)
    df['receivables_turnover'] = np.where(df['accounts_receivable'] != 0, df['revenue'] / df['accounts_receivable'], np.nan)
    df['payables_turnover'] = np.where(df['accounts_payable'] != 0, df['revenue'] / df['accounts_payable'], np.nan)
    df['cash_flow_margin'] = np.where(df['revenue'] != 0, df['operating_cash_flow'] / df['revenue'], np.nan)
    df['equity_ratio'] = np.where(df['total_assets'] != 0, df['equity'] / df['total_assets'], np.nan)
    df['liabilities_ratio'] = np.where(df['total_assets'] != 0, df['total_liabilities'] / df['total_assets'], np.nan)
    df['roa'] = np.where(df['total_assets'] != 0, df['net_income'] / df['total_assets'], np.nan)
    df['roe'] = np.where(df['equity'] != 0, df['net_income'] / df['equity'], np.nan)

    # Detailed debt ratios vs equity and revenue
    df['short_term_debt_to_equity'] = np.where(df['equity'] != 0, df['current_liabilities'] / df['equity'], np.nan)
    df['short_term_debt_to_revenue'] = np.where(df['revenue'] != 0, df['current_liabilities'] / df['revenue'], np.nan)
    df['long_term_debt_to_equity'] = np.where(df['equity'] != 0, df['long_term_liabilities'] / df['equity'], np.nan)
    df['long_term_debt_to_revenue'] = np.where(df['revenue'] != 0, df['long_term_liabilities'] / df['revenue'], np.nan)

    # Altman Z' (suitable for private firms / non-manufacturing approx)
    A = np.where(df['total_assets'] != 0, (df['current_assets'] - df['current_liabilities']) / df['total_assets'], np.nan)
    B = np.where(df['total_assets'] != 0, df['net_income'] / df['total_assets'], np.nan)  # proxy retained earnings
    C = np.where(df['total_assets'] != 0, df['ebit'] / df['total_assets'], np.nan)
    D = np.where(df['total_liabilities'] != 0, df['equity'] / df['total_liabilities'], np.nan)
    E = np.where(df['total_assets'] != 0, df['revenue'] / df['total_assets'], np.nan)

    df['altman_z_prime'] = 0.717 * A + 0.847 * B + 3.107 * C + 0.420 * D + 0.998 * E

    def z_interpret(z):
        if pd.isna(z):
            return "Insufficient data"
        if z < 1.8:
            return "High risk of bankruptcy"
        if z < 2.99:
            return "Moderate risk"
        return "Low risk"

    df['altman_z_interpretation'] = df['altman_z_prime'].apply(z_interpret)

    return df

# === Period handling & aggregation utilities ===
def _parse_period_value(p: str) -> Dict[str, int | str]:
    """Parse common period formats into parts.
    Accepted examples: '2024-Q1', '2024Q1', '2024-03', '2024/03', '2024-3', '2024'
    Returns dict with keys: year, quarter (1..4 or NaN), month (1..12 or NaN), period_std (string)
    """
    if pd.isna(p):
        return {"year": np.nan, "quarter": np.nan, "month": np.nan, "period_std": None}
    s = str(p).strip().upper().replace(" ", "")
    year, quarter, month = np.nan, np.nan, np.nan
    period_std = None

    # YYYY-Qn or YYYYQn
    if "Q" in s:
        # normalize like 2024-Q1
        parts = s.replace("/", "-").replace("_", "-")
        # remove extra hyphens
        if "-Q" in parts:
            try:
                y = int(parts.split("-Q")[0])
                q = int(parts.split("-Q")[1])
                year, quarter = y, q
                period_std = f"{y}-Q{q}"
            except Exception:
                pass
        else:
            try:
                y, q = parts.split("Q")
                y = int(y)
                q = int(q)
                year, quarter = y, q
                period_std = f"{y}-Q{q}"
            except Exception:
                pass
    else:
        # try YYYY-MM or YYYY/M or YYYY-M
        for sep in ["-", "/", "."]:
            if sep in s:
                try:
                    y, m = s.split(sep)[0], s.split(sep)[1]
                    y = int(y)
                    m = int(m)
                    year, month = y, m
                    q = (m - 1) // 3 + 1
                    quarter = q
                    period_std = f"{y}-{m:02d}"
                    break
                except Exception:
                    pass
        # only year
        if period_std is None:
            try:
                y = int(s)
                year = y
                period_std = f"{y}"
            except Exception:
                pass

    return {"year": year, "quarter": quarter, "month": month, "period_std": period_std}


def add_period_parts(df: pd.DataFrame) -> pd.DataFrame:
    """Add columns year, quarter, month, period_std derived from 'period' column if present."""
    df = df.copy()
    if 'period' not in df.columns:
        return df
    parts = df['period'].apply(_parse_period_value)
    df['year'] = parts.apply(lambda x: x['year'])
    df['quarter'] = parts.apply(lambda x: x['quarter'])
    df['month'] = parts.apply(lambda x: x['month'])
    df['period_std'] = parts.apply(lambda x: x['period_std'])
    return df


def aggregate_by_period(df: pd.DataFrame, freq: str = 'Q', agg: str = 'mean') -> pd.DataFrame:
    """Aggregate computed ratios by quarter ('Q') or year ('Y').
    Default aggregation is mean; can be 'mean' or 'sum'.
    Requires columns produced by compute_ratios and add_period_parts.
    """
    if freq not in ('Q', 'Y'):
        raise ValueError("freq must be 'Q' or 'Y'")

    if 'year' not in df.columns:
        df = add_period_parts(df)

    group_cols = ['company'] if 'company' in df.columns else []
    if freq == 'Q':
        group_cols += ['year', 'quarter']
        df = df[df['quarter'].notna()]
    else:
        group_cols += ['year']
        df = df[df['year'].notna()]

    # choose numeric columns to aggregate
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    # keep only meaningful metrics
    prefer_cols = [
        'revenue','operating_cash_flow','total_assets','total_liabilities','equity',
        'current_assets','current_liabilities','long_term_liabilities','inventory',
        'debt_to_equity','debt_to_revenue','current_ratio','quick_ratio','short_term_debt_ratio','long_term_debt_ratio',
        'short_term_debt_to_equity','short_term_debt_to_revenue','long_term_debt_to_equity','long_term_debt_to_revenue',
        'receivables_turnover','payables_turnover','cash_flow_margin','equity_ratio','liabilities_ratio',
        'roa','roe','altman_z_prime'
    ]
    agg_cols = [c for c in prefer_cols if c in numeric_cols]

    if agg == 'sum':
        spec = {c: 'sum' for c in agg_cols}
    else:
        spec = {c: 'mean' for c in agg_cols}

    out = df.groupby(group_cols, dropna=False).agg(spec).reset_index()

    # stable ordering
    if 'quarter' in out.columns:
        out = out.sort_values(by=[c for c in ['company','year','quarter'] if c in out.columns])
    else:
        out = out.sort_values(by=[c for c in ['company','year'] if c in out.columns])
    return out


def compute_variation(df: pd.DataFrame, freq_cols: list[str]) -> pd.DataFrame:
    """Compute sequential and YoY changes for aggregated time series using groupby pct_change.
    Adds columns like metric_chg_1 and metric_chg_4 (for quarterly YoY).
    """
    df = df.copy()
    sort_cols = [c for c in ['company'] if c in df.columns] + freq_cols
    df = df.sort_values(by=sort_cols)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    for tcol in ['year','quarter','month']:
        if tcol in numeric_cols:
            numeric_cols.remove(tcol)

    by_cols = [c for c in ['company'] if c in df.columns]
    # compute change for periods=1
    for c in numeric_cols:
        if by_cols:
            df[f"{c}_chg_1"] = (
                df.sort_values(sort_cols)
                  .groupby(by_cols, dropna=False)[c]
                  .pct_change(periods=1, fill_method=None)
            )
        else:
            df[f"{c}_chg_1"] = df[c].pct_change(periods=1, fill_method=None)

    # compute 4-period change for quarterly series
    if 'quarter' in freq_cols:
        for c in numeric_cols:
            if by_cols:
                df[f"{c}_chg_4"] = (
                    df.sort_values(sort_cols)
                      .groupby(by_cols, dropna=False)[c]
                      .pct_change(periods=4, fill_method=None)
                )
            else:
                df[f"{c}_chg_4"] = df[c].pct_change(periods=4, fill_method=None)

    return df

# Persistence
def save_to_sqlite(df: pd.DataFrame, db_path: str = "financial_data.db", table: str = "ratios"):
    conn = sqlite3.connect(db_path)
    # ensure columns 'company' and 'period' exist for timeseries
    df.to_sql(table, conn, if_exists='append', index=False)
    conn.close()

def query_sql(sql: str, db_path: str = "financial_data.db") -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df
