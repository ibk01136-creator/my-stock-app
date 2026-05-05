import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

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
        res[f"{type_name} {s}상"] = ma + (std * s)
        res[f"{type_name} {s}하"] = ma - (std * s)
    return res

tabs = st.tabs(list(STOCKS.keys()))

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        d_raw = get_clean_data(ticker, "100d", "1d")
        w_raw = get_clean_data(ticker, "2y", "1wk")
        
        if d_raw is not None and w_raw is not None:
            d_bands = calculate_bands(d_raw, "일봉")
            w_bands = calculate_bands(w_raw, "주봉")
            
            # 1. 날짜 설정 (최근 20영업일)
            recent_idx = d_raw.index[-20:]
            last_date = recent_idx[-1]
            next_date = last_date + pd.Timedelta(days=1)
            
            # 2. Plotly 차트 생성
            fig = go.Figure()
            
            # --- 과거 데이터 (5/4까지 실선) ---
            # 현재가 (검정색)
            fig.add_trace(go.Scatter(x=recent_idx, y=d_raw['Close'].iloc[-20:], name='현재가', line=dict(color='black', width=2)))
            
            # 일봉 밴드 (빨강/파랑/보라 계열)
            colors_upper = ['#FFCCCC', '#FF6666', '#FF0000']
            colors_lower = ['#CCCCFF', '#6666FF', '#0000FF']
            
            fig.add_trace(go.Scatter(x=recent_idx, y=d_bands['일봉 중심'].iloc[-20:], name='일봉 중심', line=dict(color='purple', width=1)))
            for j, s in enumerate(STD_LIST):
                fig.add_trace(go.Scatter(x=recent_idx, y=d_bands[f'일봉 {s}상'].iloc[-20:], name=f'일봉 {s}상', line=dict(color=colors_upper[j], width=1)))
                fig.add_trace(go.Scatter(x=recent_idx, y=d_bands[f'일봉 {s}하'].iloc[-20:], name=f'일봉 {s}하', line=dict(color=colors_lower[j], width=1)))

            # 주봉 밴드 (첫 영업일 매칭 및 선 연결)
            for j, s in enumerate(STD_LIST):
                # 주봉 데이터 중 최근 20일 범위에 있는 것만 추출
                w_sub = w_bands[f'주봉 {s}상'][w_bands[f'주봉 {s}상'].index >= recent_idx[0]]
                fig.add_trace(go.Scatter(x=w_sub.index, y=w_sub.values, name=f'주봉 {s}상', line=dict(color=colors_upper[j], width=1, dash='dashdot')))
                
                w_sub_l = w_bands[f'주봉 {s}하'][w_bands[f'주봉 {s}하'].index >= recent_idx[0]]
                fig.add_trace(go.Scatter(x=w_sub_l.index, y=w_sub_l.values, name=f'주봉 {s}하', line=dict(color=colors_lower[j], width=1, dash='dashdot')))

            # --- 미래 예측 (내일 하루만 점선) ---
            future_x = [last_date, next_date] # 5/4에서 5/5로 이어지는 선
            for k, v in d_bands.items():
                diff = v.iloc[-1] - v.iloc[-2]
                pred_val = v.iloc[-1] + diff
                fig.add_trace(go.Scatter(x=future_x, y=[v.iloc[-1], pred_val], line=dict(dash='dot', width=1), showlegend=False))

            # 3. 레이아웃 설정 (Y축 스케일 및 X축 포맷)
            y_min = float(d_raw['Close'].iloc[-20:].min() * 0.95)
            y_max = float(d_raw['Close'].iloc[-20:].max() * 1.05)

            fig.update_layout(
                height=500,
                margin=dict(l=10, r=10, t=30, b=10),
                xaxis=dict(tickformat='%m/%d', range=[recent_idx[0], next_date]),
                yaxis=dict(range=[y_min, y_max], autorange=False), # Y축 강제 고정
                showlegend=False,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            
            # 4. 하단 가격 리스트 (내림차순 정렬)
            curr_p = float(d_raw['Close'].iloc[-1])
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("📊 금일/금주 확정")
                p_map = {"현재가": curr_p}
                for k, v in d_bands.items(): p_map[k] = float(v.iloc[-1])
                for k, v in w_bands.items(): p_map[k] = float(v.iloc[-1])
                for k, v in sorted(p_map.items(), key=lambda x: x[1], reverse=True):
                    diff = ((v/curr_p)-1)*100
                    if k == "현재가": st.markdown(f"### 🚩 {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({diff:+.2f}%)")

            with c2:
                st.subheader("🔮 내일/차주 예측")
                f_map = {"현재가": curr_p}
                for k, v in d_bands.items(): f_map[f"{k}예측"] = float(v.iloc[-1] + (v.iloc[-1]-v.iloc[-2]))
                for k, v in w_bands.items(): f_map[f"{k}예측"] = float(v.iloc[-1] + (v.iloc[-1]-v.iloc[-2]))
                for k, v in sorted(f_map.items(), key=lambda x: x[1], reverse=True):
                    diff = ((v/curr_p)-1)*100
                    if k == "현재가": st.markdown(f"### 🚩 {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({diff:+.2f}%)")
