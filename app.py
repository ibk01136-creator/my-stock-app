import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 1. 설정
st.set_page_config(page_title="변동성 전략 시뮬레이터", layout="wide")

STOCKS = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "SK스퀘어": "402340.KS",
    "두산에너빌리티": "034020.KS",
    "삼성전기": "009150.KS",
    "삼성생명": "032830.KS",
    "KB금융": "105560.KS",
    "삼성SDI": "006400.KS",
    "HD일렉트릭": "267260.KS",
    "LS일렉트릭": "010120.KS",
    "미래에셋증권": "006800.KS",
    "신한지주": "055550.KS",
    "포스코홀딩스": "005490.KS",
    "SK": "034730.KS",
    "하나금융지주": "086790.KS",
    "두산": "000150.KS",
    "삼성중공업": "010140.KS",
    "현대로템": "064350.KS",
    "LG전자": "066570.KS",
    "HD현대": "267250.KS",
    "LIG디펜스": "079550.KS",
    "SK텔레콤": "017670.KS",
    "KT&G": "033780.KS",
    "대한전선": "001440.KS",
    "삼성E&A": "028050.KS",
    "한화": "000880.KS",
    "HD건설기계": "267270.KS",
    "엘앤에프": "066970.KS"
}
EXCLUDE_STOCKS = ["삼성전자", "SK하이닉스"]

# 2. 데이터 관련 함수
@st.cache_data(ttl=3600)
def get_shares_dynamic(ticker):
    try:
        t = yf.Ticker(ticker)
        shares = t.fast_info.get('shares_outstanding')
        if not shares: shares = t.info.get('sharesOutstanding')
        return float(shares) if shares else 0.0
    except: return 0.0

@st.cache_data(ttl=300)
def get_clean_data(ticker, period, interval):
    try:
        data = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
        if data.empty: return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data
    except: return None

@st.cache_data(ttl=3600)
def get_market_baseline():
    total_cap = 5686_000_000_000_000 
    try:
        kospi = yf.download("^KS11", period="5d", interval="1m", progress=False)
        if not kospi.empty:
            curr_index = float(kospi['Close'].iloc[-1])
            total_cap = 5686_000_000_000_000 * (curr_index / 6936.99)
    except: pass

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

def calculate_bands(data, type_name):
    tp = (data['High'] + data['Low'] + data['Close']) / 3
    ma = tp.rolling(window=20).mean()
    std = tp.rolling(window=20).std()
    res = {f"{type_name} 중심": ma}
    for s in [2.0, 1.6, 1.0]:
        res[f"{type_name} {s}상"] = ma + (std * s)
        res[f"{type_name} {s}하"] = ma - (std * s)
    return res

# 3. 메인 로직 시작
current_total_cap, exclude_caps_sum = get_market_baseline()
adjusted_base_cap = current_total_cap - exclude_caps_sum

tabs = st.tabs(list(STOCKS.keys()))

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        d_raw = get_clean_data(ticker, "100d", "1d")
        w_raw = get_clean_data(ticker, "2y", "1wk")

        if d_raw is not None and w_raw is not None:
            curr_price = float(d_raw['Close'].iloc[-1])
            shares = get_shares_dynamic(ticker)
            
            # --- 변수 초기화 위치 수정 (에러 방지) ---
            m_ratio = 0.0
            base_label = "데이터 없음" 
            
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
            
            # 영업일 계산 안전장치
            step_df = d_raw[(d_raw.index > prev_w_date) & (d_raw.index <= this_w_date)]
            step_days = len(step_df) if len(step_df) > 0 else 5
            
            w_end_x = today_x + step_days
            d_pred_x = today_x + 1

            x_range = list(range(40))
            date_labels = ["" for _ in range(40)]
            for idx, d in enumerate(recent_idx): date_labels[idx] = d.strftime('%m/%d')
            for idx in range(20, 40): date_labels[idx] = f"+{idx - today_x}"

            fig = go.Figure()
            c_up, c_lo = ['#FFCCCC', '#FF6666', '#FF0000'], ['#CCCCFF', '#6666FF', '#0000FF']
            upper_vals, w_center_vals = [], []

            # 일봉 렌더링
            for key in d_bands:
                std_val = float(key.split()[1][:-1]) if '중심' not in key else 0
                color = 'purple' if '중심' in key else (c_up[[2.0, 1.6, 1.0].index(std_val)] if '상' in key else c_lo[[2.0, 1.6, 1.0].index(std_val)])
                y_vals = d_bands[key].iloc[-20:].tolist()
                fig.add_trace(go.Scatter(x=list(range(20)), y=y_vals, name=key, line=dict(color=color, width=1)))
                
                slope = float(d_bands[key].iloc[-1] - d_bands[key].iloc[-2])
                pred_y = float(y_vals[-1] + slope)
                fig.add_trace(go.Scatter(x=[today_x, d_pred_x], y=[y_vals[-1], pred_y], line=dict(color=color, width=1, dash='dot'), showlegend=False))
                if '상' in key or '중심' in key: upper_vals.extend(y_vals); upper_vals.append(pred_y)

            # 주봉 렌더링
            for key in w_bands:
                std_val = float(key.split()[1][:-1]) if '중심' not in key else 0
                color = '#BA55D3' if '중심' in key else (c_up[[2.0, 1.6, 1.0].index(std_val)] if '상' in key else c_lo[[2.0, 1.6, 1.0].index(std_val)])
                w_sub = w_bands[key][w_bands[key].index <= this_w_date]
                
                # 인덱스 매칭 안전장치
                w_x = []
                for dt in w_sub.index:
                    if dt in d_raw.index:
                        try:
                            pos = d_raw.index.get_loc(dt) - (len(d_raw) - 20)
                            if 0 <= pos < 20: w_x.append(pos)
                        except: pass
                
                if w_x:
                    vals = w_sub.values[-len(w_x):].tolist()
                    fig.add_trace(go.Scatter(x=w_x, y=vals, name=key, line=dict(color=color, width=1, dash='dashdot')))
                    w_slope = float(w_bands[key].iloc[-1] - w_bands[key].iloc[-2])
                    w_pred_y = float(vals[-1] + w_slope)
                    fig.add_trace(go.Scatter(x=[w_x[-1], w_end_x], y=[vals[-1], w_pred_y], line=dict(color=color, width=1, dash='dot'), showlegend=False))
                    if '상' in key or '중심' in key: upper_vals.extend(vals); upper_vals.append(w_pred_y)
                    if '중심' in key: w_center_vals.extend(vals); w_center_vals.append(w_pred_y)

            curr_close_v = d_raw['Close'].iloc[-20:].tolist()
            fig.add_trace(go.Scatter(x=list(range(20)), y=curr_close_v, name='현재가', line=dict(color='black', width=2)))
            
            y_min = min(curr_close_v + (w_center_vals if w_center_vals else curr_close_v)) * 0.98
            y_max = max(upper_vals + curr_close_v) * 1.02
            
            fig.update_layout(height=500, margin=dict(l=5, r=5, t=30, b=5),
                xaxis=dict(tickmode='array', tickvals=x_range, ticktext=date_labels, range=[0, max(d_pred_x, w_end_x) + 1]),
                yaxis=dict(tickformat=",", range=[y_min, y_max]), hovermode='x unified', showlegend=False)
            
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

            c1, c2 = st.columns(2)
            with c1:
                st.subheader(f"📊 금일 확정 ({base_label} 대비)")
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
        else:
            st.error(f"{name} 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
