import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="주식 변동성 전략 도우미", layout="wide")

# 1. 설정 및 계산 함수
STOCKS = {"SK하이닉스": "000660.KS", "삼성전자": "005930.KS"}
STD_LIST = [2.0, 1.6, 1.0]

def get_clean_data(ticker, period, interval):
    # auto_adjust=True를 써서 가격 데이터 구조를 단순화합니다.
    data = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
    if data.empty: return None
    
    # [핵심] 멀티인덱스(중첩 구조)를 한 줄로 압축합니다.
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    return data

def calculate_all(data, std_list, type_name):
    # Typical Price (HLC/3) 계산
    tp = (data['High'] + data['Low'] + data['Close']) / 3
    ma20 = tp.rolling(window=20).mean()
    std = tp.rolling(window=20).std()
    
    res = {}
    for s in std_list:
        upper = ma20.iloc[-1] + (std.iloc[-1] * s)
        lower = ma20.iloc[-1] - (std.iloc[-1] * s)
        # 예측값 (기울기 반영)
        prev_upper = ma20.iloc[-2] + (std.iloc[-2] * s)
        prev_lower = ma20.iloc[-2] - (std.iloc[-2] * s)
        
        res[f"{type_name} {s} 상단"] = float(upper)
        res[f"{type_name} {s} 하단"] = float(lower)
        res[f"{type_name.replace('금','내').replace('주','다음주')} {s} 상단예측"] = float(upper + (upper - prev_upper))
        res[f"{type_name.replace('금','내').replace('주','다음주')} {s} 하단예측"] = float(lower + (lower - prev_lower))
    return res

def display_sorted_prices(price_dict, current_price, title):
    sorted_items = sorted(price_dict.items(), key=lambda x: x[1], reverse=True)
    st.subheader(title)
    for name, price in sorted_items:
        diff_pct = ((price / current_price) - 1) * 100
        if name == "현재가":
            st.markdown(f"### 🚩 **{name}: {price:,.0f}원**")
        else:
            color = "red" if price > current_price else "blue"
            st.write(f"{name}: **{price:,.0f}원** ({diff_pct:+.2f}%)")

# 2. 앱 화면 구성
tabs = st.tabs(list(STOCKS.keys()))

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        d_data = get_clean_data(ticker, "60d", "1d")
        w_data = get_clean_data(ticker, "1y", "1wk")
        
        if d_data is not None and w_data is not None:
            curr_p = float(d_data['Close'].iloc[-1])
            
            # 지표 계산
            d_res = calculate_all(d_data, STD_LIST, "일봉")
            w_res = calculate_all(w_data, STD_LIST, "주봉")
            
            # --- 상단: 현재 기준 데이터 ---
            now_vals = {"현재가": curr_p}
            for k, v in d_res.items(): 
                if "상단" in k or "하단" in k: now_vals[k] = v
            for k, v in w_res.items(): 
                if "상단" in k or "하단" in k: now_vals[k] = v
            display_sorted_prices(now_vals, curr_p, "📊 금일/금주 지표 (내림차순)")
            
            st.divider()
            
            # --- 하단: 예측 데이터 ---
            pred_vals = {"현재가": curr_p}
            for k, v in d_res.items(): 
                if "예측" in k: pred_vals[k] = v
            for k, v in w_res.items(): 
                if "예측" in k: pred_vals[k] = v
            display_sorted_prices(pred_vals, curr_p, "🔮 내일/차주 예측 (내림차순)")
