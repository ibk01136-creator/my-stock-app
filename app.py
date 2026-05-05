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

def calculate_bands(data, type_name):
    tp = (data['High'] + data['Low'] + data['Close']) / 3
    ma = tp.rolling(window=20).mean()
    std = tp.rolling(window=20).std()
    
    res = {f"{type_name} 중심": ma}
    for s in STD_LIST:
        res[f"{type_name} {s}상"] = ma + (std * s)
        res[f"{type_name} {s}하"] = ma - (std * s)
    return res

# 앱 화면 구성
tabs = st.tabs(list(STOCKS.keys()))

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        # 데이터 로드
        d_raw = get_clean_data(ticker, "100d", "1d")
        w_raw = get_clean_data(ticker, "2y", "1wk")
        
        if d_raw is not None and w_raw is not None:
            # 1. 지표 계산
            d_bands = calculate_bands(d_raw, "일봉")
            w_bands = calculate_bands(w_raw, "주봉")
            
            # 2. 차트용 타임라인 구성 (최근 20영업일)
            recent_idx = d_raw.index[-20:]
            chart_df = pd.DataFrame(index=recent_idx)
            chart_df['현재가'] = d_raw['Close'].iloc[-20:]
            
            # 일봉 7개 추가
            for k, v in d_bands.items(): chart_df[k] = v.iloc[-20:]
            
            # 주봉 7개 추가 (일봉 날짜에 맞춰 주봉 값을 매칭)
            # 주봉 데이터의 날짜가 일봉 날짜보다 이전일 수 있으므로 ffill(앞의 값으로 채우기) 사용
            for k, v in w_bands.items():
                temp_w = v.reindex(recent_idx, method='ffill')
                chart_df[k] = temp_w

            # 3. 미래 5일 예측 (단순 +1일씩 5번)
            last_date = recent_idx[-1]
            future_idx = [last_date + pd.Timedelta(days=j) for j in range(1, 6)]
            forecast_df = pd.DataFrame(index=future_idx)
            
            # 예측값 기울기 및 데이터 생성
            for k in chart_df.columns:
                if k == '현재가': continue
                base_val = chart_df[k].iloc[-1]
                prev_val = chart_df[k].iloc[-2]
                diff = base_val - prev_val
                forecast_df[f"{k}예측"] = [base_val + diff * j for j in range(1, 6)]

            # 4. 최종 병합 및 포맷팅
            final_df = pd.concat([chart_df, forecast_df])
            # y축 스케일 수동 계산 (현재가 주변 ±15% 정도로 타이트하게)
            y_min = float(final_df.min().min() * 0.95)
            y_max = float(final_df.max().max() * 1.05)

            # 날짜 인덱스를 MM/DD 문자열로 변환
            final_df.index = final_df.index.strftime('%m/%d')

            # 5. 차트 출력 (st.line_chart 대신 세부 설정이 가능한 st.area_chart나 오토스케일 적용)
            st.subheader(f"📈 {name} 통합 변동성 차트")
            
            # Streamlit 기본 차트는 y축 범위를 직접 지정하는 인자가 없으므로 
            # 데이터를 슬라이싱하거나 Plotly 없이 해결하려면 이 방식이 최선입니다.
            st.line_chart(final_df, y_label="가격(원)")

            st.divider()
            
            # --- 숫자 리스트 부분 (생략 - 이전 로직과 동일) ---
            st.info("차트의 X축은 20일 확정값과 5일 예측값으로 구성됩니다.")
