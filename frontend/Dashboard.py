import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from rapidfuzz import process
import numpy as np
from streamlit_option_menu import option_menu

# =========================
# 🎨 PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Phân Tích Tài Chính Doanh Nghiệp",
    page_icon="💹",
    layout="wide",
)

# =========================
# 🌈 CSS TÙY CHỈNH
# =========================
st.markdown("""
<style>
:root{
  --pri:#7c3aed; /* violet */
  --pri2:#06b6d4; /* cyan */
  --bg1:#0b1220; --bg2:#111827; --txt:#f8fafc; --muted:#cbd5e1;
}
body{background: radial-gradient(1200px 400px at -10% -20%, rgba(124,58,237,.25), transparent),
                      radial-gradient(1200px 400px at 110% -20%, rgba(6,182,212,.2), transparent),
                      linear-gradient(120deg, var(--bg1), var(--bg2));
     color:var(--txt); font-family: 'Segoe UI', system-ui, sans-serif;}
h1,h2,h3{color:var(--txt); text-shadow:0 0 12px rgba(0,0,0,.25)}
.stButton>button{background:linear-gradient(90deg, var(--pri), var(--pri2)); color:#fff; border:0; border-radius:12px; padding:.65rem 1.1rem; font-weight:700; box-shadow:0 10px 24px rgba(124,58,237,.35); transition:.2s}
.stButton>button:hover{filter:brightness(.95); transform:translateY(-1px)}
.stDataFrame div[data-testid="stTable"]{border-radius:12px; overflow:hidden; box-shadow:0 8px 22px rgba(0,0,0,.25)}
div[data-testid="stMetric"]{background:rgba(255,255,255,.06); padding:12px; border-radius:12px; box-shadow:0 8px 22px rgba(0,0,0,.25)}
/* option menu */
.nav-container{background:rgba(17,25,40,.7); border:1px solid rgba(148,163,184,.15); border-radius:14px; padding:6px 10px; box-shadow:0 10px 24px rgba(0,0,0,.25)}
</style>
""", unsafe_allow_html=True)

# =========================
# 🌟 HEADER
# =========================
st.markdown("""
<div style='padding:18px; text-align:center; background:linear-gradient(135deg, rgba(124,58,237,.18), rgba(6,182,212,.18)); border:1px solid rgba(148,163,184,.18); border-radius:16px; box-shadow:0 14px 28px rgba(0,0,0,.35);'>
  <h1>💹 HỆ THỐNG PHÂN TÍCH TÀI CHÍNH DOANH NGHIỆP</h1>
  <p style='color:#e2e8f0; font-size:16px; margin:.4rem 0 0'>Tải dữ liệu, tính chỉ số, đánh giá rủi ro, theo dõi xu hướng và xuất báo cáo chuyên nghiệp</p>
</div>
""", unsafe_allow_html=True)

# =========================
# 🧭 THANH MENU CHÍNH
# =========================
selected = option_menu(
    menu_title=None,
    options=["🏠 Tổng quan", "📊 Chỉ số & Mapping", "📈 Xu hướng", "⚠️ Rủi ro & Z-Score", "📉 Biểu đồ", "📤 Báo cáo"],
    icons=["house", "bar-chart", "graph-up", "exclamation-triangle", "pie-chart", "cloud-upload"],
    orientation="horizontal",
    styles={
        "container": {"padding": "6px 0", "background-color": "rgba(0,0,0,0)"},
        "nav": {"background-color": "rgba(17,25,40,.65)", "border-radius":"14px", "padding":"6px 10px", "border":"1px solid rgba(148,163,184,.18)"},
        "icon": {"color": "#a78bfa", "font-size": "21px"},
        "nav-link": {"font-size": "15px", "color": "#e2e8f0", "padding": "8px 14px", "margin":"0 2px"},
        "nav-link-selected": {"background-color": "#7c3aed", "border-radius": "10px"},
    }
)

# =========================
# 📁 FILE UPLOAD
# =========================
st.markdown("### 📂 Tải lên báo cáo tài chính (.CSV hoặc .XLSX)")
uploaded = st.file_uploader(
    "Chọn file báo cáo tài chính",
    type=["csv","xlsx"],
    label_visibility="collapsed"
)
API_BASE = "http://127.0.0.1:8000/api"

# =========================
# 🔍 SMART COLUMN MATCH
# =========================
def smart_match_column(df, expected_cols, threshold=70):
    mapping = {}
    cols = list(df.columns)
    for exp in expected_cols:
        match = process.extractOne(exp, cols)
        if match and match[1] >= threshold:
            mapping[match[0]] = exp
    return mapping

def clean_df_for_json(df: pd.DataFrame) -> pd.DataFrame:
    tmp = df.copy()
    for c in tmp.columns:
        if tmp[c].dtype == object:
            try:
                tmp[c] = pd.to_numeric(tmp[c].astype(str).str.replace(',', '').str.replace(' ', ''), errors='ignore')
            except Exception:
                pass
    tmp = tmp.replace([np.inf, -np.inf], np.nan)
    tmp = tmp.astype(object).where(pd.notna(tmp), None)
    return tmp

# Tìm cột theo danh sách tên thay thế (không phân biệt hoa thường)
def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    # exact first
    for c in candidates:
        if c in df.columns:
            return c
    # case-insensitive
    lower_map = {str(c).strip().lower(): c for c in df.columns}
    for c in candidates:
        key = c.strip().lower()
        if key in lower_map:
            return lower_map[key]
    return None

# =========================
# 📦 MAIN CONTENT
# =========================
if uploaded:
    try:
        df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        st.success(f"✅ Đã tải lên: {uploaded.name}")
        st.dataframe(df.head())

        expected = ["company","period","Doanh thu","Tổng nợ","Vốn chủ sở hữu","Lợi nhuận sau thuế",
                    "Tài sản ngắn hạn","EBIT","Phải thu","Phải trả","Dòng tiền từ hoạt động"]
        mapping = smart_match_column(df, expected, threshold=60)

        with st.expander("🔠 Tên cột được hệ thống tự động phát hiện"):
            for k,v in mapping.items():
                st.write(f"- `{k}` → gợi ý: `{v}`")

        # ----------------------------
        # 🏠 TỔNG QUAN
        # ----------------------------
        if selected == "🏠 Tổng quan":
            st.header("🏠 Tổng quan dữ liệu")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Số dòng", len(df))
            k2.metric("Số cột", len(df.columns))
            k3.metric("Có 'company'", "Có" if "company" in df.columns else "Không")
            k4.metric("Có 'period'", "Có" if "period" in df.columns else "Không")

            st.caption("Mẹo: Nên có cột company và period (YYYY-Qn hoặc YYYY-MM) để phân tích xu hướng và lưu lịch sử")

            if st.button("💾 Lưu & Tính toán (SQLite)"):
                try:
                    res = requests.post(f"{API_BASE}/store_and_compute", json=clean_df_for_json(df).to_dict(orient="records"))
                    if res.status_code == 200:
                        st.success("✅ Dữ liệu đã được lưu và xử lý thành công.")
                    else:
                        st.error(f"Lỗi lưu: {res.text}")
                except Exception as e:
                    st.error(f"Lỗi kết nối: {e}")

        # ----------------------------
        # 📊 CHỈ SỐ
        # ----------------------------
        elif selected == "📊 Chỉ số & Mapping":
            st.header("📊 Phân tích chỉ số tài chính")
            if st.button("🚀 Tính toán chỉ số"):
                try:
                    res = requests.post(f"{API_BASE}/analyze", json=clean_df_for_json(df).to_dict(orient="records"))
                    if res.status_code == 200:
                        result = res.json()
                        summary = result.get("summary", {})
                        c1,c2,c3 = st.columns(3)
                        c1.metric("Tỷ lệ Nợ/VCSH", summary.get("Tỷ lệ nợ/Vốn chủ sở hữu (bình quân)"))
                        c2.metric("Tỷ suất LN/DT", summary.get("Tỷ suất lợi nhuận/Doanh thu (bình quân)"))
                        c3.metric("Thanh toán NH", summary.get("Khả năng thanh toán ngắn hạn (bình quân)"))
                        if result.get("risk_analysis"):
                            with st.expander("⚠️ Nhận định rủi ro"):
                                for r in result["risk_analysis"]:
                                    st.write("- ", r)
                    else:
                        st.error(f"Lỗi API: {res.text}")
                except Exception as e:
                    st.error(e)

        # ----------------------------
        # 📈 XU HƯỚNG
        # ----------------------------
        elif selected == "📈 Xu hướng":
            st.header("📈 Xu hướng theo thời gian")
            c1,c2 = st.columns([2,1])
            with c1:
                metrics = ["revenue","total_liabilities","equity","current_ratio","altman_z_prime"]
                chosen = st.multiselect("Chọn chỉ tiêu", metrics, default=["revenue","total_liabilities","equity"]) 
            with c2:
                freq = st.selectbox("Tần suất", ["Q","Y"], index=0)
            if st.button("📊 Xem xu hướng"):
                try:
                    res = requests.post(f"{API_BASE}/trends", json=clean_df_for_json(df).to_dict(orient="records"), params={"freq": freq})
                    if res.status_code == 200:
                        data = pd.DataFrame(res.json().get("series", []))
                        if not data.empty:
                            # tạo nhãn thời gian
                            if "quarter" in data.columns:
                                data["__label"] = data[["year","quarter"]].astype(str).agg(" Q".join, axis=1)
                            elif "year" in data.columns:
                                data["__label"] = data["year"].astype(int).astype(str)
                            else:
                                data["__label"] = range(len(data))
                            plot_df = data.set_index("__label")
                            available = [c for c in chosen if c in plot_df.columns]
                            st.line_chart(plot_df[available])
                            with st.expander("Dữ liệu tổng hợp"):
                                st.dataframe(data)
                        else:
                            st.info("Không có dữ liệu phù hợp.")
                    else:
                        st.error("Không lấy được dữ liệu xu hướng")
                except Exception as e:
                    st.error(e)

        # ----------------------------
        # ⚠️ RỦI RO
        # ----------------------------
        elif selected == "⚠️ Rủi ro & Z-Score":
            st.header("⚠️ Phân tích rủi ro doanh nghiệp")
            if st.button("🧮 Tính Z-Score"):
                try:
                    res = requests.post(f"{API_BASE}/zscore_and_recommend", json=clean_df_for_json(df).to_dict(orient="records"))
                    if res.status_code == 200:
                        out = res.json().get("results", [])
                        if out:
                            st.dataframe(pd.DataFrame(out))
                        for r in out:
                            rec = r.get("recommendation","")
                            if "Approve" in rec:
                                st.success(rec)
                            elif "Consider" in rec:
                                st.warning(rec)
                            else:
                                st.error(rec)
                    else:
                        st.error("API lỗi.")
                except Exception as e:
                    st.error(e)

        # ----------------------------
        # 📉 BIỂU ĐỒ
        # ----------------------------
        elif selected == "📉 Biểu đồ":
            st.header("📉 Biểu đồ tài chính")
            fig, ax = plt.subplots()
            plotted = False
            col_revenue = find_column(df, ["Doanh thu","revenue","doanh thu"]) 
            col_debt = find_column(df, ["Tổng nợ","total liabilities","total_liabilities","tong no"]) 
            col_equity = find_column(df, ["Vốn chủ sở hữu","equity","von chu so huu"]) 
            if col_revenue:
                ax.plot(pd.to_numeric(df[col_revenue], errors='coerce'), label="Doanh thu", color="#3b82f6"); plotted = True
            if col_debt:
                ax.plot(pd.to_numeric(df[col_debt], errors='coerce'), label="Tổng nợ", color="#ef4444"); plotted = True
            if col_equity:
                ax.plot(pd.to_numeric(df[col_equity], errors='coerce'), label="Vốn chủ sở hữu", color="#10b981"); plotted = True
            ax.set_title("Cơ cấu tài chính")
            if plotted:
                ax.legend()
                st.pyplot(fig)
            else:
                st.info("Không có cột phù hợp để vẽ biểu đồ (cần 'Doanh thu'/'Tổng nợ'/'Vốn chủ sở hữu').")
            st.caption("Mẹo: Hãy chuẩn hoá các cột theo mẫu để biểu đồ chính xác hơn.")

        # ----------------------------
        # 📤 BÁO CÁO
        # ----------------------------
        elif selected == "📤 Báo cáo":
            st.header("📤 Xuất báo cáo và dữ liệu")
            c1,c2 = st.columns(2)
            with c1:
                if st.button("📄 Xuất PDF"):
                    try:
                        res = requests.post(f"{API_BASE}/report", json=clean_df_for_json(df).to_dict(orient="records"))
                        st.success(f"Report: {res.json().get('message')}")
                    except Exception as e:
                        st.error(e)
            with c2:
                if st.button("💾 Xuất CSV"):
                    try:
                        res = requests.post(f"{API_BASE}/export_csv", json=clean_df_for_json(df).to_dict(orient="records"))
                        payload = res.json()
                        csv = pd.DataFrame(payload["rows"], columns=payload["columns"]).to_csv(index=False).encode('utf-8')
                        st.download_button("Tải file CSV", csv, "ratios_export.csv", "text/csv")
                    except Exception as e:
                        st.error(e)

    except Exception as e:
        st.error(f"Lỗi đọc file: {e}")

else:
    st.info("📤 Hãy tải lên file báo cáo tài chính để bắt đầu.")
