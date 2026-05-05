import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="변동성 전략 시뮬레이터", layout="wide")

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
            
            recent_idx = d_raw.index[-20:]
            last_date = recent_idx[-1]
            next_date = last_date + pd.Timedelta(days=1)
            
            fig = go.Figure()
            c_up = ['#FFCCCC', '#FF6666', '#FF0000']
            c_lo = ['#CCCCFF', '#6666FF', '#0000FF']

            # 1. 일봉 차트 그리기
            # 모든 일봉 라인(중심 + 6개 밴드)에 대해 개별 기울기 적용
            d_keys = list(d_bands.keys())
            for key in d_keys:
                if '중심' in key: color = 'purple'
                elif '상' in key: color = c_up[STD_LIST.index(float(key.split()[1][:-1]))]
                else: color = c_lo[STD_LIST.index(float(key.split()[1][:-1]))]
                
                # 과거 실선
                fig.add_trace(go.Scatter(x=recent_idx, y=d_bands[key].iloc[-20:], name=key, line=dict(color=color, width=1)))
                
                # 미래 예측 (해당 선의 개별 기울기: 오늘값 - 어제값)
                slope = d_bands[key].iloc[-1] - d_bands[key].iloc[-2]
                pred_val = d_bands[key].iloc[-1] + slope
                fig.add_trace(go.Scatter(x=[last_date, next_date], y=[d_bands[key].iloc[-1], pred_val], 
                                         line=dict(color=color, width=1, dash='dot'), showlegend=False))

            # 2. 주봉 차트 그리기
            w_keys = list(w_bands.keys())
            for key in w_keys:
                if '중심' in key: color = 'green'
                elif '상' in key: color = c_up[STD_LIST.index(float(key.split()[1][:-1]))]
                else: color = c_lo[STD_LIST.index(float(key.split()[1][:-1]))]
                
                # 과거 (월요일 등 주의 첫 영업일 데이터만 추출)
                w_sub = w_bands[key][w_bands[key].index >= recent_idx[0]]
                fig.add_trace(go.Scatter(x=w_sub.index, y=w_sub.values, name=key, line=dict(color=color, width=1, dash='dashdot')))
                
                # 주봉 미래 예측 (주봉도 해당 선의 개별 기울기 적용하여 +1일 연결)
                w_slope = w_bands[key].iloc[-1] - w_bands[key].iloc[-2]
                w_pred_val = w_bands[key].iloc[-1] + w_slope
                fig.add_trace(go.Scatter(x=[last_date, next_date], y=[w_bands[key].iloc[-1], w_pred_val], 
                                         line=dict(color=color, width=1, dash='dot'), showlegend=False))

            # 현재가 실선 (5/4에서 끝남)
            fig.add_trace(go.Scatter(x=recent_idx, y=d_raw['Close'].iloc[-20:], name='현재가', line=dict(color='black', width=2)))

            # 레이아웃 설정
            y_min = float(d_raw['Close'].iloc[-20:].min() * 0.96)
            y_max = float(d_raw['Close'].iloc[-20:].max() * 1.04)

            fig.update_layout(
                height=500, margin=dict(l=5, r=5, t=30, b=5),
                xaxis=dict(tickformat='%m/%d', range=[recent_idx[0], next_date]),
                yaxis=dict(range=[y_min, y_max], autorange=False),
                showlegend=False, hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

            # 3. 하단 리스트 (개별 기울기 반영)
            curr_p = float(d_raw['Close'].iloc[-1])
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📊 금일 확정")
                p_map = {"현재가": curr_p}
                for k in d_keys: p_map[k] = float(d_bands[k].iloc[-1])
                for k in w_keys: p_map[k] = float(w_bands[k].iloc[-1])
                for k, v in sorted(p_map.items(), key=lambda x: x[1], reverse=True):
                    if k == "현재가": st.markdown(f"### 🚩 {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({((v/curr_p)-1)*100:+.2f}%)")
            with c2:
                st.subheader("🔮 내일 예측")
                f_map = {"현재가": curr_p}
                for k in d_keys: f_map[f"{k}예측"] = float(d_bands[k].iloc[-1] + (d_bands[k].iloc[-1] - d_bands[k].iloc[-2]))
                for k in w_keys: f_map[f"{k}예측"] = float(w_bands[k].iloc[-1] + (w_bands[k].iloc[-1] - w_bands[k].iloc[-2]))
                for k, v in sorted(f_map.items(), key=lambda x: x[1], reverse=True):
                    if k == "현재가": st.markdown(f"### 🚩 {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({((v/curr_p)-1)*100:+.2f}%)")
