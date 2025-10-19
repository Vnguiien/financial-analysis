# app.py (FastAPI)
from fastapi import FastAPI, HTTPException, Body, Response
from pydantic import RootModel
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import sqlite3
import os

# import ETL utilities
from etl.data_processing import compute_ratios, save_to_sqlite, query_sql, add_period_parts, aggregate_by_period, compute_variation

app = FastAPI(title="Financial Analysis API", version="4.0")

DB_PATH = "financial_data.db"
TABLE_NAME = "ratios"

class FinancialRecord(RootModel[Dict[str, Any]]):
    pass

@app.get("/")
def root():
    return {"thong_bao": "API Phân tích Tài chính đang chạy", "huong_dan": "Dùng /api/analyze, /api/trends, /api/zscore_and_recommend, /api/export_csv_stored, /api/demo_excel"}

# Helper to convert DataFrame to JSON-safe records
def df_to_json_records_safe(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to JSON-safe python objects (no NaN/Inf)."""
    def to_safe_scalar(x):
        # Handle pandas/NumPy scalars
        try:
            if x is None:
                return None
            if isinstance(x, (float, int)):
                if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
                    return None
                if isinstance(x, (float, int)) and not np.isfinite(x):
                    return None
                return x
            # strings and others
            if pd.isna(x):
                return None
            return x
        except Exception:
            return None

    df = df.replace({np.inf: None, -np.inf: None})
    df = df.astype(object).where(pd.notna(df), None)
    records = []
    for rec in df.to_dict(orient='records'):
        clean = {k: to_safe_scalar(v) for k, v in rec.items()}
        records.append(clean)
    return records

# Basic analyze (returns mapping + summary + risk), expects list of dict records
@app.post("/api/analyze")
def analyze(records: List[FinancialRecord] = Body(...)):
    if not records:
        raise HTTPException(status_code=400, detail="No data provided")
    try:
        rows = [r.root for r in records]
        df = pd.DataFrame(rows)
        df.columns = df.columns.str.strip()
        df_ratios = compute_ratios(df)
        # helper to make JSON-safe numbers
        def safe_num(val):
            try:
                if val is None:
                    return None
                # normalize numpy numbers to python float
                if isinstance(val, (np.floating, np.integer)):
                    val = float(val)
                if pd.isna(val):
                    return None
                if isinstance(val, (float, int)) and not np.isfinite(val):
                    return None
                return round(float(val), 2)
            except Exception:
                return None
        # create summary averages (JSON-safe)
        dte = safe_num(df_ratios['debt_to_equity'].mean(skipna=True))
        ln_dt = None
        if 'Tỷ suất LN/DT' in df_ratios.columns:
            ln_dt = safe_num(df_ratios['Tỷ suất LN/DT'].mean(skipna=True))
        else:
            ln_dt = safe_num(df_ratios['roa'].mean(skipna=True))
        cr = safe_num(df_ratios['current_ratio'].mean(skipna=True))
        summary = {
            "Tỷ lệ nợ/Vốn chủ sở hữu (bình quân)": dte,
            "Tỷ suất lợi nhuận/Doanh thu (bình quân)": ln_dt,
            "Khả năng thanh toán ngắn hạn (bình quân)": cr
        }
        # mapping: return the input->normalized cols (approx)
        mapping = {c: c for c in df.columns}
        # risk summary from altman interpretation (majority)
        risk_counts = df_ratios['altman_z_interpretation'].value_counts(dropna=True).to_dict()
        most_common_risk = max(risk_counts, key=risk_counts.get) if risk_counts else "Insufficient data"
        risk_analysis = [f"Altman Z summary: {most_common_risk}"]

        return {
            "status": "success",
            "mapping": mapping,
            "summary": summary,
            "risk_analysis": risk_analysis,
            "records_analyzed": len(df_ratios)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Store & compute: store processed ratios into SQLite for historical analysis
@app.post("/api/store_and_compute")
def store_and_compute(records: List[FinancialRecord] = Body(...)):
    if not records:
        raise HTTPException(status_code=400, detail="No data")
    try:
        rows = [r.root for r in records]
        df = pd.DataFrame(rows)
        df.columns = df.columns.str.strip()
        # require company & period
        if 'company' not in df.columns or 'period' not in df.columns:
            raise HTTPException(status_code=400, detail="Missing required columns: 'company' and 'period' (format YYYY-Qn or YYYY-MM)")

        df_ratios = compute_ratios(df)
        # ensure period parts are stored for SQL-based analysis later
        df_ratios = add_period_parts(df_ratios)
        save_to_sqlite(df_ratios, db_path=DB_PATH, table=TABLE_NAME)
        return {"status": "success", "stored_rows": len(df_ratios)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Trends & variations by quarter/year
@app.post("/api/trends")
def trends(records: List[FinancialRecord] = Body(...), freq: str = 'Q', agg: str = 'mean'):
    """
    Trả về chuỗi chỉ số theo quý ('Q') hoặc năm ('Y') và biến động tuần tự (QoQ/YoY).
    """
    if not records:
        raise HTTPException(status_code=400, detail="No data")
    if freq not in ('Q','Y'):
        raise HTTPException(status_code=400, detail="freq must be 'Q' or 'Y'")
    try:
        rows = [r.root for r in records]
        df = pd.DataFrame(rows)
        df.columns = df.columns.str.strip()
        # require 'period' to compute quarterly/yearly trends
        if 'period' not in df.columns:
            raise HTTPException(status_code=400, detail="Thiếu cột 'period' (ví dụ 2024-Q1 hoặc 2024-03)")
        df_ratios = compute_ratios(df)
        df_ratios = add_period_parts(df_ratios)
        series = aggregate_by_period(df_ratios, freq=freq, agg=agg)
        freq_cols = ['year','quarter'] if freq == 'Q' else ['year']
        series_var = compute_variation(series, freq_cols=freq_cols)
        return {
            "freq": freq,
            "agg": agg,
            "series": df_to_json_records_safe(series),
            "series_with_change": df_to_json_records_safe(series_var)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Export stored data as CSV for Power BI "From Web"
@app.get("/api/export_csv_stored")
def export_csv_stored(company: str | None = None, start_period: str | None = None, end_period: str | None = None):
    try:
        conn = sqlite3.connect(DB_PATH)
        base_cols = [
            'company','period','year','quarter','month',
            'revenue','operating_cash_flow','total_assets','total_liabilities','equity',
            'current_assets','current_liabilities','long_term_liabilities','inventory',
            'debt_to_equity','debt_to_revenue','current_ratio','quick_ratio','short_term_debt_ratio','long_term_debt_ratio',
            'short_term_debt_to_equity','short_term_debt_to_revenue','long_term_debt_to_equity','long_term_debt_to_revenue',
            'receivables_turnover','payables_turnover','cash_flow_margin','equity_ratio','liabilities_ratio',
            'roa','roe','altman_z_prime','altman_z_interpretation'
        ]
        cols_sql = ",".join(base_cols)
        sql = f"SELECT {cols_sql} FROM {TABLE_NAME} WHERE 1=1"
        params: list = []
        if company:
            sql += " AND company = ?"; params.append(company)
        if start_period:
            sql += " AND period >= ?"; params.append(start_period)
        if end_period:
            sql += " AND period <= ?"; params.append(end_period)
        sql += " ORDER BY company, period"
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        return Response(content=csv_bytes, media_type="text/csv")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Generate demo Excel file for users to download
@app.get("/api/demo_excel")
def generate_demo_excel():
    try:
        # Build small demo DataFrame similar to sample_data/financial_demo.csv
        data = [
            {"company":"ABC","period":"2023-Q1","Doanh thu":1200000,"Tổng tài sản":5000000,"Tài sản ngắn hạn":2000000,
             "Hàng tồn kho":300000,"Tiền":500000,"Tổng nợ":3000000,"Nợ ngắn hạn":1200000,"Nợ dài hạn":1800000,
             "Vốn chủ sở hữu":2000000,"EBIT":250000,"Lợi nhuận sau thuế":180000,"Phải thu":350000,"Phải trả":220000,
             "Dòng tiền từ hoạt động":210000},
            {"company":"ABC","period":"2023-Q2","Doanh thu":1300000,"Tổng tài sản":5200000,"Tài sản ngắn hạn":2100000,
             "Hàng tồn kho":320000,"Tiền":520000,"Tổng nợ":3050000,"Nợ ngắn hạn":1250000,"Nợ dài hạn":1800000,
             "Vốn chủ sở hữu":2150000,"EBIT":270000,"Lợi nhuận sau thuế":190000,"Phải thu":360000,"Phải trả":230000,
             "Dòng tiền từ hoạt động":230000},
            {"company":"XYZ","period":"2023-Q1","Doanh thu":900000,"Tổng tài sản":4000000,"Tài sản ngắn hạn":1600000,
             "Hàng tồn kho":250000,"Tiền":400000,"Tổng nợ":2200000,"Nợ ngắn hạn":900000,"Nợ dài hạn":1300000,
             "Vốn chủ sở hữu":1800000,"EBIT":180000,"Lợi nhuận sau thuế":120000,"Phải thu":280000,"Phải trả":180000,
             "Dòng tiền từ hoạt động":150000},
            {"company":"XYZ","period":"2023-Q2","Doanh thu":950000,"Tổng tài sản":4100000,"Tài sản ngắn hạn":1650000,
             "Hàng tồn kho":260000,"Tiền":410000,"Tổng nợ":2250000,"Nợ ngắn hạn":920000,"Nợ dài hạn":1330000,
             "Vốn chủ sở hữu":1850000,"EBIT":190000,"Lợi nhuận sau thuế":130000,"Phải thu":285000,"Phải trả":185000,
             "Dòng tiền từ hoạt động":170000}
        ]
        df = pd.DataFrame(data)
        path = os.path.join("sample_data","financial_demo.xlsx")
        os.makedirs("sample_data", exist_ok=True)
        df.to_excel(path, index=False)
        with open(path, 'rb') as f:
            content = f.read()
        return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition":"attachment; filename=financial_demo.xlsx"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# SQL analysis endpoint for quarterly/yearly variation using SQLite (data must be stored previously)
@app.get("/api/sql_variation")
def sql_variation(company: str, level: str = 'Q'):
    """Dùng SQL để phân tích biến động các chỉ số theo quý/năm từ SQLite (đã lưu)."""
    if level not in ('Q','Y'):
        raise HTTPException(status_code=400, detail="level must be 'Q' or 'Y'")
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # Ensure the ratios table has needed columns (assumed from compute_ratios + add_period_parts stored earlier)
        # Quarterly variation: percent change vs previous quarter for selected metrics
        if level == 'Q':
            sql = f"""
            WITH base AS (
              SELECT company, period, year, quarter,
                     revenue, total_liabilities, equity, current_ratio, quick_ratio,
                     receivables_turnover, payables_turnover, altman_z_prime
              FROM {TABLE_NAME}
              WHERE company = ? AND quarter IS NOT NULL
            ), seq AS (
              SELECT *,
                     LAG(revenue) OVER (PARTITION BY company ORDER BY year, quarter) AS rev_prev,
                     LAG(total_liabilities) OVER (PARTITION BY company ORDER BY year, quarter) AS debt_prev,
                     LAG(equity) OVER (PARTITION BY company ORDER BY year, quarter) AS equity_prev,
                     LAG(current_ratio) OVER (PARTITION BY company ORDER BY year, quarter) AS cr_prev,
                     LAG(quick_ratio) OVER (PARTITION BY company ORDER BY year, quarter) AS qr_prev
              FROM base
            )
            SELECT company, year, quarter,
                   revenue,
                   CASE WHEN rev_prev IS NOT NULL AND rev_prev != 0 THEN (revenue - rev_prev)/rev_prev ELSE NULL END AS revenue_qoq,
                   total_liabilities,
                   CASE WHEN debt_prev IS NOT NULL AND debt_prev != 0 THEN (total_liabilities - debt_prev)/debt_prev ELSE NULL END AS debt_qoq,
                   equity,
                   CASE WHEN equity_prev IS NOT NULL AND equity_prev != 0 THEN (equity - equity_prev)/equity_prev ELSE NULL END AS equity_qoq,
                   current_ratio,
                   CASE WHEN cr_prev IS NOT NULL AND cr_prev != 0 THEN (current_ratio - cr_prev)/cr_prev ELSE NULL END AS current_ratio_qoq,
                   quick_ratio,
                   CASE WHEN qr_prev IS NOT NULL AND qr_prev != 0 THEN (quick_ratio - qr_prev)/qr_prev ELSE NULL END AS quick_ratio_qoq,
                   receivables_turnover, payables_turnover, altman_z_prime
            FROM seq
            ORDER BY year, quarter
            """
            rows = pd.read_sql_query(sql, conn, params=[company]).to_dict(orient='records')
        else:
            sql = f"""
            WITH base AS (
              SELECT company, period, year,
                     revenue, total_liabilities, equity, current_ratio, quick_ratio,
                     receivables_turnover, payables_turnover, altman_z_prime
              FROM {TABLE_NAME}
              WHERE company = ? AND year IS NOT NULL
            ), seq AS (
              SELECT *,
                     LAG(revenue) OVER (PARTITION BY company ORDER BY year) AS rev_prev,
                     LAG(total_liabilities) OVER (PARTITION BY company ORDER BY year) AS debt_prev,
                     LAG(equity) OVER (PARTITION BY company ORDER BY year) AS equity_prev
              FROM base
            )
            SELECT company, year,
                   revenue,
                   CASE WHEN rev_prev IS NOT NULL AND rev_prev != 0 THEN (revenue - rev_prev)/rev_prev ELSE NULL END AS revenue_yoy,
                   total_liabilities,
                   CASE WHEN debt_prev IS NOT NULL AND debt_prev != 0 THEN (total_liabilities - debt_prev)/debt_prev ELSE NULL END AS debt_yoy,
                   equity,
                   CASE WHEN equity_prev IS NOT NULL AND equity_prev != 0 THEN (equity - equity_prev)/equity_prev ELSE NULL END AS equity_yoy,
                   current_ratio, quick_ratio, receivables_turnover, payables_turnover, altman_z_prime
            FROM seq
            ORDER BY year
            """
            rows = pd.read_sql_query(sql, conn, params=[company]).to_dict(orient='records')
        conn.close()
        return {"company": company, "level": level, "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Export CSV for Power BI ingestion
@app.post("/api/export_csv")
def export_csv(records: List[FinancialRecord] = Body(...)):
    """Trả về dữ liệu ratios sau chuẩn hoá để nạp vào Power BI (CSV-like JSON)."""
    if not records:
        raise HTTPException(status_code=400, detail="No data")
    try:
        rows = [r.root for r in records]
        df = pd.DataFrame(rows)
        df.columns = df.columns.str.strip()
        df_ratios = compute_ratios(df)
        df_ratios = add_period_parts(df_ratios)
        # chọn cột quan trọng cho Power BI
        cols = [c for c in [
            'company','period','year','quarter','month',
            'revenue','operating_cash_flow','total_assets','total_liabilities','equity',
            'current_assets','current_liabilities','long_term_liabilities','inventory',
            'debt_to_equity','debt_to_revenue','current_ratio','quick_ratio','short_term_debt_ratio','long_term_debt_ratio',
            'short_term_debt_to_equity','short_term_debt_to_revenue','long_term_debt_to_equity','long_term_debt_to_revenue',
            'receivables_turnover','payables_turnover','cash_flow_margin','equity_ratio','liabilities_ratio',
            'roa','roe','altman_z_prime','altman_z_interpretation'
        ] if c in df_ratios.columns]
        safe_df = df_ratios[cols]
        data = df_to_json_records_safe(safe_df)
        return {"columns": cols, "rows": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Query series
@app.get("/api/series")
def get_series(company: str, start_period: str = None, end_period: str = None):
    try:
        conn = sqlite3.connect(DB_PATH)
        sql = f"SELECT * FROM {TABLE_NAME} WHERE company = ?"
        params = [company]
        if start_period:
            sql += " AND period >= ?"; params.append(start_period)
        if end_period:
            sql += " AND period <= ?"; params.append(end_period)
        sql += " ORDER BY period"
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return {"company": company, "rows": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Z-score + Recommendation
@app.post("/api/zscore_and_recommend")
def zscore_and_recommend(records: List[FinancialRecord] = Body(...)):
    if not records:
        raise HTTPException(status_code=400, detail="No data")
    try:
        rows = [r.root for r in records]
        df = pd.DataFrame(rows)
        df.columns = df.columns.str.strip()
        df_ratios = compute_ratios(df)

        out = []
        for _, row in df_ratios.iterrows():
            z = row.get('altman_z_prime', None)
            interp = row.get('altman_z_interpretation', 'Insufficient data')
            rec = "Decline"
            # simple rules (example)
            if pd.notna(z) and np.isfinite(z):
                cr = row.get('current_ratio', 0)
                dte = row.get('debt_to_equity', 999)
                cr = float(cr) if pd.notna(cr) and np.isfinite(cr) else 0.0
                dte = float(dte) if pd.notna(dte) and np.isfinite(dte) else 999.0
                if z > 2.99 and cr >= 1.2 and dte < 2:
                    rec = "Approve with standard collateral"
                elif 1.8 < z <= 2.99 and cr >= 1.0:
                    rec = "Consider with additional guarantees & monitoring"
                else:
                    rec = "Decline or require strong collateral"
            out.append({
                "company": row.get('company'),
                "period": row.get('period'),
                "altman_z": float(z) if pd.notna(z) and np.isfinite(z) else None,
                "z_interpretation": interp,
                "debt_to_equity": float(row.get('debt_to_equity')) if pd.notna(row.get('debt_to_equity')) and np.isfinite(row.get('debt_to_equity')) else None,
                "current_ratio": float(row.get('current_ratio')) if pd.notna(row.get('current_ratio')) and np.isfinite(row.get('current_ratio')) else None,
                "recommendation": rec
            })
        return {"results": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Report PDF (simple summary) - reuse compute_ratios
@app.post("/api/report")
def generate_report(records: List[FinancialRecord] = Body(...)):
    if not records:
        raise HTTPException(status_code=400, detail="No data")
    try:
        rows = [r.root for r in records]
        df = pd.DataFrame(rows)
        df.columns = df.columns.str.strip()
        df_ratios = compute_ratios(df)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []
        elements.append(Paragraph("Báo cáo phân tích tài chính", styles["Title"]))
        elements.append(Spacer(1, 12))

        # table
        data = [df_ratios.columns.tolist()] + df_ratios.fillna("").values.tolist()
        table = Table(data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightblue),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey)
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

        # summary
        summary = [
            ["Chỉ số", "Giá trị trung bình"],
            ["Tỷ lệ nợ/VCSH", round(df_ratios['debt_to_equity'].mean(skipna=True),2)],
            ["Tỷ suất LN/DT (proxy)", round(df_ratios['roa'].mean(skipna=True),2)],
            ["Khả năng thanh toán ngắn hạn", round(df_ratios['current_ratio'].mean(skipna=True),2)]
        ]
        s_table = Table(summary)
        s_table.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.5,colors.grey)]))
        elements.append(s_table)

        doc.build(elements)
        buffer.seek(0)
        size_kb = round(len(buffer.getvalue())/1024,2)
        return {"message": "Report generated", "size_kb": size_kb}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
