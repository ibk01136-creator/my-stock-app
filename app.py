import streamlit as st
import yfinance as yf

st.title("📈 주식 감시 도우미")

# 종목 리스트
stocks = {
    "삼성전자": "005930.KS",
    "현대차": "005380.KS",
    "네이버": "035420.KS"
}

if st.button('오늘의 감시가 계산'):
    for name, ticker in stocks.items():
        # auto_adjust=True를 넣어 가격 데이터를 단일 형태로 고정
        data = yf.download(ticker, period="60d", auto_adjust=True)
        
        if not data.empty:
            # 20일 이동평균선 계산
            # 최근 yfinance 업데이트 대응을 위해 .iloc[:, 0] 등으로 열을 확실히 지정
            close_prices = data['Close']
            ma20_series = close_prices.rolling(window=20).mean()
            
            curr_price = float(close_prices.iloc[-1])
            ma20_price = float(ma20_series.iloc[-1])
            
            st.subheader(f"📍 {name}")
            col1, col2 = st.columns(2)
            col1.metric("현재가", f"{curr_price:,.0f}원")
            col2.metric("감시가(20일선)", f"{ma20_price:,.0f}원", f"{curr_price - ma20_price:,.0f}원")
            st.divider()
        else:
            st.error(f"{name} 데이터를 불러오지 못했습니다.")
