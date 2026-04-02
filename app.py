import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 網頁基本設定
st.set_page_config(page_title="台股投資戰情室", layout="wide")

# 隱藏預設箭頭
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_html=True)

# 1. 連接 Google Sheets
SP_URL = "https://docs.google.com/spreadsheets/d/1pSVEg5J_-tg0wetPxNUVb9cU6kapUL_NIEV_Xz84PDM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data_cached():
    try:
        s_df = conn.read(spreadsheet=SP_URL, worksheet="stocks")
        n_df = conn.read(spreadsheet=SP_URL, worksheet="notes")
        # 核心修正：確保代碼一定是 4-5 碼字串，不足則補 0 (解決 ETF 00 開頭問題)
        def format_code(x):
            s = str(x).replace(".0", "").strip()
            if s.isdigit() and len(s) < 4:
                return s.zfill(4)
            return s
        
        s_df['code'] = s_df['code'].apply(format_code)
        return s_df.dropna(how='all'), n_df.dropna(how='all')
    except:
        return None, None

# 頂部導覽
c_title, c_sync = st.columns([4, 1])
with c_title:
    st.title("🇹🇼 台股投資戰情室 3.0")
with c_sync:
    if st.button("🔄 同步雲端"):
        st.cache_data.clear()
        st.rerun()

stocks_df, notes_df = load_data_cached()

if stocks_df is None:
    st.warning("⚠️ 讀取中，若長時間無反應請點擊「同步雲端」。")
    stocks_df = pd.DataFrame(columns=["group", "code", "name"])
    notes_df = pd.DataFrame(columns=["title", "tags", "content", "date"])

# --- 2. 大盤摘要 ---
try:
    twii = yf.Ticker("^TWII")
    t_hist = twii.history(period="5d")
    if not t_hist.empty:
        now, prev = t_hist.iloc[-1], t_hist.iloc[-2]
        diff, pct = now['Close'] - prev['Close'], (now['Close'] - prev['Close']) / prev['Close'] * 100
        icon = "🔴" if diff > 0 else "🟢"
        c1, c2, c3 = st.columns(3)
        c1.metric("加權指數", f"{now['Close']:,.2f}", f"{icon} {diff:+.2f} ({pct:+.2f}%)")
        c2.metric("市場情緒", "數據連線中", "")
        c3.metric("更新時間", datetime.now().strftime('%H:%M:%S'), "")
except:
    pass

st.divider()

# --- 3. 自選股管理 ---
with st.expander("⚙️ 管理中心", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        new_g = st.text_input("新建分類")
        if st.button("確認建立"):
            if new_g:
                new_row = pd.DataFrame([{"group": new_g, "code": "9999", "name": "PH"}])
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=pd.concat([stocks_df, new_row]))
                st.cache_data.clear()
                st.rerun()
    with col2:
        target_g_del = st.selectbox("刪除分類", ["請選擇"] + list(stocks_df['group'].unique()))
        if st.button("確認刪除"):
            conn.update(spreadsheet=SP_URL, worksheet="stocks", data=stocks_df[stocks_df['group'] != target_g_del])
            st.cache_data.clear()
            st.rerun()
    
    st.write("---")
    st.write("**新增個股/ETF**")
    target_g = st.selectbox("存入群組", stocks_df['group'].unique())
    c_s1, c_s2 = st.columns(2)
    in_c, in_n = c_s1.text_input("代碼 (例: 0050)"), c_s2.text_input("名稱")
    if st.button("🚀 存入雲端"):
        if in_c:
            clean = stocks_df[~((stocks_df['group'] == target_g) & (stocks_df['code'] == "9999"))]
            new_s = pd.DataFrame([{"group": target_g, "code": str(in_c).strip(), "name": in_n}])
            conn.update(spreadsheet=SP_URL, worksheet="stocks", data=pd.concat([clean, new_s]))
            st.cache_data.clear()
            st.rerun()

# --- 4. 顯示列表 (強化 ETF 抓取邏輯) ---
for g in stocks_df['group'].unique():
    st.subheader(f"📁 {g}")
    sub = stocks_df[stocks_df['group'] == g]
    for _, row in sub.iterrows():
        t_c = str(row['code'])
        if t_c == "9999": continue
        
        try:
            # 嘗試抓取 (.TW 或 .TWO)
            success = False
            for suffix in [".TW", ".TWO"]:
                tk = yf.Ticker(f"{t_c}{suffix}")
                h = tk.history(period="2d")
                if not h.empty:
                    cp, pp = h.iloc[-1]['Close'], h.iloc[0]['Close']
                    d, p = cp - pp, ((cp - pp)/pp)*100
                    m = "🔴" if d > 0 else "🟢" if d < 0 else "⚪"
                    sc1, sc2, sc3, sc4 = st.columns([2, 1.5, 2, 1])
                    sc1.write(f"**{t_c} {row['name']}**")
                    sc2.write(f"價: {cp:.2f}")
                    sc3.write(f"{m} {d:+.2f} ({p:+.2f}%)")
                    if sc4.button("❌", key=f"del_{g}_{t_c}"):
                        conn.update(spreadsheet=SP_URL, worksheet="stocks", data=stocks_df[~((stocks_df['group'] == g) & (stocks_df['code'] == t_c))])
                        st.cache_data.clear()
                        st.rerun()
                    success = True
                    break
            if not success:
                st.caption(f"⚠️ 無法取得 {t_c} 資料，請確認代碼是否正確")
        except:
            st.caption(f"讀取 {t_c} 中...")

st.divider()
st.header("📝 雲端筆記")
# (筆記區邏輯維持不變...)
