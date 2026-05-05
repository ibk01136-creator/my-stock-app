import streamlit as st
import yfinance as yf

st.set_page_config(page_title="주식 감시 도우미", layout="centered")
st.title("📈 주식 감시 도우미")

# 종목 리스트
stocks = {
    "삼성전자": "005930.KS",
    "현대차": "005380.KS",
    "네이버": "035420.KS"
}

if st.button('오늘의 감시가 계산'):
    for name, ticker in stocks.items():
        # 데이터를 가장 단순한 형태로 가져오기
        data = yf.download(ticker, period="60d")
        
        if not data.empty:
            # 최근 업데이트 대응: Close 열만 추출하여 숫자로 변환
            close_series = data['Close'].squeeze()
            
            # 20일 이동평균선 계산
            ma20_series = close_series.rolling(window=20).mean()
            
            # 가장 최신 값(숫자)만 추출
            curr_price = float(close_series.iloc[-1])
            ma20_price = float(ma20_series.iloc[-1])
            
            st.subheader(f"📍 {name}")
            col1, col2 = st.columns(2)
            col1.metric("현재가", f"{curr_price:,.0f}원")
            col2.metric("감시가(20일선)", f"{ma20_price:,.0f}원", f"{curr_price - ma20_price:,.0f}원")
            st.divider()
        else:
            st.error(f"{name} 데이터를 불러오지 못했습니다.")
