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

# --- B. 終極洗滌讀取邏輯 ---
@st.cache_data(ttl=5)
def load_and_clean_data():
    try:
        s_raw = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl=0)
        n_raw = conn.read(spreadsheet=SP_URL, worksheet="notes", ttl=0)
        
        # 股票資料洗滌
        if s_raw is not None and not s_raw.empty:
            s_df = s_raw.copy()
            # 強制轉換為字串，去除空格與 .0
            s_df['code'] = s_df['code'].astype(str).str.replace(".0", "", regex=False).str.strip()
            # 排除掉 nan, None 或長度不對的垃圾資料
            s_df = s_df[s_df['code'].str.lower() != 'nan']
            s_df = s_df[s_df['code'].str.len() >= 2]
            # 自動補零 (針對 0050 等)
            s_df['code'] = s_df['code'].apply(lambda x: x.zfill(4) if (x.isdigit() and len(x) < 4) else x)
            s_df = s_df.dropna(subset=['group', 'code'])
        else:
            s_df = pd.DataFrame(columns=["group", "code", "name"])

        n_df = n_raw.dropna(subset=['title']).copy() if n_raw is not None else pd.DataFrame()
        return s_df, n_df
    except:
        return pd.DataFrame(columns=["group", "code", "name"]), pd.DataFrame()

stocks_df, notes_df = load_and_clean_data()

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
    t_h = twii.history(period="3d")
    if not t_h.empty:
        now_c, pre_c = t_h.iloc[-1]['Close'], t_h.iloc[-2]['Close']
        diff, pct = now_c - pre_c, (now_c - pre_c)/pre_c * 100
        icon = "🔴" if diff > 0 else "🟢"
        c1, c2, c3 = st.columns(3)
        c1.metric("加權指數", f"{now_c:,.0f}", f"{icon} {diff:+.0f} ({pct:+.2f}%)")
        c2.metric("數據狀態", "✅ 已連線", "")
        c3.metric("最後更新", datetime.now().strftime('%H:%M:%S'), "")
except:
    st.info("大盤數據讀取中...")

st.divider()

# --- 3. 管理中心 (維持美化版) ---
with st.expander("⚙️ 管理中心", expanded=False):
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
    # (群組管理邏輯維持不變)

# --- 4. 個股清單 (nan 防禦版) ---
if not stocks_df.empty:
    for g in stocks_df['group'].unique():
        st.subheader(f"📁 {g}")
        sub = stocks_df[stocks_df['group'] == g]
        m_col, _ = st.columns([10, 1])
        with m_col:
            for _, row in sub.iterrows():
                t_c = str(row['code']).strip()
                # 再次檢查：無效代碼不進入抓取
                if t_c.lower() in ["nan", "none", "", "9999"]: continue
                
                try:
                    # 嘗試抓取
                    success = False
                    for suffix in [".TW", ".TWO"]:
                        tk = yf.Ticker(f"{t_c}{suffix}")
                        # 使用 fast_info 確保效率
                        h = tk.history(period="2d")
                        if not h.empty and not pd.isna(h.iloc[-1]['Close']):
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
                        st.caption(f"無法取得 {t_c} 數據 (請檢查代碼)")
                except: continue

st.divider()

# --- 5. 雲端筆記區 (穩定顯示版) ---
st.header("📝 雲端筆記")
with st.form("note_form_v2", clear_on_submit=True):
    n_t = st.text_input("主題")
    n_k = st.text_input("標籤")
    n_c = st.text_area("內容")
    if st.form_submit_button("💾 儲存筆記"):
        if n_t:
            new_n = pd.DataFrame([{"title": n_t, "tags": n_k, "content": n_c, "date": datetime.now().strftime("%Y-%m-%d")}])
            updated_n = pd.concat([notes_df, new_n], ignore_index=True)
            conn.update(spreadsheet=SP_URL, worksheet="notes", data=updated_n)
            st.cache_data.clear()
            st.rerun()

if not notes_df.empty:
    for _, n in notes_df.iloc[::-1].iterrows():
        with st.expander(f"📌 {n['title']} ({n['date']})"):
            st.write(n['content'])
