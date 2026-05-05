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
            
            # --- 주봉 예측 위치 계산 로직 ---
            # 주봉의 마지막 두 데이터 사이의 영업일수 계산
            last_w_date = w_raw.index[-1]
            prev_w_date = w_raw.index[-2]
            # 두 날짜 사이의 실제 영업일수(평일 기준) 추출
            business_days = len(pd.bdate_range(prev_w_date, last_w_date)) - 1
            if business_days <= 0: business_days = 5 # 기본값 5일
            
            # 미래 날짜 라벨 생성 (최대 business_days만큼 확보)
            future_dates = []
            current_dt = last_date
            for _ in range(business_days):
                current_dt += pd.Timedelta(days=1)
                # 주말 제외하고 영업일만 추가 (간단한 예시)
                while current_dt.weekday() >= 5: 
                    current_dt += pd.Timedelta(days=1)
                future_dates.append(current_dt)
            
            # X축 라벨: 과거 20일 + 미래 영업일들
            date_labels = [d.strftime('%m/%d') for d in recent_idx] + [d.strftime('%m/%d') for d in future_dates]
            x_range = list(range(len(date_labels)))
            
            # 일봉 예측은 바로 다음 칸(+1), 주봉 예측은 계산된 영업일수 칸(+business_days)
            d_pred_x = len(recent_idx) 
            w_pred_x = len(recent_idx) + business_days - 1

            fig = go.Figure()
            c_up = ['#FFCCCC', '#FF6666', '#FF0000'] # 상단 (연한빨강 -> 진한빨강)
            c_lo = ['#CCCCFF', '#6666FF', '#0000FF'] # 하단 (연한파랑 -> 진한파랑)
            c_purple_lines = ['#E6E6FA', '#D8BFD8', '#DDA0DD', '#EE82EE'] # 보라 계열

            # 1. 일봉 및 예측선
            for key in d_bands.keys():
                if '중심' in key: color = '#800080' # 진보라
                elif '상' in key: color = c_up[STD_LIST.index(float(key.split()[1][:-1]))]
                else: color = c_lo[STD_LIST.index(float(key.split()[1][:-1]))]
                
                y_vals = d_bands[key].iloc[-20:].tolist()
                fig.add_trace(go.Scatter(x=x_range[:20], y=y_vals, name=key, line=dict(color=color, width=1)))
                
                slope = d_bands[key].iloc[-1] - d_bands[key].iloc[-2]
                pred_val = d_bands[key].iloc[-1] + slope
                fig.add_trace(go.Scatter(x=[x_range[19], d_pred_x], y=[y_vals[-1], pred_val], 
                                         line=dict(color=color, width=1, dash='dot'), showlegend=False))

            # 2. 주봉 및 예측선
            for key in w_bands.keys():
                # 주봉 중심선도 보라색 계열로 변경
                if '중심' in key: color = '#BA55D3' # 미디엄 오키드 (보라계열)
                elif '상' in key: color = c_up[STD_LIST.index(float(key.split()[1][:-1]))]
                else: color = c_lo[STD_LIST.index(float(key.split()[1][:-1]))]
                
                # 과거 주봉 매칭
                w_sub = w_bands[key][w_bands[key].index >= recent_idx[0]]
                w_x = [date_labels.index(dt.strftime('%m/%d')) for dt in w_sub.index if dt.strftime('%m/%d') in date_labels]
                
                fig.add_trace(go.Scatter(x=w_x, y=w_sub.values, name=key, line=dict(color=color, width=1, dash='dashdot')))
                
                # 주봉 미래 예측 (계산된 business_days 위치로 보냄)
                w_slope = w_bands[key].iloc[-1] - w_bands[key].iloc[-2]
                w_pred_val = w_bands[key].iloc[-1] + w_slope
                fig.add_trace(go.Scatter(x=[x_range[19], w_pred_x], y=[w_sub.values[-1], w_pred_val], 
                                         line=dict(color=color, width=1, dash='dot'), showlegend=False))

            # 현재가 실선
            fig.add_trace(go.Scatter(x=x_range[:20], y=d_raw['Close'].iloc[-20:], name='현재가', line=dict(color='black', width=2)))

            # 레이아웃
            y_min = float(d_raw['Close'].iloc[-20:].min() * 0.96)
            y_max = float(d_raw['Close'].iloc[-20:].max() * 1.04)

            fig.update_layout(
                height=500, margin=dict(l=5, r=5, t=30, b=5),
                xaxis=dict(tickmode='array', tickvals=x_range, ticktext=date_labels, range=[0, w_pred_x + 1]),
                yaxis=dict(range=[y_min, y_max], autorange=False, tickformat=","),
                showlegend=False, hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

            # 3. 하단 리스트
            curr_p = float(d_raw['Close'].iloc[-1])
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📊 금일 확정")
                p_map = {"현재가": curr_p}
                for k in list(d_bands.keys()): p_map[k] = float(d_bands[k].iloc[-1])
                for k in list(w_bands.keys()): p_map[k] = float(w_bands[k].iloc[-1])
                for k, v in sorted(p_map.items(), key=lambda x: x[1], reverse=True):
                    if k == "현재가": st.markdown(f"### 🚩 {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({((v/curr_p)-1)*100:+.2f}%)")
            with c2:
                st.subheader("🔮 내일/차주 예측")
                f_map = {"현재가": curr_p}
                for k in list(d_bands.keys()): f_map[f"{k}예측"] = float(d_bands[k].iloc[-1] + (d_bands[k].iloc[-1] - d_bands[k].iloc[-2]))
                for k in list(w_bands.keys()): f_map[f"{k}예측"] = float(w_bands[k].iloc[-1] + (w_bands[k].iloc[-1] - w_bands[k].iloc[-2]))
                for k, v in sorted(f_map.items(), key=lambda x: x[1], reverse=True):
                    if k == "현재가": st.markdown(f"### 🚩 {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({((v/curr_p)-1)*100:+.2f}%)")
