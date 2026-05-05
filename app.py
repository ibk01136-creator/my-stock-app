import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="변동성 전략 시뮬레이터", layout="wide")

# 엘앤에프 티커를 .KS로 수정
STOCKS = {
    "SK하이닉스": "000660.KS", "삼성전자": "005930.KS", "LIG디펜스": "079550.KS",
    "삼성SDI": "006400.KS", "두산에너빌리티": "034020.KS", "엘앤에프": "066970.KS",
    "삼성생명": "032830.KS", "SK스퀘어": "402340.KS", "삼성전기": "009150.KS",
    "HD건설기계": "267270.KS", "HD일렉트릭": "267260.KS", "한화": "000880.KS",
    "삼성중공업": "010140.KS", "삼성E&A": "028050.KS", "하나금융지주": "086790.KS"
}

def get_shares_dynamic(ticker):
    """실시간 주식수 획득"""
    try:
        t = yf.Ticker(ticker)
        shares = t.fast_info.get('shares_outstanding')
        return float(shares) if shares else 0.0
    except:
        return 0.0

def get_clean_data(ticker, period, interval):
    try:
        data = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
        if data.empty: return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data
    except:
        return None

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
def get_market_caps():
    """분모용 시총 데이터 계산 (전체, 삼전, 하닉)"""
    try:
        kospi = yf.download("^KS11", period="1d", interval="1m", progress=False)
        total_cap = 5686_000_000_000_000 
        if not kospi.empty:
            curr_idx = float(kospi['Close'].iloc[-1])
            total_cap = 5686_000_000_000_000 * (curr_idx / 6936.99)
            
        ss_p = float(yf.download("005930.KS", period="1d", progress=False)['Close'].iloc[-1])
        ss_s = get_shares_dynamic("005930.KS")
        sk_p = float(yf.download("000660.KS", period="1d", progress=False)['Close'].iloc[-1])
        sk_s = get_shares_dynamic("000660.KS")
        
        return total_cap, (ss_p * ss_s), (sk_p * sk_s)
    except:
        return 5686_000_000_000_000, 0, 0

total_kospi, ss_cap, sk_cap = get_market_caps()
others_denominator = total_kospi - (ss_cap + sk_cap)

tabs = st.tabs(list(STOCKS.keys()))

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        d_raw = get_clean_data(ticker, "100d", "1d")
        w_raw = get_clean_data(ticker, "2y", "1wk")
        
        if d_raw is not None and w_raw is not None:
            curr_price = float(d_raw['Close'].iloc[-1])
            shares = get_shares_dynamic(ticker)
            
            # 비중 계산
            m_ratio = 0.0
            if shares > 0:
                m_cap = curr_price * shares
                if ticker in ["005930.KS", "000660.KS"]:
                    m_ratio = (m_cap / total_kospi) * 100
                else:
                    m_ratio = (m_cap / others_denominator) * 100 if others_denominator > 0 else 0.0

            d_bands = calculate_bands(d_raw, "일봉")
            w_bands = calculate_bands(w_raw, "주봉")
            recent_idx = d_raw.index[-20:]
            today_x = 19
            
            # 차트 그리기 시작
            fig = go.Figure()
            c_up, c_lo = ['#FFCCCC', '#FF6666', '#FF0000'], ['#CCCCFF', '#6666FF', '#0000FF']
            upper_vals, w_center_vals = [], []

            for key in d_bands:
                std_val = float(key.split()[1][:-1]) if '중심' not in key else 0
                color = 'purple' if '중심' in key else (c_up[[2.0, 1.6, 1.0].index(std_val)] if '상' in key else c_lo[[2.0, 1.6, 1.0].index(std_val)])
                y_vals = d_bands[key].iloc[-20:].tolist()
                fig.add_trace(go.Scatter(x=list(range(20)), y=y_vals, name=key, line=dict(color=color, width=1)))
                if '상' in key or '중심' in key: upper_vals.extend(y_vals)

            for key in w_bands:
                std_val = float(key.split()[1][:-1]) if '중심' not in key else 0
                color = '#BA55D3' if '중심' in key else (c_up[[2.0, 1.6, 1.0].index(std_val)] if '상' in key else c_lo[[2.0, 1.6, 1.0].index(std_val)])
                w_sub = w_bands[key][w_bands[key].index >= recent_idx[0]]
                w_x = [d_raw.index.get_loc(dt) - (len(d_raw) - 20) for dt in w_sub.index if dt in d_raw.index]
                if w_x:
                    vals = w_sub.values[:len(w_x)].tolist()
                    fig.add_trace(go.Scatter(x=w_x, y=vals, name=key, line=dict(color=color, width=1, dash='dashdot')))
                    if '중심' in key: w_center_vals.extend(vals)

            fig.add_trace(go.Scatter(x=list(range(20)), y=d_raw['Close'].iloc[-20:].tolist(), name='현재가', line=dict(color='black', width=2)))
            fig.update_layout(height=450, margin=dict(l=5, r=5, t=30, b=5), hovermode='x unified', showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

            # 하단 정보
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📊 금일 확정")
                p_map = {k: float(d_bands[k].iloc[-1]) for k in d_bands}
                p_map.update({k: float(w_bands[k].iloc[-1]) for k in w_bands})
                p_map["🚩 현재가"] = curr_price
                
                for k, v in sorted(p_map.items(), key=lambda x: x[1], reverse=True):
                    if "현재가" in k:
                        label = "전체비중" if ticker in ["005930.KS", "000660.KS"] else "제외비중"
                        ratio_text = f"{m_ratio:.2f}%" if m_ratio > 0 else "불러오기 실패"
                        st.markdown(f"### {k}: {v:,.0f} <span style='font-size:14px; color:gray;'>({label}: {ratio_text})</span>", unsafe_allow_html=True)
                    else:
                        st.write(f"{k}: **{v:,.0f}** ({((v/curr_price)-1)*100:+.2f}%)")
            with c2:
                st.subheader("🔮 예측")
                # (예측 로직 생략, 기존과 동일)
                st.write("차트 상단의 추세선을 확인하세요.")
