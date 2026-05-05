import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="주식 변동성 전략 도우미", layout="wide")

# 1. 설정 및 계산 함수
STOCKS = {"SK하이닉스": "000660.KS", "삼성전자": "005930.KS"}
STD_LIST = [2.0, 1.6, 1.0]

def get_indicators(ticker, period, interval):
    data = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
    if data.empty: return None
    
    # Typical Price (HLC/3) 계산
    tp = (data['High'] + data['Low'] + data['Close']) / 3
    ma20 = tp.rolling(window=20).mean()
    std = tp.rolling(window=20).std()
    curr_p = float(data['Close'].iloc[-1])
    
    results = {"현재가": curr_p}
    for s in STD_LIST:
        results[f"일봉 {s} 상단"] = float(ma20.iloc[-1] + (std.iloc[-1] * s))
        results[f"일봉 {s} 하단"] = float(ma20.iloc[-1] - (std.iloc[-1] * s))
        # 예측값 계산 (기울기 반영)
        results[f"내일 {s} 상단예측"] = float((ma20.iloc[-1] + (std.iloc[-1] * s)) + ((ma20.iloc[-1] + (std.iloc[-1] * s)) - (ma20.iloc[-2] + (std.iloc[-2] * s))))
        results[f"내일 {s} 하단예측"] = float((ma20.iloc[-1] - (std.iloc[-1] * s)) + ((ma20.iloc[-1] - (std.iloc[-1] * s)) - (ma20.iloc[-2] - (std.iloc[-2] * s))))
    
    return results

def get_weekly_indicators(ticker):
    data = yf.download(ticker, period="1y", interval="1wk", auto_adjust=True)
    if data.empty: return None
    
    tp = (data['High'] + data['Low'] + data['Close']) / 3
    ma20 = tp.rolling(window=20).mean()
    std = tp.rolling(window=20).std()
    
    results = {}
    for s in STD_LIST:
        results[f"주봉 {s} 상단"] = float(ma20.iloc[-1] + (std.iloc[-1] * s))
        results[f"주봉 {s} 하단"] = float(ma20.iloc[-1] - (std.iloc[-1] * s))
        # 예측값 계산 (기울기 반영)
        results[f"다음주 {s} 상단예측"] = float((ma20.iloc[-1] + (std.iloc[-1] * s)) + ((ma20.iloc[-1] + (std.iloc[-1] * s)) - (ma20.iloc[-2] + (std.iloc[-2] * s))))
        results[f"다음주 {s} 하단예측"] = float((ma20.iloc[-1] - (std.iloc[-1] * s)) + ((ma20.iloc[-1] - (std.iloc[-1] * s)) - (ma20.iloc[-2] - (std.iloc[-2] * s))))
    
    return results

def display_sorted_prices(price_dict, current_price, title):
    # 가격 기준 내림차순 정렬
    sorted_items = sorted(price_dict.items(), key=lambda x: x[1], reverse=True)
    
    st.subheader(title)
    for name, price in sorted_items:
        diff_pct = ((price / current_price) - 1) * 100
        color = "red" if price > current_price else "blue"
        if name == "현재가":
            st.markdown(f"### 🚩 **{name}: {price:,.0f}원**")
        else:
            st.write(f"{name}: **{price:,.0f}원** ({diff_pct:+.2f}%)")

# 2. 앱 화면 구성
tabs = st.tabs(list(STOCKS.keys()))

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        daily_res = get_indicators(ticker, "60d", "1d")
        weekly_res = get_weekly_indicators(ticker)
        
        if daily_res and weekly_res:
            curr_p = daily_res["현재가"]
            
            # --- 상단: 금일 및 금주 실시간 데이터 ---
            now_data = {"현재가": curr_p}
            for k, v in daily_res.items():
                if "상단" in k or "하단" in k: 
                    if "내일" not in k: now_data[k] = v
            for k, v in weekly_res.items():
                if "상단" in k or "하단" in k:
                    if "다음주" not in k: now_data[k] = v
            
            display_sorted_prices(now_data, curr_p, "📊 금일/금주 지표 (가격순 정렬)")
            
            st.divider()
            
            # --- 하단: 내일 및 다음주 예측 데이터 ---
            predict_data = {"현재가": curr_p}
            for k, v in daily_res.items():
                if "예측" in k: predict_data[k] = v
            for k, v in weekly_res.items():
                if "예측" in k: predict_data[k] = v
            
            display_sorted_prices(predict_data, curr_p, "🔮 내일/차주 예측 (가격순 정렬)")
