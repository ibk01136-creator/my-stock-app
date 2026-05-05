import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="SK/삼성 변동성 전략", layout="wide")

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
            
            # 1. 차트 기본 데이터 (최근 20일)
            recent_idx = d_raw.index[-20:]
            chart_df = pd.DataFrame(index=recent_idx)
            chart_df['현재가'] = d_raw['Close'].iloc[-20:]
            for k, v in d_bands.items(): chart_df[k] = v.iloc[-20:]
            
            # 주봉 데이터 매칭 (첫 영업일만 찍기)
            for k, v in w_bands.items():
                s = pd.Series(index=recent_idx, dtype='float64')
                intersect = v.index.intersection(recent_idx)
                s.loc[intersect] = v.loc[intersect]
                chart_df[k] = s

            # 2. 미래 1일 예측치 계산
            last_date = recent_idx[-1]
            next_date = last_date + pd.Timedelta(days=1)
            
            # 3. 차트용 데이터 변환 (KeyError 방지 구조)
            # 인덱스를 먼저 문자열 날짜로 바꾸고 컬럼화
            plot_df = chart_df.copy()
            plot_df.index = plot_df.index.strftime('%m/%d')
            plot_df = plot_df.reset_index().rename(columns={'index': 'date'})
            
            # 미래 예측 포인트 추가 (선 연결용)
            last_date_str = last_date.strftime('%m/%d')
            next_date_str = next_date.strftime('%m/%d')
            
            pred_entries = []
            for col in chart_df.columns:
                if col == '현재가': continue
                vals = chart_df[col].dropna()
                if len(vals) >= 2:
                    diff = vals.iloc[-1] - vals.iloc[-2]
                    pred_val = vals.iloc[-1] + diff
                    # 마지막 점과 예측 점을 리스트에 추가
                    pred_entries.append({'date': last_date_str, 'variable': f"{col}예측", 'value': vals.iloc[-1]})
                    pred_entries.append({'date': next_date_str, 'variable': f"{col}예측", 'value': pred_val})
            
            # 데이터 합치기
            melted = plot_df.melt(id_vars='date')
            if pred_entries:
                melted = pd.concat([melted, pd.DataFrame(pred_entries)], ignore_index=True)

            # 4. 차트 출력 (Y축 스케일 최적화)
            y_min = float(chart_df.min().min() * 0.98)
            y_max = float(chart_df.max().max() * 1.02)

            line_chart = alt.Chart(melted).mark_line(interpolate='linear').encode(
                x=alt.X('date:N', sort=None, title='날짜'),
                y=alt.Y('value:Q', scale=alt.Scale(domain=[y_min, y_max]), title='가격'),
                color=alt.Color('variable:N', legend=None)
            ).properties(height=400)
            
            st.altair_chart(line_chart, use_container_width=True)

            st.divider()
            
            # 5. 하단 리스트 (확정 vs 예측)
            curr_p = float(d_raw['Close'].iloc[-1])
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("📊 금일/금주 확정")
                p_map = {"현재가": curr_p}
                for k, v in d_bands.items(): p_map[k] = v.iloc[-1]
                for k, v in w_bands.items(): p_map[k] = v.iloc[-1]
                for k, v in sorted(p_map.items(), key=lambda x: x[1], reverse=True):
                    p_diff = ((v/curr_p)-1)*100
                    if k == "현재가": st.markdown(f"### 🚩 {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({p_diff:+.2f}%)")

            with c2:
                st.subheader("🔮 내일/차주 예측")
                f_map = {"현재가": curr_p}
                for k, v in d_bands.items(): f_map[f"{k}예측"] = v.iloc[-1] + (v.iloc[-1]-v.iloc[-2])
                for k, v in w_bands.items(): f_map[f"{k}예측"] = v.iloc[-1] + (v.iloc[-1]-v.iloc[-2])
                for k, v in sorted(f_map.items(), key=lambda x: x[1], reverse=True):
                    f_diff = ((v/curr_p)-1)*100
                    if k == "현재가": st.markdown(f"### 🚩 {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({f_diff:+.2f}%)")
