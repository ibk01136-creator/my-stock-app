import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="변동성 전략 시뮬레이터", layout="wide")

STOCKS = {
    "SK하이닉스": "000660.KS", "삼성전자": "005930.KS", "LIG디펜스": "079550.KS",
    "삼성SDI": "006400.KS", "두산에너빌리티": "034020.KS", "엘앤에프": "066970.KS",
    "삼성생명": "032830.KS", "SK스퀘어": "402340.KS", "삼성전기": "009150.KS",
    "HD건설기계": "267270.KS", "HD일렉트릭": "267260.KS", "한화": "000880.KS",
    "삼성중공업": "010140.KS", "삼성E&A": "028050.KS", "하나금융지주": "086790.KS"
}

EXCLUDE_STOCKS = ["삼성전자", "SK하이닉스"]

def get_shares_dynamic(ticker):
    try:
        t = yf.Ticker(ticker)
        shares = t.fast_info.get('shares_outstanding')
        if shares and shares > 0: return float(shares)
        shares = t.info.get('sharesOutstanding')
        if shares and shares > 0: return float(shares)
    except:
        pass
    return 0.0

def get_clean_data(ticker, period, interval):
    data = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if data.empty: return None
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data

def calculate_bands(data, type_name):
    tp = (data['High'] + data['Low'] + data['Close']) / 3
    ma = tp.rolling(window=20).mean()
    std = tp.rolling(window=20).std()
    res = {f"{type_name} 중심": ma}
    # 표준편차별 밴드 생성
    for s in [2.0, 1.6, 1.0]:
        res[f"{type_name} {s}상"] = ma + (std * s)
        res[f"{type_name} {s}하"] = ma - (std * s)
    return res

@st.cache_data(ttl=3600)
def get_market_baseline():
    total_cap = 5686_000_000_000_000 
    try:
        kospi = yf.download("^KS11", period="2d", interval="1m", progress=False)
        if not kospi.empty:
            curr_index = float(kospi['Close'].iloc[-1])
            total_cap = 5686_000_000_000_000 * (curr_index / 6936.99)
    except:
        pass

    ex_sum = 0.0
    for name in EXCLUDE_STOCKS:
        ticker = STOCKS[name]
        d = yf.download(ticker, period="2d", interval="1d", auto_adjust=True, progress=False)
        if not d.empty:
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
            price = float(d['Close'].iloc[-1])
            shares = get_shares_dynamic(ticker)
            ex_sum += (price * shares)
    
    return total_cap, ex_sum

current_total_cap, exclude_caps_sum = get_market_baseline()
adjusted_base_cap = current_total_cap - exclude_caps_sum

tabs = st.tabs(list(STOCKS.keys()))

# 색상 설정 (요청대로 2.0선과 1.0선 교체: 0번 인덱스가 2.0)
# 상단(c_up): 2.0(옅음) -> 1.6(중간) -> 1.0(진함)
# 하단(c_lo): 2.0(옅음) -> 1.6(중간) -> 1.0(진함)
C_UP = ['#FFCCCC', '#FF6666', '#FF0000'] 
C_LO = ['#CCCCFF', '#6666FF', '#0000FF']
STD_LIST = [2.0, 1.6, 1.0]

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        d_raw = get_clean_data(ticker, "100d", "1d")
        w_raw = get_clean_data(ticker, "2y", "1wk")
        
        if d_raw is not None and w_raw is not None:
            curr_price = float(d_raw['Close'].iloc[-1])
            shares = get_shares_dynamic(ticker)
            
            m_ratio = 0.0
            if shares > 0:
                m_cap = curr_price * shares
                if name in EXCLUDE_STOCKS:
                    m_ratio = (m_cap / current_total_cap) * 100
                    base_label = "전체 코스피"
                else:
                    denominator = adjusted_base_cap if adjusted_base_cap > 0 else current_total_cap
                    m_ratio = (m_cap / denominator) * 100
                    base_label = "삼전/하닉 제외 코스피"
            
            d_bands = calculate_bands(d_raw, "일봉")
            w_bands = calculate_bands(w_raw, "주봉")
            
            recent_idx = d_raw.index[-20:]
            today_x = 19
            
            this_w_date = w_raw.index[-1]
            prev_w_date = w_raw.index[-2]
            step_days = len(d_raw[(d_raw.index > prev_w_date) & (d_raw.index <= this_w_date)])
            
            try:
                w_start_x_in_d = d_raw.index.get_loc(this_w_date) - (len(d_raw) - 20)
            except:
                w_start_x_in_d = 0
            
            w_end_x = w_start_x_in_d + step_days
            d_pred_x = today_x + 1

            x_range = list(range(40))
            date_labels = ["" for _ in range(40)]
            for idx, d in enumerate(recent_idx): date_labels[idx] = d.strftime('%m/%d')
            for idx in range(20, 40): date_labels[idx] = f"+{idx - today_x}"

            fig = go.Figure()
            upper_vals, w_center_vals = [], []

            # --- 렌더링 함수 정의 (중복 방지) ---
            def add_band_traces(bands, is_weekly=False):
                for key, data_series in bands.items():
                    if '중심' in key:
                        color = '#BA55D3' if is_weekly else 'purple'
                    else:
                        std_val = float(key.split()[1][:-1])
                        c_idx = STD_LIST.index(std_val)
                        color = C_UP[c_idx] if '상' in key else C_LO[c_idx]
                    
                    if not is_weekly:
                        y_vals = data_series.iloc[-20:].tolist()
                        fig.add_trace(go.Scatter(x=list(range(20)), y=y_vals, name=key, line=dict(color=color, width=1.5 if '중심' in key else 1)))
                        slope = float(data_series.iloc[-1] - data_series.iloc[-2])
                        pred_y = float(y_vals[-1] + slope)
                        fig.add_trace(go.Scatter(x=[today_x, d_pred_x], y=[y_vals[-1], pred_y], line=dict(color=color, width=1, dash='dot'), showlegend=False))
                        if '상' in key or '중심' in key: 
                            upper_vals.extend(y_vals); upper_vals.append(pred_y)
                    else:
                        w_sub = data_series[data_series.index <= this_w_date]
                        w_x = [d_raw.index.get_loc(dt) - (len(d_raw) - 20) for dt in w_sub.index if dt in d_raw.index]
                        w_x = [x for x in w_x if 0 <= x < 20]
                        if w_x:
                            vals = w_sub.values[-len(w_x):].tolist()
                            fig.add_trace(go.Scatter(x=w_x, y=vals, name=key, line=dict(color=color, width=1, dash='dashdot')))
                            w_slope = float(data_series.iloc[-1] - data_series.iloc[-2])
                            w_pred_y = float(vals[-1] + w_slope)
                            fig.add_trace(go.Scatter(x=[w_x[-1], w_end_x], y=[vals[-1], w_pred_y], line=dict(color=color, width=1, dash='dot'), showlegend=False))
                            if '상' in key or '중심' in key: 
                                upper_vals.extend(vals); upper_vals.append(w_pred_y)
                            if '중심' in key: 
                                w_center_vals.extend(vals); w_center_vals.append(w_pred_y)

            add_band_traces(d_bands, is_weekly=False)
            add_band_traces(w_bands, is_weekly=True)

            curr_close_v = d_raw['Close'].iloc[-20:].tolist()
            fig.add_trace(go.Scatter(x=list(range(20)), y=curr_close_v, name='현재가', line=dict(color='black', width=2.5)))
            
            y_min = min(curr_close_v + (w_center_vals if w_center_vals else curr_close_v)) * 0.99
            y_max = max(upper_vals + curr_close_v) * 1.01
            
            # --- 다크모드 무시 설정 (흰색 배경 고정) ---
            fig.update_layout(
                paper_bgcolor='white',
                plot_bgcolor='white',
                font=dict(color='black'),
                height=550, 
                margin=dict(l=5, r=5, t=30, b=5),
                xaxis=dict(
                    tickmode='array', tickvals=x_range, ticktext=date_labels, 
                    range=[0, max(d_pred_x, w_end_x) + 1],
                    gridcolor='lightgray', linecolor='black'
                ),
                yaxis=dict(
                    tickformat=",", range=[y_min, y_max],
                    gridcolor='lightgray', linecolor='black'
                ),
                hovermode='x unified', showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

            c1, c2 = st.columns(2)
            with c1:
                st.subheader(f"📊 금일 확정 ({base_label})")
                p_map = {k: float(d_bands[k].iloc[-1]) for k in d_bands}
                p_map.update({k: float(w_bands[k].iloc[-1]) for k in w_bands})
                p_map["🚩 현재가"] = curr_price
                for k, v in sorted(p_map.items(), key=lambda x: x[1], reverse=True):
                    if "현재가" in k:
                        st.markdown(f"### {k}: {v:,.0f} <span style='font-size:15px; color:gray;'>(비중: {m_ratio:.2f}%)</span>", unsafe_allow_html=True)
                    else:
                        st.write(f"{k}: **{v:,.0f}** ({((v/curr_price)-1)*100:+.2f}%)")
            with c2:
                st.subheader(f"🔮 미래 예측")
                f_map = {f"{k}예측": float(d_bands[k].iloc[-1] + (d_bands[k].iloc[-1] - d_bands[k].iloc[-2])) for k in d_bands}
                f_map.update({f"{k}예측": float(w_bands[k].iloc[-1] + (w_bands[k].iloc[-1] - w_bands[k].iloc[-2])) for k in w_bands})
                f_map["🚩 현재가"] = curr_price
                for k, v in sorted(f_map.items(), key=lambda x: x[1], reverse=True):
                    if "현재가" in k: st.markdown(f"### {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({((v/curr_price)-1)*100:+.2f}%)")
