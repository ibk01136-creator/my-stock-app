import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="SK하이닉스/삼성전자 변동성", layout="wide")

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
            
            # 1. 차트용 데이터 빌드 (최근 20일)
            recent_idx = d_raw.index[-20:]
            chart_df = pd.DataFrame(index=recent_idx)
            chart_df['현재가'] = d_raw['Close'].iloc[-20:]
            
            for k, v in d_bands.items(): chart_df[k] = v.iloc[-20:]
            
            # 주봉: 주의 첫 영업일에만 데이터 매칭 (나머지는 빈칸)
            for k, v in w_bands.items():
                w_series = pd.Series(index=recent_idx, dtype='float64')
                common_dates = v.index.intersection(recent_idx)
                w_series.loc[common_dates] = v.loc[common_dates]
                chart_df[k] = w_series

            # 2. 미래 1일 예측 행 생성
            last_date = recent_idx[-1]
            next_date = last_date + pd.Timedelta(days=1)
            forecast_data = {}
            
            for col in chart_df.columns:
                if col == '현재가': continue
                # 과거 마지막 2개 지점으로 기울기 계산
                vals = chart_df[col].dropna()
                if len(vals) >= 2:
                    diff = vals.iloc[-1] - vals.iloc[-2]
                    forecast_data[f"{col}예측"] = vals.iloc[-1] + diff
            
            # 3. 차트용 멜팅 (Altair 전용 데이터 구조)
            # 인덱스를 '날짜' 컬럼으로 고정하여 KeyError 방지
            chart_ready = chart_df.copy()
            chart_ready.index = chart_ready.index.strftime('%m/%d')
            chart_ready = chart_ready.reset_index().rename(columns={'index': '날짜'})
            
            # 미래 데이터 추가 (선 연결을 위해 마지막 날짜와 예측 날짜만 포함된 임시 DF)
            last_date_str = recent_idx[-1].strftime('%m/%d')
            next_date_str = next_date.strftime('%m/%d')
            
            pred_rows = []
            for pred_name, pred_val in forecast_data.items():
                origin_name = pred_name.replace("예측", "")
                # 마지막 실선 끝점
                pred_rows.append({'날짜': last_date_str, 'variable': pred_name, 'value': chart_df[origin_name].iloc[-1]})
                # 예측 점점
                pred_rows.append({'날짜': next_date_str, 'variable': pred_name, 'value': pred_val})
            
            plot_data = chart_ready.melt(id_vars='날짜')
            if pred_rows:
                plot_data = pd.concat([plot_data, pd.DataFrame(pred_rows)], ignore_index=True)

            # 4. 차트 출력 (Y축 스케일 조정)
            y_min = float(chart_df.min().min() * 0.97)
            y_max = float(chart_df.max().max() * 1.03)

            main_chart = alt.Chart(plot_data).mark_line(interpolate='linear').encode(
                x=alt.X('날짜:N', sort=None),
                y=alt.Y('value:Q', scale=alt.Scale(domain=[y_min, y_max]), title='가격(원)'),
                color=alt.Color('variable:N', legend=None)
            ).properties(height=400)
            
            st.altair_chart(main_chart, use_container_width=True)

            st.divider()
            
            # 5. 하단 가격 리스트
            curr_p = float(d_raw['Close'].iloc[-1])
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 금일/금주 확정")
                p_dict = {"현재가": curr_p}
                for k, v in d_bands.items(): p_dict[k] = v.iloc[-1]
                for k, v in w_bands.items(): p_dict[k] = v.iloc[-1]
                
                for k, v in sorted(p_dict.items(), key=lambda x: x[1], reverse=True):
                    pct = ((v/curr_p)-1)*100
                    if k == "현재가": st.markdown(f"### 🚩 **{k}: {v:,.0f}**")
                    else: st.write(f"{k}: **{v:,.0f}** ({pct:+.2f}%)")

            with col2:
                st.subheader("🔮 내일/차주 예측")
                f_dict = {"현재가": curr_p}
                for k, v in d_bands.items(): 
                    f_dict[f"{k}예측"] = v.iloc[-1] + (v.iloc[-1]-v.iloc[-2])
                for k, v in w_bands.items():
                    f_dict[f"{k}예측"] = v.iloc[-1] + (v.iloc[-1]-v.iloc[-2])
                
                for k, v in sorted(f_dict.items(), key=lambda x: x[1], reverse=True):
                    pct = ((v/curr_p)-1)*100
                    if k == "현재가": st.markdown(f"### 🚩 **{k}: {v:,.0f}**")
                    else: st.write(f"{k}: **{v:,.0f}** ({pct:+.2f}%)")
