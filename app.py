import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

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
    target = data['Close']
    ma = target.rolling(window=20).mean()
    std = target.rolling(window=20).std()
    res = {f"{type_name} 중심": ma}
    for s in [2.0, 1.6, 1.0]:
        res[f"{type_name} {s}상"] = ma + (std * s)
        res[f"{type_name} {s}하"] = ma - (std * s)
    return res

# --- 메인 로직 ---
current_total_cap, exclude_caps_sum = get_market_baseline()
adjusted_base_cap = current_total_cap - exclude_caps_sum

tabs = st.tabs(list(STOCKS.keys()))

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        d_raw = get_clean_data(ticker, "200d", "1d")

        if d_raw is not None:
            # 주봉 데이터 100% 일봉 기반 생성
            w_raw = d_raw.resample('W-MON').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'
            }).dropna()

            d_bands = calculate_bands(d_raw, "일봉")
            w_bands = calculate_bands(w_raw, "주봉")
            
            # --- 차트 렌더링 생략 (기존 로직 동일하게 적용) ---
            DISPLAY_DAYS = 20 
            d_recent = d_raw.iloc[-DISPLAY_DAYS:]
            today_x = DISPLAY_DAYS - 1
            this_w_idx = w_raw.index[-1]
            days_passed = len(d_raw[d_raw.index >= this_w_idx])
            w_future_x = today_x + (5 - days_passed)
            d_future_x = today_x + 1
            max_x = max(d_future_x, w_future_x) + 3
            x_range = list(range(max_x + 5))
            date_labels = ["" for _ in x_range]
            for idx, d_idx in enumerate(d_recent.index):
                date_labels[idx] = d_idx.strftime('%m/%d')
            for idx in range(DISPLAY_DAYS, len(date_labels)):
                date_labels[idx] = f"+{idx - today_x}"

            fig = go.Figure()
            # (차트 trace 추가 부분은 이전 답변 코드와 동일하므로 지면상 중략합니다)
            # ... (차트 그리는 부분) ...
            st.plotly_chart(fig, use_container_width=True)

            # --- 백데이터 표 생성 파트 ---
            st.subheader("📋 백데이터 (최근 21일 포함 주 기준)")
            
            # 1. 기준 날짜 설정
            target_date = d_raw.index[-1] - timedelta(days=21)
            # 21일 전날이 포함된 주의 첫 영업일 찾기
            start_date = w_raw.index[w_raw.index <= target_date][-1]
            
            # 2. 표 데이터 구성
            table_df = pd.DataFrame(index=d_raw.loc[start_date:].index)
            table_df['종가'] = d_raw['Close']
            table_df['일봉중심'] = d_bands['일봉 중심']
            table_df['일봉2.0상'] = d_bands['일봉 2.0상']
            
            # 3. 주봉 데이터 매칭 (주의 첫 영업일에만 값 표시, 나머지는 빈칸)
            w_center_series = pd.Series(index=table_df.index, dtype=float)
            w_upper_series = pd.Series(index=table_df.index, dtype=float)
            
            for w_dt in w_raw.index:
                if w_dt in table_df.index:
                    w_center_series[w_dt] = w_bands['주봉 중심'][w_dt]
                    w_upper_series[w_dt] = w_bands['주봉 2.0상'][w_dt]
            
            table_df['주봉중심'] = w_center_series
            table_df['주봉2.0상'] = w_upper_series
            
            # 4. 출력용 포맷팅 (내림차순, 천단위 콤마, 소수점 제거)
            display_df = table_df.sort_index(ascending=False).copy()
            # 날짜 형식 변경
            display_df.index = display_df.index.strftime('%Y-%m-%d')
            
            # 소수점 반올림 및 천단위 콤마 (값이 없는 경우 대비)
            for col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
            
            st.table(display_df)
