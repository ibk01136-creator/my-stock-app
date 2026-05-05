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
            
            # 1. 주봉 주기 (4/27~5/4 간격 = 4영업일)
            b_days = len(pd.bdate_range(w_raw.index[-2], w_raw.index[-1])) - 1
            if b_days <= 0: b_days = 5
            
            # 2. 오늘(5/4) 기준 주봉 확정일부터 경과일
            days_passed = len(pd.bdate_range(w_raw.index[-1], recent_idx[-1])) - 1
            
            # 3. 남은 칸수 (4 - 0 = 4)
            remain_days = b_days - days_passed
            if remain_days < 1: remain_days = 1

            # --- [해결책] 인덱스 구조와 라벨의 완전 일치 ---
            # 오늘(5/4)은 무조건 19번 인덱스
            today_x = 19
            
            # 전체 X축을 넉넉하게 30칸으로 설정 (0~29)
            x_range = list(range(30))
            date_labels = ["" for _ in range(30)]
            
            # 과거(0~19) 날짜 채우기
            for idx, d in enumerate(recent_idx):
                date_labels[idx] = d.strftime('%m/%d')
            
            # 미래(20~29) 라벨 채우기: 인덱스 번호에서 19를 뺀 값을 표시
            # 인덱스 20 -> +1, 21 -> +2, 22 -> +3, 23 -> +4
            for idx in range(20, 30):
                date_labels[idx] = f"+{idx - today_x}"
            
            # 실제 찍힐 위치
            d_pred_x = today_x + 1 # 20번 인덱스
            w_pred_x = today_x + remain_days # 23번 인덱스

            fig = go.Figure()
            c_up = ['#FFCCCC', '#FF6666', '#FF0000']
            c_lo = ['#CCCCFF', '#6666FF', '#0000FF']

            # 1. 일봉 차트
            d_keys = list(d_bands.keys())
            for key in d_keys:
                color = 'purple' if '중심' in key else (c_up[STD_LIST.index(float(key.split()[1][:-1]))] if '상' in key else c_lo[STD_LIST.index(float(key.split()[1][:-1]))])
                y_vals = d_bands[key].iloc[-20:].tolist()
                fig.add_trace(go.Scatter(x=x_range[:20], y=y_vals, name=key, line=dict(color=color, width=1)))
                
                # 일봉 예측 (+1)
                slope = d_bands[key].iloc[-1] - d_bands[key].iloc[-2]
                fig.add_trace(go.Scatter(x=[today_x, d_pred_x], y=[y_vals[-1], y_vals[-1] + slope], 
                                         line=dict(color=color, width=1, dash='dot'), showlegend=False))

            # 2. 주봉 차트
            w_keys = list(w_bands.keys())
            for key in w_keys:
                color = '#BA55D3' if '중심' in key else (c_up[STD_LIST.index(float(key.split()[1][:-1]))] if '상' in key else c_lo[STD_LIST.index(float(key.split()[1][:-1]))])
                w_sub = w_bands[key][w_bands[key].index >= recent_idx[0]]
                
                # 과거 주봉 데이터 위치 매칭
                w_x = []
                for dt in w_sub.index:
                    dt_str = dt.strftime('%m/%d')
                    if dt_str in date_labels[:20]:
                        w_x.append(date_labels[:20].index(dt_str))
                
                fig.add_trace(go.Scatter(x=w_x, y=w_sub.values, name=key, line=dict(color=color, width=1, dash='dashdot')))
                
                # 주봉 예측 (동적 위치: +remain_days)
                w_slope = w_bands[key].iloc[-1] - w_bands[key].iloc[-2]
                fig.add_trace(go.Scatter(x=[today_x, w_pred_x], y=[w_sub.values[-1], w_sub.values[-1] + w_slope], 
                                         line=dict(color=color, width=1, dash='dot'), showlegend=False))

            # 현재가 실선
            fig.add_trace(go.Scatter(x=x_range[:20], y=d_raw['Close'].iloc[-20:], name='현재가', line=dict(color='black', width=2)))

            fig.update_layout(
                height=500, margin=dict(l=5, r=5, t=30, b=5),
                xaxis=dict(tickmode='array', tickvals=x_range, ticktext=date_labels, range=[0, w_pred_x + 0.5]),
                yaxis=dict(tickformat=","),
                hovermode='x unified', showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

            # 하단 리스트
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
                st.subheader(f"🔮 예측 (일봉+1, 주봉+{remain_days})")
                f_map = {"현재가": curr_p}
                for k in d_keys: f_map[f"{k}예측"] = float(d_bands[k].iloc[-1] + (d_bands[k].iloc[-1] - d_bands[k].iloc[-2]))
                for k in w_keys: f_map[f"{k}예측"] = float(w_bands[k].iloc[-1] + (w_bands[k].iloc[-1] - w_bands[k].iloc[-2]))
                for k, v in sorted(f_map.items(), key=lambda x: x[1], reverse=True):
                    if k == "현재가": st.markdown(f"### 🚩 {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({((v/curr_p)-1)*100:+.2f}%)")
