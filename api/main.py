from fastapi import APIRouter, HTTPException
import pandas as pd

router = APIRouter()

@router.post("/analyze")
def analyze_financial_data(data: list[dict]):
    """
    Nhận dữ liệu báo cáo tài chính (list of dict)
    và trả về kết quả phân tích cơ bản.
    """
    try:
        df = pd.DataFrame(data)

        # ✅ Kiểm tra cột cần thiết
        required_cols = ["Tổng tài sản", "Nợ phải trả", "Doanh thu", "Lợi nhuận sau thuế"]
        for col in required_cols:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Thiếu cột dữ liệu bắt buộc: {col}")

        # ✅ Phân tích tài chính
        df["Hệ số nợ"] = df["Nợ phải trả"] / df["Tổng tài sản"]
        df["Tỷ suất lợi nhuận"] = df["Lợi nhuận sau thuế"] / df["Doanh thu"]

        avg_debt_ratio = df["Hệ số nợ"].mean()
        avg_profit_ratio = df["Tỷ suất lợi nhuận"].mean()

        # ✅ Đánh giá rủi ro
        if avg_debt_ratio > 0.6:
            risk = "⚠️ Rủi ro cao (Tỷ lệ nợ cao so với tài sản)"
        elif avg_debt_ratio > 0.4:
            risk = "🟡 Mức rủi ro trung bình"
        else:
            risk = "🟢 Rủi ro thấp"

        # ✅ Đánh giá hiệu quả
        if avg_profit_ratio < 0.05:
            efficiency = "🔴 Hiệu quả thấp"
        elif avg_profit_ratio < 0.15:
            efficiency = "🟡 Hiệu quả trung bình"
        else:
            efficiency = "🟢 Hiệu quả cao"

        return {
            "Tổng số bản ghi": len(df),
            "Tỷ lệ nợ trung bình": round(avg_debt_ratio, 2),
            "Tỷ suất lợi nhuận trung bình": round(avg_profit_ratio, 2),
            "Đánh giá rủi ro": risk,
            "Đánh giá hiệu quả": efficiency,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
