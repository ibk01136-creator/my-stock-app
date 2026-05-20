import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 1. 설정
st.set_page_config(page_title="볼린저 비전", layout="wide")

STOCKS = {
    "삼성전자": "005930", "SK하이닉스": "000660", "SK스퀘어": "402340",
    "현대차": "005380", "두산에너빌리티": "034020", "삼성전기": "009150", "삼성생명": "032830",
    "KB금융": "105560", "삼성SDI": "006400", "HD일렉트릭": "267260",
    "LS일렉트릭": "010120", "미래에셋증권": "006800", "신한지주": "055550",
    "포스코홀딩스": "005490", "SK": "034730", "하나금융지주": "086790",
    "두산": "000150", "삼성중공업": "010140",
    "LG전자": "066570", "HD현대": "267250", "LIG디펜스": "079550",
    "SK텔레콤": "017670", "KT&G": "033780", "LG이노텍": "011070", "대한전선": "001440",
    "삼성E&A": "028050", "한화": "000880", "HD건설기계": "267270",
    "엘앤에프": "066970", "머니마켓액티브": "488770"
}

# 2. 데이터 관련 함수
@st.cache_data(ttl=300)
def get_clean_data(ticker, period_days, interval='d'):
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (pd.Timestamp.now() - pd.Timedelta(days=period_days)).strftime('%Y-%m-%d')
        data = fdr.DataReader(ticker, start_date, end_date)
        if interval == 'wk':
            data = data.resample('W-MON').last()
        if data.empty: return None
        return data
    except: return None

def calculate_bands(data, type_name):
    tp = data['Close']
    ma = tp.rolling(window=20).mean()
    std = tp.rolling(window=20).std()
    res = {f"{type_name} 중심": ma}
    for s in [2.0, 1.6, 1.2]:
        res[f"{type_name} {s}상"] = ma + (std * s)
        res[f"{type_name} {s}하"] = ma - (std * s)
    return res

# 3. 메인 로직
tabs = st.tabs(list(STOCKS.keys()))

for i, (name, ticker) in enumerate(STOCKS.items()):
    with tabs[i]:
        d_raw = get_clean_data(ticker, 150, 'd')
        w_raw = get_clean_data(ticker, 730, 'wk')

        if d_raw is not None and w_raw is not None:
            curr_price = float(d_raw['Close'].iloc[-1])
            d_bands = calculate_bands(d_raw, "일봉")
            w_bands = calculate_bands(w_raw, "주봉")
            
            DISPLAY_DAYS = 20 
            d_recent = d_raw.iloc[-DISPLAY_DAYS:]
            today_x = DISPLAY_DAYS - 1
            
            # X축 날짜 라벨 준비
            date_labels = [d.strftime('%m/%d') for d in d_recent.index]
            # 예측 영역 라벨 추가 (+1일 등)
            date_labels += [f"+{j}" for j in range(1, 10)]

        
            # 주봉 위치 계산
            this_w_idx = w_raw.index[-1]
            prev_w_idx = w_raw.index[-2]
            actual_gap = len(d_raw[(d_raw.index >= prev_w_idx) & (d_raw.index < this_w_idx)])
            if actual_gap == 0: actual_gap = 5
            
            try:
                this_w_pos_x = d_recent.index.get_loc(this_w_idx)
            except:
                this_w_pos_x = today_x

            w_future_x = this_w_pos_x + actual_gap
            d_future_x = today_x + 1

            fig = go.Figure()
            c_up, c_lo = ['#FFCCCC', '#FF6666', '#FF0000'], ['#CCCCFF', '#6666FF', '#0000FF']
            
            # 스케일 조절을 위한 데이터 수집
            top_check = []
            bottom_check = []

            # 1. 일봉 렌더링
            for key in d_bands:
                std_val = float(key.split()[1][:-1]) if '중심' not in key else 0
                color = 'purple' if '중심' in key else (c_up[[2.0, 1.6, 1.2].index(std_val)] if '상' in key else c_lo[[2.0, 1.6, 1.2].index(std_val)])
                y_vals = d_bands[key].iloc[-DISPLAY_DAYS:].tolist()
                fig.add_trace(go.Scatter(x=list(range(DISPLAY_DAYS)), y=y_vals, name=key, line=dict(color=color, width=1)))
                
                slope = float(d_bands[key].iloc[-1] - d_bands[key].iloc[-2])
                pred_y = float(y_vals[-1] + slope)
                fig.add_trace(go.Scatter(x=[today_x, d_future_x], y=[y_vals[-1], pred_y], line=dict(color=color, width=1, dash='dot'), showlegend=False))
                top_check.extend(y_vals + [pred_y])

            # 2. 주봉 렌더링
            for key in w_bands:
                std_val = float(key.split()[1][:-1]) if '중심' not in key else 0
                color = '#BA55D3' if '중심' in key else (c_up[[2.0, 1.6, 1.2].index(std_val)] if '상' in key else c_lo[[2.0, 1.6, 1.2].index(std_val)])
                w_x, w_y = [], []
                for w_dt, val in w_bands[key].items():
                    if w_dt in d_recent.index:
                        w_x.append(d_recent.index.get_loc(w_dt))
                        w_y.append(val)
                if w_x:
                    fig.add_trace(go.Scatter(x=w_x, y=w_y, name=key, line=dict(color=color, width=1.3, dash='dashdot')))
                    w_slope = float(w_bands[key].iloc[-1] - w_bands[key].iloc[-2])
                    w_pred_y = float(w_y[-1] + w_slope)
                    fig.add_trace(go.Scatter(x=[w_x[-1], w_future_x], y=[w_y[-1], w_pred_y], line=dict(color=color, width=1.3, dash='dot'), showlegend=False))
                    top_check.extend(w_y + [w_pred_y])
                    # 주봉 중심선은 바닥 체크 대상
                    if "중심" in key:
                        bottom_check.extend(w_y + [w_pred_y])

            # 3. 현재가 선
            curr_close_v = d_recent['Close'].tolist()
            fig.add_trace(go.Scatter(x=list(range(DISPLAY_DAYS)), y=curr_close_v, name='현재가', line=dict(color='black', width=2)))
            bottom_check.extend(curr_close_v) # 현재가 바닥 체크 대상 추가

            # Y축 스케일 최적화
            y_min = min([v for v in bottom_check if pd.notna(v)]) * 0.99
            y_max = max([v for v in top_check if pd.notna(v)]) * 1.01
            
            fig.update_layout(height=500, margin=dict(l=10, r=10, t=30, b=10),
                xaxis=dict(tickmode='array', tickvals=list(range(len(date_labels))), ticktext=date_labels, range=[0, d_future_x + 2]),
                yaxis=dict(tickformat=",", range=[y_min, y_max]), 
                hovermode='x unified', showlegend=False)
            
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📊 지표 확정가")
                p_map = {k: float(d_bands[k].iloc[-1]) for k in d_bands}
                p_map.update({k: float(w_bands[k].iloc[-1]) for k in w_bands})
                p_map["🚩 현재가"] = curr_price
                for k, v in sorted(p_map.items(), key=lambda x: x[1], reverse=True):
                    if "현재가" in k: st.markdown(f"### {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({((v/curr_price)-1)*100:+.2f}%)")
            with c2:
                st.subheader("🔮 미래 예측")
                f_map = {f"{k}예측": float(d_bands[k].iloc[-1] + (d_bands[k].iloc[-1] - d_bands[k].iloc[-2])) for k in d_bands}
                f_map.update({f"{k}예측": float(w_bands[k].iloc[-1] + (w_bands[k].iloc[-1] - w_bands[k].iloc[-2])) for k in w_bands})
                f_map["🚩 현재가"] = curr_price
                for k, v in sorted(f_map.items(), key=lambda x: x[1], reverse=True):
                    if "현재가" in k: st.markdown(f"### {k}: {v:,.0f}")
                    else: st.write(f"{k}: **{v:,.0f}** ({((v/curr_price)-1)*100:+.2f}%)")
