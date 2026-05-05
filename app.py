import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="주식 변동성 전략 시뮬레이터", layout="wide")

STOCKS = {"SK하이닉스": "000660.KS", "삼성전자": "005930.KS"}
STD_LIST = [2.0, 1.6, 1.0]

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
    for s in STD_LIST:
        res[f"{type_name} {s}상"] = ma + (std * s)
        res[f"{type_name} {s}하"] = ma - (std * s)
    return res

tabs = st.tabs(list(STOCKS.keys()))

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        d_raw = get_clean_data(ticker, "100d", "1d")
        w_raw = get_clean_data(ticker, "2y", "1wk")
        
        if d_raw is not None and w_raw is not None:
            d_bands = calculate_bands(d_raw, "일봉")
            w_bands = calculate_bands(w_raw, "주봉")
            
            # 1. 차트 데이터 구성 (과거 20일)
            recent_idx = d_raw.index[-20:]
            chart_df = pd.DataFrame(index=recent_idx)
            chart_df['현재가'] = d_raw['Close'].iloc[-20:]
            for k, v in d_bands.items(): chart_df[k] = v.iloc[-20:]
            
            # 주봉: 첫 영업일만 남기고 나머지는 NaN (선 연결을 위해)
            for k, v in w_bands.items():
                w_val = v.reindex(recent_idx) # NaN으로 비워둠
                # 주의 첫 영업일(여기서는 데이터가 존재하는 날짜)에만 값 할당
                common_dates = v.index.intersection(recent_idx)
                w_val.loc[common_dates] = v.loc[common_dates]
                chart_df[k] = w_val

            # 2. 미래 1일 예측 (연결 끊김 방지)
            last_date = recent_idx[-1]
            next_date = last_date + pd.Timedelta(days=1)
            forecast_row = pd.Series(name=next_date, dtype='float64')
            
            for col in chart_df.columns:
                if col == '현재가': continue
                # 마지막 두 값으로 기울기 계산
                vals = chart_df[col].dropna()
                if len(vals) >= 2:
                    diff = vals.iloc[-1] - vals.iloc[-2]
                    forecast_row[f"{col}예측"] = vals.iloc[-1] + diff
            
            # 예측용 데이터프레임 (과거 마지막 행 포함하여 선 연결)
            combined_df = chart_df.copy()
            for col in forecast_row.index:
                combined_df.loc[next_date, col] = forecast_row[col]

            # 3. 차트 구현 (Y축 스케일 해결)
            plot_data = combined_df.reset_index().melt('index')
            plot_data['index'] = plot_data['index'].dt.strftime('%m/%d')
            
            y_min = float(combined_df.min().min() * 0.98)
            y_max = float(combined_df.max().max() * 1.02)

            chart = alt.Chart(plot_data).mark_line(interpolate='linear').encode(
                x=alt.X('index:N', title='날짜', sort=None),
                y=alt.Y('value:Q', title='가격', scale=alt.Scale(domain=[y_min, y_max])),
                color=alt.Color('variable:N', legend=None)
            ).properties(width='container', height=400)
            
            st.altair_chart(chart, use_container_width=True)

            st.divider()
            
            # 4. 하단 가격 리스트 (부활)
            curr_p = float(d_raw['Close'].iloc[-1])
            
            def display_list(title, is_predict):
                st.subheader(title)
                price_dict = {"현재가": curr_p}
                target_res = [d_bands, w_bands]
                
                for res in target_res:
                    for k, v in res.items():
                        base_v = float(v.iloc[-1])
                        if is_predict:
                            diff = base_v - float(v.iloc[-2])
                            price_dict[f"{k}예측"] = base_v + diff
                        else:
                            price_dict[k] = base_v
                            
                sorted_items = sorted(price_dict.items(), key=lambda x: x[1], reverse=True)
                for name, price in sorted_items:
                    pct = ((price / curr_p) - 1) * 100
                    if name == "현재가": st.markdown(f"### 🚩 **{name}: {price:,.0f}**")
                    else: st.write(f"{name}: **{price:,.0f}** ({pct:+.2f}%)")

            col1, col2 = st.columns(2)
            with col1: display_list("📊 금일/금주 확정", False)
            with col2: display_list("🔮 내일/차주 예측", True)
