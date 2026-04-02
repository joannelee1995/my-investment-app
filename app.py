import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="台股投資戰情室 3.0", layout="wide")

# 強制隱藏系統預設箭頭
st.markdown("""
    <style>
    [data-testid="stMetricDelta"] svg { display: none; }
    </style>
    """, unsafe_allow_html=True)

# 內建常用名稱對照
STOCK_NAMES = {"2330": "台積電", "2454": "聯發科", "0050": "元大台灣50", "0056": "元大高股息", "00878": "國泰永續高股息"}

# 初始化資料
if 'stock_groups' not in st.session_state:
    st.session_state.stock_groups = {"電子": [{"code": "2330", "name": "台積電"}]}
if 'notes' not in st.session_state: 
    st.session_state.notes = []

# --- 1. 置頂：大盤狀況 ---
st.title("🇹🇼 台股投資戰情室 3.0")
try:
    twii = yf.Ticker("^TWII")
    t_hist = twii.history(period="2d")
    if not t_hist.empty:
        now = t_hist.iloc[-1]['Close']
        prev = t_hist.iloc[-2]['Close']
        diff = now - prev
        pct = (diff / prev) * 100
        
        # 判定市場情緒 (客觀描述)
        if pct >= 1.0: sentiment = "📈 強勢"
        elif 0.2 <= pct < 1.0: sentiment = "↗️ 上漲"
        elif -0.2 < pct < 0.2: sentiment = "⚖️ 平盤震盪"
        elif -1.0 < pct <= -0.2: sentiment = "↘️ 回檔"
        else: sentiment = "📉 跌幅較大"
        
        m_icon = "🔴" if diff > 0 else "🟢"
        
        c1, c2, c3 = st.columns(3)
        c1.metric("加權指數", f"{now:,.2f}", f"{m_icon} {diff:+.2f} ({pct:+.2f}%)")
        c2.metric("當前盤勢", sentiment, f"趨勢標示: {m_icon}")
        c3.metric("最後更新", datetime.now().strftime('%H:%M:%S'), "")
except:
    st.write("大盤數據讀取中...")

st.divider()

# --- 2. 財經焦點摘要 ---
st.header("📰 今日財經焦點摘要")
st.markdown("""
- **大盤走勢：** 今日權值股表現為觀察重點，留意加權指數支撐點位。
- **量能觀察：** 成交量是否放量將決定短線反彈力道。
- **產業焦點：** 半導體與高股息 ETF 交易依舊活絡。
""")

st.divider()

# --- 3. 自選股群組管理 ---
st.header("🗂️ 自選股群組管理")

with st.expander("⚙️ 管理群組與個股 (點此編輯)", expanded=True):
    g1, g2 = st.columns(2)
    new_g = g1.text_input("1. 建立新分類")
    if g1.button("新增分類"):
        if new_g and new_g not in st.session_state.stock_groups:
            st.session_state.stock_groups[new_g] = []
            st.rerun()
    
    st.write("---")
    target_g = st.selectbox("2. 選擇分類", list(st.session_state.stock_groups.keys()))
    c_col1, c_col2 = st.columns(2)
    s_code = c_col1.text_input("3. 代碼")
    s_name = c_col2.text_input("4. 名稱 (選填)")
    
    if st.button("確認加入"):
        if s_code:
            final_name = s_name if s_name else STOCK_NAMES.get(s_code, "台股")
            st.session_state.stock_groups[target_g].append({"code": s_code, "name": final_name})
            st.rerun()

# 顯示分組
for
