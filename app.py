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
    [data-testid="stMetricDelta"] svg { display: none; }
    [data-testid="metric-container"] { 
        background-color: #1e2129; 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #333; 
    }
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
# 4. 管理中心 (修復語法版)
# ==========================================
st.subheader("🗂️ 自選股管理")
with st.expander("⚙️ 點此展開管理中心", expanded=False):
    st.markdown('<div class="manage-card">', unsafe_allow_html=True)
    st.markdown('<div class="manage-header">🚀 新增個股/ETF</div>', unsafe_allow_html=True)
    current_gs = list(stocks_df['group'].unique()) if stocks_df is not None else []
    ca1, ca2, ca3, ca4 = st.columns([2, 1.5, 2, 1])
    with ca1: target_g = st.selectbox("目標群組", current_gs if current_gs else ["請先建立"], key="sel_g")
    with ca2: in_c = st.text_input("代碼", placeholder="例: 0050", key="in_c")
    with ca3: in_n = st.text_input("名稱", placeholder="例: 元大台灣50", key="in_n")
    with ca4:
        st.write("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("存入", key="save_btn"):
            if target_g != "請先建立" and in_c:
                clean = stocks_df[~((stocks_df['group'] == target_g) & (stocks_df['code'] == "9999"))]
                new_s = pd.DataFrame([{"group": target_g, "code": str(in_c).strip(), "name": in_n}])
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=pd.concat([clean, new_s]))
                st.cache_data.clear()
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    cg1, cg2 = st.columns(2)
    with cg1:
        st.markdown('<div class="manage-card">', unsafe_allow_html=True)
        st.markdown('<div class="manage-header">新建群組</div>', unsafe_allow_html=True)
        new_g = st.text_input("輸入名稱", key="ng")
        if st.button("建立", key="ng_b"):
            if new_g:
                row = pd.DataFrame([{"group": new_g, "code": "9999", "name": "PH"}])
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=pd.concat([stocks_df, row]))
                st.cache_data.clear()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with cg2:
        st.markdown('<div class="manage-card">', unsafe_allow_html=True)
        st.markdown('<div class="manage-header">⚠️ 刪除群組</div>', unsafe_allow_html=True)
        dg = st.selectbox("選取群組", ["請選擇"] + current_gs, key="dg")
        if st.button("確認刪除", key="dg_b"):
            if dg != "請選擇":
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=stocks_df[stocks_df['group'] != dg])
                st.cache_data.clear()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 5. 個股清單
# ==========================================
if stocks_df is not None:
    for g in stocks_df['group'].unique():
        st.subheader(f"📁 {g}")
        sub = stocks_df[stocks_df['group'] == g]
        m_col, _ = st.columns([10, 1])
        with m_col:
            for _, row in sub.iterrows():
                t_c = str(row['code'])
                if t_c == "9999": continue
                try:
                    success = False
                    for suffix in [".TW", ".TWO"]:
                        tk = yf.Ticker(f"{t_c}{suffix}")
                        h = tk.history(period="2d")
                        if not h.empty:
                            cp, pp = h.iloc[-1]['Close'], h.iloc[0]['Close']
                            d, p = cp - pp, ((cp - pp)/pp)*100
                            color = "#ff4b4b" if d > 0 else "#00ff41" if d < 0 else "#ffffff"
                            m_icon = "▲" if d > 0 else "▼" if d < 0 else "─"
                            del_params = urllib.parse.urlencode({"delete_code": t_c, "delete_group": g})
                            del_url = f"./?{del_params}"
                            st.markdown(f"""
                            <div style="display: flex; justify-content: space-between; align-items: center; background: #262730; padding: 10px 15px; border-radius: 8px; margin-bottom: 3px; border-left: 5px solid {color}; border-right: 1px solid #444;">
                                <div style="flex: 2;">
                                    <div style="font-size: 0.75rem; color: #888;">{t_c}</div>
                                    <div style="font-size: 1rem; font-weight: 700;">{row['name']}</div>
                                </div>
                                <div style="flex: 1.2; text-align: center; font-size: 1.1rem; font-weight: 800;">{cp:.2f}</div>
                                <div style="flex: 1.8; text-align: right; display: flex; align-items: center; justify-content: flex-end; gap: 12px;">
                                    <div style="color: {color}; font-size: 0.9rem; line-height: 1.1;">
                                        <b>{m_icon} {abs(d):.2f}</b><br><small>({p:+.2f}%)</small>
                                    </div>
                                    <a href="{del_url}" target="_self" style="text-decoration: none; color: #555; font-size: 1.3rem; font-weight: bold; padding: 0 5px;">×</a>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            success = True; break
                except: continue

st.divider()

# ==========================================
# 6. 雲端筆記區
# ==========================================
st.header("📝 投資筆記")
with st.form("note_vfinal", clear_on_submit=True):
    nt, nk = st.text_input("主題"), st.text_input("標籤")
    nc = st.text_area("詳細內容")
    if st.form_submit_button("儲存至雲端"):
        if nt:
            new_note = pd.DataFrame([{"title": nt, "tags": nk, "content": nc, "date": datetime.now().strftime("%Y-%m-%d")}])
            conn.update(spreadsheet=SP_URL, worksheet="notes", data=pd.concat([notes_df, new_note]))
            st.cache_data.clear()
            st.rerun()

if notes_df is not None and not notes_df.empty:
    for _, n in notes_df.iloc[::-1].iterrows():
        with st.expander(f"📌 {n['title']} ({n['date']})"):
            st.caption(f"標籤: {n['tags']}")
            st.write(n['content'])
