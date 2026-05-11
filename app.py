import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 1. 설정
st.set_page_config(page_title="볼린저 비전", layout="wide")

STOCKS = {
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "SK스퀘어": "402340.KS",
    "두산에너빌리티": "034020.KS", "삼성전기": "009150.KS", "삼성생명": "032830.KS",
    "KB금융": "105560.KS", "삼성SDI": "006400.KS", "HD일렉트릭": "267260.KS",
    "LS일렉트릭": "010120.KS", "미래에셋증권": "006800.KS", "신한지주": "055550.KS",
    "포스코홀딩스": "005490.KS", "SK": "034730.KS", "하나금융지주": "086790.KS",
    "두산": "000150.KS", "삼성중공업": "010140.KS", "현대로템": "064350.KS",
    "LG전자": "066570.KS", "HD현대": "267250.KS", "LIG디펜스": "079550.KS",
    "SK텔레콤": "017670.KS", "KT&G": "033780.KS", "대한전선": "001440.KS",
    "삼성E&A": "028050.KS", "한화": "000880.KS", "HD건설기계": "267270.KS",
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
        kospi = yf.download("^KS11", period="2d", interval="1m", progress=False)
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
            
            DISPLAY_DAYS = 20 
            d_recent = d_raw.iloc[-DISPLAY_DAYS:]
            today_x = DISPLAY_DAYS - 1
            
            # 주봉 간격 및 미래 위치 계산 (수정됨)
            this_w_idx = w_raw.index[-1]
            prev_w_idx = w_raw.index[-2]
            # 지난 주 첫 영업일로부터 오늘까지의 실제 일봉 개수(영업일) 계산
            actual_gap = len(d_raw[(d_raw.index >= prev_w_idx) & (d_raw.index < this_w_idx)])
            if actual_gap == 0: actual_gap = 5
            
            # 미래 위치: 오늘(today_x) + (한 주 영업일 - 지난 주 첫날부터 오늘까지 경과일)
            days_passed_in_week = len(d_raw[d_raw.index >= this_w_idx])
            w_future_x = today_x + (actual_gap - days_passed_in_week + 1)
            d_future_x = today_x + 1

            # X축 라벨링
            max_x = max(d_future_x, w_future_x) + 3
            x_range = list(range(max_x + 5))
            date_labels = ["" for _ in x_range]
            for idx, d_idx in enumerate(d_recent.index):
                date_labels[idx] = d_idx.strftime('%m/%d')
            for idx in range(DISPLAY_DAYS, len(date_labels)):
                date_labels[idx] = f"+{idx - today_x}"

            fig = go.Figure()
            c_up, c_lo = ['#FFCCCC', '#FF6666', '#FF0000'], ['#CCCCFF', '#6666FF', '#0000FF']
            top_check, bottom_check = [], []

            # 1. 일봉 렌더링
            for key in d_bands:
                std_val = float(key.split()[1][:-1]) if '중심' not in key else 0
                color = 'purple' if '중심' in key else (c_up[[2.0, 1.6, 1.0].index(std_val)] if '상' in key else c_lo[[2.0, 1.6, 1.0].index(std_val)])
                y_vals = d_bands[key].iloc[-DISPLAY_DAYS:].tolist()
                fig.add_trace(go.Scatter(x=list(range(DISPLAY_DAYS)), y=y_vals, name=key, line=dict(color=color, width=1)))
                
                slope = float(d_bands[key].iloc[-1] - d_bands[key].iloc[-2])
                pred_y = float(y_vals[-1] + slope)
                fig.add_trace(go.Scatter(x=[today_x, d_future_x], y=[y_vals[-1], pred_y], line=dict(color=color, width=1, dash='dot'), showlegend=False))
                top_check.extend(y_vals + [pred_y])

            # 2. 주봉 렌더링 (계단식 제거 및 기울기 수정)
            for key in w_bands:
                std_val = float(key.split()[1][:-1]) if '중심' not in key else 0
                color = '#BA55D3' if '중심' in key else (c_up[[2.0, 1.6, 1.0].index(std_val)] if '상' in key else c_lo[[2.0, 1.6, 1.0].index(std_val)])
                
                w_x, w_y = [], []
                for w_dt, val in w_bands[key].items():
                    if w_dt in d_recent.index:
                        w_x.append(d_recent.index.get_loc(w_dt))
                        w_y.append(val)
                
                # 이번 주 데이터가 인덱스에 없어도 마지막 값은 오늘 위치에 표시
                if not w_x or (this_w_idx not in d_recent.index and this_w_idx > d_recent.index[-1]):
                     w_x.append(today_x)
                     w_y.append(w_bands[key].iloc[-1])

                if w_x:
                    fig.add_trace(go.Scatter(x=w_x, y=w_y, name=key, mode='lines+markers', line=dict(color=color, width=1.3, dash='dashdot'), marker=dict(size=4)))
                    
                    # 기울기 유지 예측
                    w_slope = float(w_bands[key].iloc[-1] - w_bands[key].iloc[-2])
                    w_pred_y = float(w_y[-1] + w_slope)
                    fig.add_trace(go.Scatter(x=[w_x[-1], w_future_x], y=[w_y[-1], w_pred_y], line=dict(color=color, width=1.3, dash='dot'), showlegend=False))
                    
                    top_check.extend(w_y + [w_pred_y])
                    if "중심" in key: bottom_check.extend(w_y + [w_pred_y])

            # 3. 현재가 선
            curr_close_v = d_recent['Close'].tolist()
            fig.add_trace(go.Scatter(x=list(range(DISPLAY_DAYS)), y=curr_close_v, name='현재가', line=dict(color='black', width=2)))
            top_check.extend(curr_close_v)
            bottom_check.extend(curr_close_v)

            y_min = min([v for v in bottom_check if pd.notna(v)]) * 0.99
            y_max = max([v for v in top_check if pd.notna(v)]) * 1.01
            
            fig.update_layout(height=500, margin=dict(l=5, r=5, t=30, b=5),
                xaxis=dict(tickmode='array', tickvals=x_range, ticktext=date_labels, range=[0, max_x]),
                yaxis=dict(tickformat=",", range=[y_min, y_max]), 
                hovermode='x unified', showlegend=False)
            
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

            # 하단 정보
            c1, c2 = st.columns(2)
            with c1:
                st.subheader(f"📊 금일 확정 ({base_label} 대비)")
                p_map = {k: float(d_bands[k].iloc[-1]) for k in d_bands}
                p_map.update({k: float(w_bands[k].iloc[-1]) for k in w_bands})
                p_map["🚩 현재가"] = curr_price
                for k, v in sorted(p_map.items(), key=lambda x: x[1], reverse=True):
                    if "현재가" in k: st.markdown(f"### {k}: {v:,.0f} <span style='font-size:15px; color:gray;'>(비중: {m_ratio:.2f}%)</span>", unsafe_allow_html=True)
                    else: st.write(f"{k}: **{v:,.0f}** ({((v/curr_price)-1)*100:+.2f}%)")
            with c2:
                st.subheader(f"🔮 미래 예측")
                f_map = {f"{k}예측": float(d_bands[k].iloc[-1] + (d_bands[k].iloc[-1] - d_bands[k].iloc[-2])) for k in d_bands}
                f_map.update({f"{k}예측": float(w_bands[k].iloc[-1] + (w_bands[k].iloc[-1] - w_bands[k].iloc[-2])) for k in w_bands})
                f_map["🚩 현재가"] = curr_price
                for k, v in sorted(f_map.items(), key=lambda x: x[1], reverse=True):
                    if "현재가" in k: st.markdown(f"### {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({((v/curr_price)-1)*100:+.2f}%)")
