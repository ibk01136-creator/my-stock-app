import streamlit as st
import yfinance as yf

st.title("📈 주식 감시 도우미")

# 원하는 종목 추가 (이름: 티커)
stocks = {
    "삼성전자": "005930.KS",
    "현대차": "005380.KS",
    "네이버": "035420.KS"
}

if st.button('오늘의 감시가 계산'):
    for name, ticker in stocks.items():
        # 데이터 가져오기
        data = yf.download(ticker, period="60d")
        
        # 20일 이동평균선 계산
        ma20 = data['Close'].rolling(window=20).mean().iloc[-1]
        current_price = data['Close'].iloc[-1]
        
        # 결과 표시
        st.subheader(f"📍 {name}")
        st.write(f"현재가: {current_price:,.0f}원")
        st.write(f"**감시가(20일선): {ma20:,.0f}원**")
        st.divider()
