import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import urllib.parse

# 1. 基本設定
st.set_page_config(page_title="台股投資戰情室", layout="wide")
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_html=True)

# 2. 連接 Google Sheets
SP_URL = "https://docs.google.com/spreadsheets/d/1pSVEg5J_-tg0wetPxNUVb9cU6kapUL_NIEV_Xz84PDM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- A. 處理刪除請求 ---
query_params = st.query_params
if "delete_code" in query_params:
    try:
        d_c = str(query_params["delete_code"]).strip()
        d_g = str(query_params["delete_group"]).strip()
        tmp = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl=0)
        tmp['code'] = tmp['code'].astype(str).str.replace(".0", "", regex=False).str.strip()
        updated = tmp[~((tmp['group'] == d_g) & (tmp['code'] == d_c))]
        conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
        st.query_params.clear()
        st.rerun()
    except:
        st.query_params.clear()

# --- B. 穩定版資料讀取 ---
@st.cache_data(ttl=5)
def load_all_data():
    try:
        # 讀取股票
        s_raw = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl=0)
        if s_raw is not None and not s_raw.empty:
            s_df = s_raw.dropna(subset=['group']).copy()
            s_df['code'] = s_df['code'].astype(str).str.replace(".0", "", regex=False).str.strip()
            s_df = s_df[~s_df['code'].isin(['nan', 'NaN', 'None', ''])]
        else:
            s_df = pd.DataFrame(columns=["group", "code", "name"])
            
        # 讀取筆記
        n_raw = conn.read(spreadsheet=SP_URL, worksheet="notes", ttl=0)
        if n_raw is not None and not n_raw.empty:
            n_df = n_raw.dropna(subset=['title']).copy()
        else:
            n_df = pd.DataFrame(columns=["title", "tags", "content", "date"])
            
        return s_df, n_df
    except:
        return pd.DataFrame(columns=["group", "code", "name"]), pd.DataFrame(columns=["title", "tags", "content", "date"])

stocks_df, notes_df = load_all_data()

# 頂部導覽
c_t, c_s = st.columns([5, 1])
with c_t: st.title("🇹🇼 台股投資戰情室 3.0")
with c_s: 
    if st.button("🔄 同步"):
        st.cache_data.clear()
        st.rerun()

# --- 2. 大盤摘要 ---
try:
    twii = yf.Ticker("^TWII")
    t_h = twii.history(period="5d")
    if not t_h.empty:
        now, prev_c = t_h.iloc[-1]['Close'], t_h.iloc[-2]['Close']
        diff, pct = now - prev_c, (now - prev_c)/prev_c * 100
        icon = "🔴" if diff > 0 else "🟢"
        c1, c2, c3 = st.columns(3)
        c1.metric("加權指數", f"{now:,.0f}", f"{icon} {diff:+.0f} ({pct:+.2f}%)")
        c2.metric("數據狀態", "✅ 連線正常", "")
        c3.metric("更新時間", datetime.now().strftime('%H:%M:%S'), "")
except:
    st.info("正在獲取大盤數據...")

st.divider()

# --- 3. 管理中心 ---
with st.expander("⚙️ 管理中心", expanded=False):
    # 新增個股
    with st.container(border=True):
        st.markdown("#### 🚀 新增個股 / ETF")
        g_opts = list(stocks_df['group'].unique()) if not stocks_df.empty else []
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: t_g = st.selectbox("目標群組", g_opts if g_opts else ["請先建立"], key="m_g")
        with c2: i_c = st.text_input("代碼", key="m_c")
        with c3: i_n = st.text_input("名稱", key="m_n")
        if st.button("🌟 存入雲端", use_container_width=True, type="primary"):
            if i_c and t_g != "請先建立":
                clean = stocks_df[~((stocks_df['group'] == t_g) & (stocks_df['code'] == "9999"))]
                new_row = pd.DataFrame([{"group": t_g, "code": str(i_c).strip(), "name": i_n}])
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=pd.concat([clean, new_row]))
                st.cache_data.clear()
                st.rerun()
    
    # 群組管理
    col_l, col_r = st.columns(2)
    with col_l:
        with st.container(border=True):
            st.markdown("#### 📂 新建群組")
            n_g = st.text_input("群組名稱", key="new_g_f")
            if st.button("建立群組", use_container_width=True):
                if n_g:
                    new_row = pd.DataFrame([{"group": n_g, "code": "9999", "name": "PH"}])
                    conn.update(spreadsheet=SP_URL, worksheet="stocks", data=pd.concat([stocks_df, new_row]))
                    st.cache_data.clear()
                    st.rerun()
    with col_r:
        with st.container(border=True):
            st.markdown("#### 🗑️ 刪除管理")
            d_g_sel = st.selectbox("選取群組", ["請選擇"] + g_opts, key="del_g_f")
            if st.button("刪除群組", use_container_width=True):
                if d_g_sel != "請選擇":
                    conn.update(spreadsheet=SP_URL, worksheet="stocks", data=stocks_df[stocks_df['group'] != d_g_sel])
                    st.cache_data.clear()
                    st.rerun()

# --- 4. 個股清單 ---
if not stocks_df.empty:
    for g in stocks_df['group'].unique():
        st.subheader(f"📁 {g}")
        sub = stocks_df[stocks_df['group'] == g]
        m_col, _ = st.columns([10, 1])
        with m_col:
            for _, row in sub.iterrows():
                t_c = str(row['code']).strip()
                if t_c in ["9999", "nan", "None", ""]: continue
                try:
                    success = False
                    for suffix in [".TW", ".TWO"]:
                        tk = yf.Ticker(f"{t_c}{suffix}")
                        h = tk.history(period="2d")
                        if not h.empty:
                            cp, pp = h.iloc[-1]['Close'], h.iloc[0]['Close']
                            d, p = cp - pp, (cp - pp)/pp * 100
                            color = "#ff4b4b" if d > 0 else "#00ff41" if d < 0 else "#ffffff"
                            m_i = "▲" if d > 0 else "▼" if d < 0 else "─"
                            params = urllib.parse.urlencode({"delete_code": t_c, "delete_group": g})
                            st.markdown(f"""
                            <div style="display: flex; justify-content: space-between; align-items: center; background: #262730; padding: 10px 15px; border-radius: 8px; margin-bottom: 4px; border-left: 4px solid {color};">
                                <div style="flex: 2;">
                                    <div style="font-size: 0.75rem; color: #888;">{t_c}</div>
                                    <div style="font-size: 1rem; font-weight: 700;">{row['name']}</div>
                                </div>
                                <div style="flex: 1.2; text-align: center; font-size: 1.15rem; font-weight: 800;">{cp:.2f}</div>
                                <div style="flex: 1.8; text-align: right; display: flex; align-items: center; justify-content: flex-end; gap: 12px;">
                                    <div style="color: {color}; font-size: 0.85rem;"><b>{m_i} {abs(d):.2f}</b><br><small>({p:+.2f}%)</small></div>
                                    <a href="./?{params}" target="_self" style="text-decoration: none; color: #666; font-size: 1.2rem;">×</a>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            success = True; break
                    if not success:
                        st.caption(f"⚠️ {t_c} {row['name']} (連線失敗)")
                except: pass

st.divider()

# --- 5. 雲端筆記區 ---
st.header("📝 雲端筆記")
with st.form("note_form", clear_on_submit=True):
    n_t = st.text_input("主題")
    n_k = st.text_input("標籤 (例: 短線, 財報)")
    n_c = st.text_area("內容")
    if st.form_submit_button("💾 儲存筆記"):
        if n_t:
            new_n = pd.DataFrame([{"title": n_t, "tags": n_k, "content": n_c, "date": datetime.now().strftime("%Y-%m-%d")}])
            updated_notes = pd.concat([notes_df, new_n], ignore_index=True)
            conn.update(spreadsheet=SP_URL, worksheet="notes", data=updated_notes)
            st.cache_data.clear()
            st.rerun()

if not notes_df.empty:
    for _, n in notes_df.iloc[::-1].iterrows():
        with st.expander(f"📌 {n['title']} - {n['tags']} ({n['date']})"):
            st.write(n['content'])
