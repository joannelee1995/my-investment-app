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

# --- A. 處理刪除請求 (個股 & 筆記) ---
query_params = st.query_params

# 刪除個股
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

# 刪除筆記 (新增邏輯)
if "delete_note_title" in query_params:
    try:
        dn_t = query_params["delete_note_title"]
        dn_d = query_params["delete_note_date"]
        n_tmp = conn.read(spreadsheet=SP_URL, worksheet="notes", ttl=0)
        # 比對標題與日期確保刪除正確
        n_updated = n_tmp[~((n_tmp['title'] == dn_t) & (n_tmp['date'] == dn_d))]
        conn.update(spreadsheet=SP_URL, worksheet="notes", data=n_updated)
        st.query_params.clear()
        st.rerun()
    except:
        st.query_params.clear()

# --- B. 讀取資料 ---
@st.cache_data(ttl=5)
def load_all_data_v4():
    try:
        s_raw = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl=0)
        n_raw = conn.read(spreadsheet=SP_URL, worksheet="notes", ttl=0)
        
        s_df = pd.DataFrame(columns=["group", "code", "name"])
        if s_raw is not None and not s_raw.empty:
            s_df = s_raw.copy()
            s_df['code'] = s_df['code'].astype(str).str.replace(".0", "", regex=False).str.strip()
            s_df = s_df[~s_df['code'].isin(['nan', 'NaN', 'None', '', '9999'])]

        n_df = pd.DataFrame(columns=["title", "tags", "content", "date"])
        if n_raw is not None and not n_raw.empty:
            n_df = n_raw.dropna(subset=['title']).copy()
            
        return s_df, n_df
    except:
        return pd.DataFrame(columns=["group", "code", "name"]), pd.DataFrame(columns=["title", "tags", "content", "date"])

stocks_df, notes_df = load_all_data_v4()

# 頂部導覽
st.title("🇹🇼 台股投資戰情室 3.0")
if st.button("🔄 同步雲端數據"):
    st.cache_data.clear()
    st.rerun()

st.divider()

# --- 3. 管理中心 ---
with st.expander("⚙️ 管理中心 (個股/群組)", expanded=False):
    st.info("可在下方直接新增個股，代碼會自動對接 Yahoo Finance。")
    with st.container(border=True):
        g_opts = list(stocks_df['group'].unique()) if not stocks_df.empty else []
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: t_g = st.selectbox("目標群組", g_opts if g_opts else ["請先建立"], key="add_g")
        with c2: i_c = st.text_input("代碼", key="add_c")
        with c3: i_n = st.text_input("名稱", key="add_n")
        if st.button("🌟 存入個股", use_container_width=True, type="primary"):
            if i_c and t_g != "請先建立":
                clean = stocks_df[~((stocks_df['group'] == t_g) & (stocks_df['code'] == "9999"))]
                new_row = pd.DataFrame([{"group": t_g, "code": str(i_c).strip(), "name": i_n}])
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=pd.concat([clean, new_row]))
                st.cache_data.clear()
                st.rerun()

# --- 4. 個股清單 ---
if not stocks_df.empty:
    for g in stocks_df['group'].unique():
        if pd.isna(g) or str(g).lower() == 'nan': continue
        st.subheader(f"📁 {g}")
        sub = stocks_df[stocks_df['group'] == g]
        for _, row in sub.iterrows():
            t_c = str(row['code']).strip()
            if t_c in ["9999", "nan", "None", ""]: continue
            try:
                d_code = t_c.zfill(4) if (t_c.isdigit() and len(t_c) < 4) else t_c
                success = False
                for suffix in [".TW", ".TWO"]:
                    tk = yf.Ticker(f"{d_code}{suffix}")
                    h = tk.history(period="2d")
                    cp = h.iloc[-1]['Close'] if not h.empty and not pd.isna(h.iloc[-1]['Close']) else tk.fast_info.get('lastPrice', 0)
                    pp = h.iloc[0]['Close'] if not h.empty and not pd.isna(h.iloc[0]['Close']) else tk.fast_info.get('previousClose', cp)
                    
                    if cp > 0 and not pd.isna(cp):
                        d, p = cp - pp, ((cp - pp)/pp)*100 if pp != 0 else 0
                        color = "#ff4b4b" if d > 0 else "#00ff41" if d < 0 else "#ffffff"
                        m_i = "▲" if d > 0 else "▼" if d < 0 else "─"
                        p_del = urllib.parse.urlencode({"delete_code": t_c, "delete_group": g})
                        st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; background: #262730; padding: 10px 15px; border-radius: 8px; margin-bottom: 4px; border-left: 4px solid {color};">
                            <div style="flex: 2;"><div style="font-size: 0.75rem; color: #888;">{d_code}</div><div style="font-size: 1rem; font-weight: bold;">{row['name']}</div></div>
                            <div style="flex: 1.2; text-align: center; font-size: 1.15rem; font-weight: 800;">{cp:.2f}</div>
                            <div style="flex: 1.8; text-align: right; display: flex; align-items: center; justify-content: flex-end; gap: 12px;">
                                <div style="color: {color}; font-size: 0.85rem;"><b>{m_i} {abs(d):.2f}</b><br><small>({p:+.2f}%)</small></div>
                                <a href="./?{p_del}" target="_self" style="text-decoration: none; color: #666; font-size: 1.2rem;">×</a>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        success = True; break
                if not success: st.caption(f"⏳ {d_code} {row['name']} 數據結算中...")
            except: continue

st.divider()

# --- 5. 雲端筆記區 ---
st.header("📝 雲端筆記")
with st.form("note_form_final", clear_on_submit=True):
    n_t = st.text_input("主題")
    n_k = st.text_input("標籤")
    n_c = st.text_area("內容")
    if st.form_submit_button("💾 儲存筆記"):
        if n_t:
            new_n = pd.DataFrame([{"title": n_t, "tags": n_k, "content": n_c, "date": datetime.now().strftime("%Y-%m-%d")}])
            conn.update(spreadsheet=SP_URL, worksheet="notes", data=pd.concat([notes_df, new_n], ignore_index=True))
            st.cache_data.clear()
            st.rerun()

if not notes_df.empty:
    for _, n in notes_df.iloc[::-1].iterrows():
        with st.expander(f"📌 {n['title']} ({n['date']})"):
            st.write(f"**標籤：** {n['tags']}")
            st.write(n['content'])
            
            # 刪除筆記按鈕
            n_del_params = urllib.parse.urlencode({"delete_note_title": n['title'], "delete_note_date": n['date']})
            st.markdown(f"""
                <div style="text-align: right;">
                    <a href="./?{n_del_params}" target="_self" style="text-decoration: none; background-color: #ff4b4b; color: white; padding: 5px 10px; border-radius: 5px; font-size: 0.8rem;">🗑️ 刪除此筆記</a>
                </div>
            """, unsafe_allow_html=True)
