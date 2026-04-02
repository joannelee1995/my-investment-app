import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import urllib.parse

# ==========================================
# 1. 網頁基本設定與 CSS 美化
# ==========================================
st.set_page_config(page_title="台股投資戰情室 3.0", layout="wide")

st.markdown("""
<style>
    /* 隱藏預設元件樣式 */
    [data-testid="stMetricDelta"] svg { display: none; }
    
    /* 大盤 Metric 樣式 */
    [data-testid="metric-container"] { 
        background-color: #1e2129; 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #333; 
    }

    /* 管理區卡片樣式 */
    .manage-card {
        background-color: #1e2129;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
        margin-bottom: 10px;
    }
    .manage-header {
        color: #ff4b4b;
        font-size: 1.1rem;
        font-weight: bold;
        margin-bottom: 15px;
    }

    /* 強制手機版 Columns 不堆疊 (關鍵 CSS) */
    @media (max-width: 640px) {
        div[data-testid="stBlock"] div[data-testid="column"] {
            min-width: unset !important;
            flex: 1 1 auto !important;
            width: fit-content !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心邏輯：連接 Google Sheets 與處理刪除
# ==========================================
SP_URL = "https://docs.google.com/spreadsheets/d/1pSVEg5J_-tg0wetPxNUVb9cU6kapUL_NIEV_Xz84PDM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# 處理來自 URL 的刪除請求
query_params = st.query_params
if "delete_code" in query_params and "delete_group" in query_params:
    del_c = query_params["delete_code"]
    del_g = query_params["delete_group"]
    try:
        tmp_df = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl=0)
        tmp_df['code'] = tmp_df['code'].astype(str).str.replace(".0", "", regex=False).str.strip()
        updated_df = tmp_df[~((tmp_df['group'] == del_g) & (tmp_df['code'] == del_c))]
        conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated_df)
        st.query_params.clear()
        st.rerun()
    except:
        st.query_params.clear()

@st.cache_data(ttl=15)
def load_data():
    try:
        s_df = conn.read(spreadsheet=SP_URL, worksheet="stocks")
        n_df = conn.read(spreadsheet=SP_URL, worksheet="notes")
        # ETF 補零邏輯
        def format_code(x):
            s = str(x).replace(".0", "").strip()
            return s.zfill(4) if (s.isdigit() and len(s) < 4) else s
        s_df['code'] = s_df['code'].apply(format_code)
        return s_df.dropna(how='all'), n_df.dropna(how='all')
    except:
        return None, None

stocks_df, notes_df = load_data()

# ==========================================
# 3. 頁面頂部與大盤數據
# ==========================================
c_t, c_s = st.columns([6, 1])
with c_t: st.title("🇹🇼 台股投資戰情室 3.0")
with c_s: 
    if st.button("🔄 同步"):
        st.cache_data.clear()
        st.rerun()

try:
    twii = yf.Ticker("^TWII")
    t_hist = twii.history(period="10d")
    if not t_hist.empty:
        now, prev = t_hist.iloc[-1], t_hist.iloc[-2]
        diff, pct = now['Close'] - prev['Close'], (now['Close'] - prev['Close']) / prev['Close'] * 100
        icon = "🔴" if diff > 0 else "🟢"
        
        avg_v = t_hist['Volume'].tail(5).mean()
        v_ratio = now['Volume'] / avg_v
        mood = "🔥 多方攻擊" if pct > 0.5 and v_ratio > 1.1 else "⚖️ 區間震盪"
        
        col1, col2, col3 = st.columns(3)
        col1.metric("加權指數", f"{now['Close']:,.0f}", f"{icon} {diff:+.0f} ({pct:+.2f}%)")
        col2.metric("市場情緒", mood, f"量能比: {v_ratio:.2f}x")
        col3.metric("更新時間", datetime.now().strftime('%H:%M:%S'), "")
except:
    st.info("大盤數據連線中...")

st.divider()

# ==========================================
# 4. 管理中心 (美化版)
# ==========================================
st.subheader("🗂️ 自選股管理")
with st.expander("⚙
