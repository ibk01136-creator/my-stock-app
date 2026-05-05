import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="변동성 전략 시뮬레이터", layout="wide")

STOCKS = {
    "SK하이닉스": "000660.KS", "삼성전자": "005930.KS", "LIG디펜스": "079550.KS",
    "삼성SDI": "006400.KS", "두산에너빌리티": "034020.KS", "엘앤에프": "066970.KS",
    "삼성생명": "032830.KS", "SK스퀘어": "402340.KS", "삼성전기": "009150.KS",
    "HD건설기계": "267270.KS", "HD일렉트릭": "267260.KS", "한화": "000880.KS",
    "삼성중공업": "010140.KS", "삼성E&A": "028050.KS", "하나금융지주": "086790.KS"
}

def get_shares_dynamic(ticker):
    """실시간 주식수만 시도 (실패 시 0 반환)"""
    try:
        t = yf.Ticker(ticker)
        # fast_info가 가장 효율적임
        s = t.fast_info.get('shares_outstanding')
        if s: return float(s)
        # 차선책 info
        s = t.info.get('sharesOutstanding')
        if s: return float(s)
    except:
        pass
    return 0.0

@st.cache_data(ttl=3600)
def get_market_context():
    """삼성전자/SK하이닉스 시총을 동적으로 계산하여 제외 분모 생성"""
    try:
        # 코스피 지수 기반 전체 시총 추정
        kospi = yf.download("^KS11", period="1d", progress=False)
        total_kospi = 5686_000_000_000_000
        if not kospi.empty:
            total_kospi = 5686_000_000_000_000 * (float(kospi['Close'].iloc[-1]) / 6936.99)
        
        # 삼성전자 시총 (동적)
        ss_p = float(yf.download("005930.KS", period="1d", progress=False)['Close'].iloc[-1])
        ss_s = get_shares_dynamic("005930.KS")
        ss_cap = ss_p * ss_s if ss_s > 0 else 0
        
        # SK하이닉스 시총 (동적)
        sk_p = float(yf.download("000660.KS", period="1d", progress=False)['Close'].iloc[-1])
        sk_s = get_shares_dynamic("000660.KS")
        sk_cap = sk_p * sk_s if sk_s > 0 else 0
        
        return total_kospi, ss_cap, sk_cap
    except:
        return 5686_000_000_000_000, 0, 0

# 분모 계산 로직
TOTAL_KOSPI, SS_CAP, SK_CAP = get_market_context()
# 삼전/하닉 데이터를 못 불러오면 분모에서 빼지 않음 (판단 오류 방지)
OTHERS_DENOMINATOR = TOTAL_KOSPI - (SS_CAP + SK_CAP)

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
            is_giant = ticker in ["005930.KS", "000660.KS"]
            
            if shares > 0:
                m_cap = curr_price * shares
                # 삼전/하닉은 전체 대비, 나머지는 제외 시총 대비
                denominator = TOTAL_KOSPI if is_giant else OTHERS_DENOMINATOR
                m_ratio = (m_cap / denominator) * 100 if denominator > 0 else 0

            d_bands = calculate_bands(d_raw, "일봉")
            w_bands = calculate_bands(w_raw, "주봉")
            recent_idx = d_raw.index[-20:]
            
            # 차트 구성
            fig = go.Figure()
            c_up, c_lo = ['#FFCCCC', '#FF6666', '#FF0000'], ['#CCCCFF', '#6666FF', '#0000FF']
            
            for key in d_bands:
                std_v = float(key.split()[1][:-1]) if '중심' not in key else 0
                color = 'purple' if '중심' in key else (c_up[[2.0, 1.6, 1.0].index(std_v)] if '상' in key else c_lo[[2.0, 1.6, 1.0].index(std_v)])
                fig.add_trace(go.Scatter(x=list(range(20)), y=d_bands[key].iloc[-20:].tolist(), name=key, line=dict(color=color, width=1)))

            for key in w_bands:
                std_v = float(key.split()[1][:-1]) if '중심' not in key else 0
                color = '#BA55D3' if '중심' in key else (c_up[[2.0, 1.6, 1.0].index(std_v)] if '상' in key else c_lo[[2.0, 1.6, 1.0].index(std_v)])
                w_sub = w_bands[key][w_bands[key].index >= recent_idx[0]]
                w_x = [d_raw.index.get_loc(dt) - (len(d_raw) - 20) for dt in w_sub.index if dt in d_raw.index]
                if w_x:
                    fig.add_trace(go.Scatter(x=w_x, y=w_sub.values[:len(w_x)].tolist(), name=key, line=dict(color=color, width=1, dash='dashdot')))

            fig.add_trace(go.Scatter(x=list(range(20)), y=d_raw['Close'].iloc[-20:].tolist(), name='현재가', line=dict(color='black', width=2)))
            fig.update_layout(height=450, margin=dict(l=5, r=5, t=30, b=5), hovermode='x unified', showlegend=False)
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
                        label = "전체비중" if is_giant else "제외비중"
                        # 주식수를 못 불러와서 m_ratio가 0인 경우 명확히 표시
                        ratio_text = f"{m_ratio:.2f}%" if m_ratio > 0 else "불러오기 실패 (판단불가)"
                        st.markdown(f"### {k}: {v:,.0f} <span style='font-size:15px; color:gray;'>({label}: {ratio_text})</span>", unsafe_allow_html=True)
                    else:
                        st.write(f"{k}: **{v:,.0f}** ({((v/curr_price)-1)*100:+.2f}%)")
            with c2:
                st.subheader("🔮 예측")
                # (예측 로직)
