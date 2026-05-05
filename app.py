import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="SK하이닉스 전략 시뮬레이터", layout="wide")
st.title("💾 SK하이닉스 변동성 밴드 (NXT 대응)")

# 1. 설정값 (SK하이닉스 고정)
TICKER = "000660.KS"
STD_LIST = [2.0, 1.6, 1.0]

def get_band(df, std_val):
    # (고+저+종)/3 계산
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    ma20 = typical_price.rolling(window=20).mean()
    std_dev = typical_price.rolling(window=20).std()
    
    upper = ma20 + (std_dev * std_val)
    lower = ma20 - (std_dev * std_val)
    return upper, ma20, lower

def process_data(interval_name, period, interval):
    data = yf.download(TICKER, period=period, interval=interval)
    if data.empty:
        return None
    
    # 멀티인덱스 방지 및 단일화
    data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
    
    results = {}
    for s in STD_LIST:
        upper, ma, lower = get_band(data, s)
        # 마지막(현재)과 직전(과거) 데이터 추출
        results[s] = {
            "prev_upper": upper.iloc[-2],
            "curr_upper": upper.iloc[-1],
            "curr_ma": ma.iloc[-1],
            "curr_lower": lower.iloc[-1],
            "prev_lower": lower.iloc[-2]
        }
    return results, data['Close'].iloc[-1]

# 앱 화면 구성
tab1, tab2 = st.tabs(["일봉(Daily) 예측", "주봉(Weekly) 예측"])

with tab1:
    res_d, curr_p = process_data("일봉", "60d", "1d")
    if res_d:
        st.write(f"### 🗓️ 오늘 종가(지연): {float(curr_p):,.0f}원")
        for s in STD_LIST:
            st.info(f"**표준편차 {s} 밴드**")
            c1, c2, c3 = st.columns(3)
            # 예측 로직: 이전일과 오늘의 기울기를 이어 내일의 예상 범위를 보여줌
            next_up = res_d[s]['curr_upper'] + (res_d[s]['curr_upper'] - res_d[s]['prev_upper'])
            next_low = res_d[s]['curr_lower'] + (res_d[s]['curr_lower'] - res_d[s]['prev_lower'])
            
            c1.metric("내일 상단 예측", f"{next_up:,.0f}원")
            c2.metric("중심선", f"{res_d[s]['curr_ma']:,.0f}원")
            c3.metric("내일 하단 예측", f"{next_low:,.0f}원")

with tab2:
    res_w, curr_p = process_data("주봉", "1y", "1wk")
    if res_w:
        st.write(f"### 🗓️ 현재가(지연): {float(curr_p):,.0f}원")
        for s in STD_LIST:
            st.success(f"**표준편차 {s} 밴드**")
            w1, w2, w3 = st.columns(3)
            # 예측 로직: 지난주와 이번주의 기울기를 이어 다음주 예상 범위 산출
            next_w_up = res_w[s]['curr_upper'] + (res_w[s]['curr_upper'] - res_w[s]['prev_upper'])
            next_w_low = res_w[s]['curr_lower'] + (res_w[s]['curr_lower'] - res_w[s]['prev_lower'])
            
            w1.metric("차주 상단 예측", f"{next_w_up:,.0f}원")
            w2.metric("중심선", f"{res_w[s]['curr_ma']:,.0f}원")
            w3.metric("차주 하단 예측", f"{next_w_low:,.0f}원")
