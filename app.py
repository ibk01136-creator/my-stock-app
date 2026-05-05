import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="변동성 전략 시뮬레이터", layout="wide")

STOCKS = {
    "SK하이닉스": "000660.KS", "삼성전자": "005930.KS", "LIG디펜스": "079550.KS",
    "삼성SDI": "006400.KS", "두산에너빌리티": "034020.KS", "엘앤에프": "066970.KQ",
    "삼성생명": "032830.KS", "SK스퀘어": "402340.KS", "삼성전기": "009150.KS",
    "HD건설기계": "267270.KS", "HD일렉트릭": "267260.KS", "한화": "000880.KS",
    "삼성중공업": "010140.KS", "삼성E&A": "028050.KS", "하나금융지주": "086790.KS"
}

def get_shares_dynamic(ticker):
    """실시간 주식수 획득 (야후 데이터 부재 시 0 반환)"""
    try:
        t = yf.Ticker(ticker)
        shares = t.fast_info.get('shares_outstanding', 0)
        return shares if shares else 0
    except:
        return 0

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
    for s in [2.0, 1.6, 1.0]:
        res[f"{type_name} {s}상"] = ma + (std * s)
        res[f"{type_name} {s}하"] = ma - (std * s)
    return res

@st.cache_data(ttl=3600)
def get_dynamic_kospi_cap():
    kospi = yf.download("^KS11", period="1d", interval="1m")
    if not kospi.empty:
        curr_index = kospi['Close'].iloc[-1]
        base_index, base_cap = 6936.99, 5686_000_000_000_000
        return base_cap * (curr_index / base_index)
    return 5686_000_000_000_000

current_total_cap = get_dynamic_kospi_cap()
tabs = st.tabs(list(STOCKS.keys()))

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        d_raw = get_clean_data(ticker, "100d", "1d")
        w_raw = get_clean_data(ticker, "2y", "1wk")
        
        if d_raw is not None and w_raw is not None:
            curr_price = float(d_raw['Close'].iloc[-1])
            shares = get_shares_dynamic(ticker)
            m_cap = curr_price * shares
            m_ratio = (m_cap / current_total_cap) * 100 if current_total_cap else 0
            
            d_bands = calculate_bands(d_raw, "일봉")
            w_bands = calculate_bands(w_raw, "주봉")
            
            recent_idx = d_raw.index[-20:]
            today_x, last_date = 19, recent_idx[-1]
            prev_w_date, this_w_date = w_raw.index[-2], w_raw.index[-1]
            actual_gap_days = len(d_raw[(d_raw.index >= prev_w_date) & (d_raw.index < this_w_date)])
            if actual_gap_days == 0: actual_gap_days = 5
            passed_days = len(d_raw[(d_raw.index >= this_w_date) & (d_raw.index <= last_date)]) - 1
            remain_days = max(1, actual_gap_days - passed_days)

            d_pred_x, w_pred_x = today_x + 1, today_x + remain_days
            x_range = list(range(35))
            date_labels = ["" for _ in range(35)]
            for idx, d in enumerate(recent_idx): date_labels[idx] = d.strftime('%m/%d')
            for idx in range(20, 35): date_labels[idx] = f"+{idx - today_x}"

            fig = go.Figure()
            c_up, c_lo = ['#FFCCCC', '#FF6666', '#FF0000'], ['#CCCCFF', '#6666FF', '#0000FF']
            upper_vals, w_center_vals = [], []

            for key in d_bands:
                color = 'purple' if '중심' in key else (c_up[[2.0, 1.6, 1.0].index(float(key.split()[1][:-1]))] if '상' in key else c_lo[[2.0, 1.6, 1.0].index(float(key.split()[1][:-1]))])
                y_vals = d_bands[key].iloc[-20:].tolist()
                fig.add_trace(go.Scatter(x=x_range[:20], y=y_vals, name=key, line=dict(color=color, width=1)))
                if '상' in key or '중심' in key: upper_vals.extend(y_vals)
                slope = d_bands[key].iloc[-1] - d_bands[key].iloc[-2]
                pred_y = y_vals[-1] + slope
                fig.add_trace(go.Scatter(x=[today_x, d_pred_x], y=[y_vals[-1], pred_y], line=dict(color=color, width=1, dash='dot'), showlegend=False))
                if '상' in key or '중심' in key: upper_vals.append(pred_y)

            for key in w_bands:
                color = '#BA55D3' if '중심' in key else (c_up[[2.0, 1.6, 1.0].index(float(key.split()[1][:-1]))] if '상' in key else c_lo[[2.0, 1.6, 1.0].index(float(key.split()[1][:-1]))])
                w_sub = w_bands[key][w_bands[key].index >= recent_idx[0]]
                w_x = [d_raw.index.get_loc(dt) - (len(d_raw) - 20) for dt in w_sub.index if dt in d_raw.index]
                w_x = [x for x in w_x if 0 <= x < 20]
                fig.add_trace(go.Scatter(x=w_x, y=w_sub.values[:len(w_x)], name=key, line=dict(color=color, width=1, dash='dashdot')))
                if '상' in key or '중심' in key: upper_vals.extend(w_sub.values)
                if '중심' in key: w_center_vals.extend(w_sub.values)
                w_slope = w_bands[key].iloc[-1] - w_bands[key].iloc[-2]
                w_pred_y = w_sub.values[-1] + w_slope
                fig.add_trace(go.Scatter(x=[today_x, w_pred_x], y=[w_sub.values[-1], w_pred_y], line=dict(color=color, width=1, dash='dot'), showlegend=False))
                if '상' in key or '중심' in key: upper_vals.append(w_pred_y)
                if '중심' in key: w_center_vals.append(w_pred_y)

            curr_close_v = d_raw['Close'].iloc[-20:].tolist()
            fig.add_trace(go.Scatter(x=x_range[:20], y=curr_close_v, name='현재가', line=dict(color='black', width=2)))
            
            y_min = min(curr_close_v + w_center_vals) * 0.995
            y_max = max(upper_vals + curr_close_v) * 1.005
            fig.update_layout(height=500, margin=dict(l=5, r=5, t=30, b=5),
                xaxis=dict(tickmode='array', tickvals=x_range, ticktext=date_labels, range=[0, w_pred_x + 1]),
                yaxis=dict(tickformat=",", range=[y_min, y_max]), hovermode='x unified', showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📊 금일 확정")
                p_map = {k: float(d_bands[k].iloc[-1]) for k in d_bands}
                p_map.update({k: float(w_bands[k].iloc[-1]) for k in w_bands})
                p_map["🚩 현재가"] = curr_price
                for k, v in sorted(p_map.items(), key=lambda x: x[1], reverse=True):
                    if "현재가" in k:
                        st.markdown(f"### {k}: {v:,.0f} <span style='font-size:15px; color:gray;'>(비중: {m_ratio:.2f}%)</span>", unsafe_allow_html=True)
                    else: st.write(f"{k}: **{v:,.0f}** ({((v/curr_price)-1)*100:+.2f}%)")
            with c2:
                st.subheader(f"🔮 예측 (일봉+1, 주봉+{remain_days})")
                f_map = {f"{k}예측": float(d_bands[k].iloc[-1] + (d_bands[k].iloc[-1] - d_bands[k].iloc[-2])) for k in d_bands}
                f_map.update({f"{k}예측": float(w_bands[k].iloc[-1] + (w_bands[k].iloc[-1] - w_bands[k].iloc[-2])) for k in w_bands})
                f_map["🚩 현재가"] = curr_price
                for k, v in sorted(f_map.items(), key=lambda x: x[1], reverse=True):
                    if "현재가" in k: st.markdown(f"### {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({((v/curr_price)-1)*100:+.2f}%)")
