import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="SK/삼성 변동성 전략", layout="wide")

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
        res[f"{type_name} {s}상"]: ma + (std * s)
        res[f"{type_name} {s}하"]: ma - (std * s)
    
    # 딕셔너리 재구성 (에러 방지용)
    final_res = {f"{type_name} 중심": ma}
    for s in STD_LIST:
        final_res[f"{type_name} {s}상"] = ma + (std * s)
        final_res[f"{type_name} {s}하"] = ma - (std * s)
    return final_res

tabs = st.tabs(list(STOCKS.keys()))

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        d_raw = get_clean_data(ticker, "100d", "1d")
        w_raw = get_clean_data(ticker, "2y", "1wk")
        
        if d_raw is not None and w_raw is not None:
            d_bands = calculate_bands(d_raw, "일봉")
            w_bands = calculate_bands(w_raw, "주봉")
            
            # 1. 차트 데이터 빌드
            recent_idx = d_raw.index[-20:]
            chart_df = pd.DataFrame(index=recent_idx)
            chart_df['현재가'] = d_raw['Close'].iloc[-20:]
            
            for k, v in d_bands.items(): chart_df[k] = v.iloc[-20:]
            
            # 주봉: 첫 영업일만 값 할당 (나머지는 NaN 유지하여 선 연결)
            for k, v in w_bands.items():
                s = pd.Series(index=recent_idx, dtype='float64')
                intersect = v.index.intersection(recent_idx)
                s.loc[intersect] = v.loc[intersect]
                chart_df[k] = s

            # 2. 미래 1일 예측 추가 (연결점 생성)
            last_dt = recent_idx[-1]
            next_dt = last_dt + pd.Timedelta(days=1)
            
            # 예측용 데이터 한 줄 생성
            forecast_row = {}
            for col in chart_df.columns:
                if col == '현재가': continue
                vals = chart_df[col].dropna()
                if len(vals) >= 2:
                    diff = vals.iloc[-1] - vals.iloc[-2]
                    forecast_row[col] = vals.iloc[-1] + diff
            
            # 3. 차트 출력 (st.line_chart의 개선된 버전 사용)
            st.subheader(f"📈 {name} 통합 차트")
            
            # Y축 0원 문제 해결을 위해 전용 옵션 사용
            plot_df = chart_df.copy()
            # 예측값 추가 (마지막 행에 붙임)
            forecast_series = pd.Series(forecast_row, name=next_dt)
            plot_df = pd.concat([plot_df, forecast_series.to_frame().T])
            
            # 인덱스를 문자열로 변환 (MM/DD)
            plot_df.index = plot_df.index.strftime('%m/%d')
            
            # st.line_chart는 최신 버전에서 y축 범위를 자동으로 잡아줍니다.
            st.line_chart(plot_df)

            st.divider()
            
            # 4. 하단 가격 리스트
            curr_p = float(d_raw['Close'].iloc[-1])
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("📊 금일/금주 확정")
                p_map = {"현재가": curr_p}
                for k, v in d_bands.items(): p_map[k] = float(v.iloc[-1])
                for k, v in w_bands.items(): p_map[k] = float(v.iloc[-1])
                for k, v in sorted(p_map.items(), key=lambda x: x[1], reverse=True):
                    p_diff = ((v/curr_p)-1)*100
                    if k == "현재가": st.markdown(f"### 🚩 {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({p_diff:+.2f}%)")

            with c2:
                st.subheader("🔮 내일/차주 예측")
                f_map = {"현재가": curr_p}
                for k, v in d_bands.items(): f_map[f"{k}예측"] = float(v.iloc[-1] + (v.iloc[-1]-v.iloc[-2]))
                for k, v in w_bands.items(): f_map[f"{k}예측"] = float(v.iloc[-1] + (v.iloc[-1]-v.iloc[-2]))
                for k, v in sorted(f_map.items(), key=lambda x: x[1], reverse=True):
                    f_diff = ((v/curr_p)-1)*100
                    if k == "현재가": st.markdown(f"### 🚩 {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({f_diff:+.2f}%)")
