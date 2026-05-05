import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="주식 변동성 전략 시뮬레이터", layout="wide")

STOCKS = {"SK하이닉스": "000660.KS", "삼성전자": "005930.KS"}
STD_LIST = [2.0, 1.6, 1.0]

def get_clean_data(ticker, period, interval):
    data = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
    if data.empty: return None
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data

def calculate_logic(data, type_name):
    tp = (data['High'] + data['Low'] + data['Close']) / 3
    ma = tp.rolling(window=20).mean()
    std = tp.rolling(window=20).std()
    
    res = {}
    # 현재 확정값
    res[f"{type_name} 중심"] = ma
    for s in STD_LIST:
        res[f"{type_name} {s}상"] = ma + (std * s)
        res[f"{type_name} {s}하"] = ma - (std * s)
    
    # 기울기 계산 (마지막 값 - 직전 값)
    diff = {}
    for k, v in res.items():
        diff[k] = v.iloc[-1] - v.iloc[-2]
        
    return res, diff

# 앱 화면 구성
tabs = st.tabs(list(STOCKS.keys()))

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        d_data = get_clean_data(ticker, "60d", "1d")
        w_data = get_clean_data(ticker, "1y", "1wk")
        
        if d_data is not None and w_data is not None:
            # 1. 데이터 계산
            d_res, d_diff = calculate_logic(d_data, "일봉")
            w_res, w_diff = calculate_logic(w_data, "주봉")
            curr_p = float(d_data['Close'].iloc[-1])

            # 2. 차트용 데이터프레임 빌드 (최근 20일)
            recent_idx = d_data.index[-20:]
            chart_df = pd.DataFrame(index=recent_idx)
            chart_df['현재가'] = d_data['Close'].iloc[-20:]
            
            for k, v in d_res.items(): chart_df[k] = v.iloc[-20:]
            for k, v in w_res.items(): chart_df[k] = v.iloc[-20:]

            # 3. 미래 5일 예측 데이터 추가
            last_date = d_data.index[-1]
            future_indices = [last_date + pd.Timedelta(days=j) for j in range(1, 6)]
            forecast_df = pd.DataFrame(index=future_indices)
            
            for k, v in d_res.items():
                base = v.iloc[-1]
                forecast_df[f"{k}예측"] = [base + d_diff[k] * j for j in range(1, 6)]
            for k, v in w_res.items():
                base = v.iloc[-1]
                forecast_df[f"{k}예측"] = [base + w_diff[k] * j for j in range(1, 6)]

            # 4. 합치기 및 날짜 포맷 변경 (MM-DD)
            final_df = pd.concat([chart_df, forecast_df])
            final_df.index = final_df.index.strftime('%m-%d')

            # 5. 차트 출력
            st.subheader(f"📈 {name} 변동성 통합 차트 (20일 확정 + 5일 예측)")
            # y축 스케일 자동 조정을 위해 최솟값/최댓값 계산
            y_min = final_df.min().min() * 0.98
            y_max = final_df.max().max() * 1.02
            
            st.line_chart(final_df) # 기본 차트 사용

            st.divider()
            
            # --- 하단 숫자 리스트 (기존 로직 유지) ---
            st.write("🔍 **상세 가격 정보는 아래 리스트를 확인하세요**")
            # (이전 답변의 display_sorted_prices 로직 적용...)
