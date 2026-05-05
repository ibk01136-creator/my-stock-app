import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="주식 변동성 전략 도우미", layout="wide")

# 1. 설정 및 계산 함수
STOCKS = {"SK하이닉스": "000660.KS", "삼성전자": "005930.KS"}
STD_LIST = [2.0, 1.6, 1.0]

def get_clean_data(ticker, period, interval):
    data = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
    if data.empty: return None
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data

def calculate_all(data, std_list, type_name):
    tp = (data['High'] + data['Low'] + data['Close']) / 3
    ma20 = tp.rolling(window=20).mean()
    std = tp.rolling(window=20).std()
    
    res = {}
    curr_ma = float(ma20.iloc[-1])
    prev_ma = float(ma20.iloc[-2])
    
    res[f"{type_name} 중심선"] = curr_ma
    pred_label = "내일" if "일봉" in type_name else "다음주"
    res[f"{pred_label} 중심예측"] = float(curr_ma + (curr_ma - prev_ma))
    
    for s in std_list:
        upper = float(ma20.iloc[-1] + (std.iloc[-1] * s))
        lower = float(ma20.iloc[-1] - (std.iloc[-1] * s))
        prev_upper = float(ma20.iloc[-2] + (std.iloc[-2] * s))
        prev_lower = float(ma20.iloc[-2] - (std.iloc[-2] * s))
        
        res[f"{type_name} {s} 상단"] = upper
        res[f"{type_name} {s} 하단"] = lower
        res[f"{pred_label} {s} 상단예측"] = float(upper + (upper - prev_upper))
        res[f"{pred_label} {s} 하단예측"] = float(lower + (lower - prev_lower))
    return res, ma20, (ma20 + std * 2.0), (ma20 - std * 2.0)

def display_sorted_prices(price_dict, current_price, title):
    sorted_items = sorted(price_dict.items(), key=lambda x: x[1], reverse=True)
    st.subheader(title)
    for name, price in sorted_items:
        diff_pct = ((price / current_price) - 1) * 100
        if name == "현재가":
            st.markdown(f"### 🚩 **{name}: {price:,.0f}원**")
        else:
            st.write(f"{name}: **{price:,.0f}원** ({diff_pct:+.2f}%)")

# 2. 앱 화면 구성
tabs = st.tabs(list(STOCKS.keys()))

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        d_data = get_clean_data(ticker, "60d", "1d")
        w_data = get_clean_data(ticker, "1y", "1wk")
        
        if d_data is not None and w_data is not None:
            curr_p = float(d_data['Close'].iloc[-1])
            d_res, d_ma, d_up, d_lo = calculate_all(d_data, STD_LIST, "일봉")
            w_res, w_ma, w_up, w_lo = calculate_all(w_data, STD_LIST, "주봉")
            
            # --- 차트 영역 ---
            st.subheader("📈 최근 흐름 (일봉 2.0 기준)")
            chart_data = pd.DataFrame({
                "현재가": d_data['Close'],
                "상단(2.0)": d_up,
                "중심선": d_ma,
                "하단(2.0)": d_lo
            })
            st.line_chart(chart_data)

            # --- 상단: 확정 지표 ---
            now_vals = {"현재가": curr_p}
            for res in [d_res, w_res]:
                for k, v in res.items():
                    if "예측" not in k: now_vals[k] = v
            display_sorted_prices(now_vals, curr_p, "📊 금일/금주 확정 지표")
            
            st.divider()
            
            # --- 하단: 예측 데이터 ---
            pred_vals = {"현재가": curr_p}
            for res in [d_res, w_res]:
                for k, v in res.items():
                    if "예측" in k: pred_vals[k] = v
            display_sorted_prices(pred_vals, curr_p, "🔮 내일/차주 방향성 예측")
