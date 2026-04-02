import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import urllib.parse

# 1. 網頁基本設定
st.set_page_config(page_title="台股投資戰情室 3.0", layout="wide")
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_html=True)

# 2. 連接 Google Sheets
SP_URL = "https://docs.google.com/spreadsheets/d/1pSVEg5J_-tg0wetPxNUVb9cU6kapUL_NIEV_Xz84PDM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- A. 處理所有刪除與操作請求 ---
query_params = st.query_params

# 刪除個股
if "delete_code" in query_params:
    try:
        d_c, d_g = str(query_params["delete_code"]).strip(), str(query_params["delete_group"]).strip()
        tmp = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl=0)
        tmp['code'] = tmp['code'].astype(str).str.replace(".0", "", regex=False).str.strip()
        updated = tmp[~((tmp['group'] == d_g) & (tmp['code'] == d_c))]
        conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
        st.query_params.clear()
        st.rerun()
    except: st.query_params.clear()

# 刪除筆記
if "delete_note_title" in query_params:
    try:
        dn_t, dn_d = query_params["delete_note_title"], query_params["delete_note_date"]
        n_tmp = conn.read(spreadsheet=SP_URL, worksheet="notes", ttl=0)
        n_updated = n_tmp[~((n_tmp['title'] == dn_t) & (n_tmp['date'] == dn_d))]
        conn.update(spreadsheet=SP_URL, worksheet="notes", data=n_updated)
        st.query_params.clear()
        st.rerun()
    except: st.query_params.clear()

# --- B. 讀取與洗滌數據 ---
@st.cache_data(ttl=5)
def load_all_v6():
    try:
        s_raw = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl=0)
        n_raw = conn.read(spreadsheet=SP_URL, worksheet="notes", ttl=0)
        s_df = s_raw.copy() if s_raw is not None else pd.DataFrame(columns=["group", "code", "name"])
        s_df['code'] = s_df['code'].astype(str).str.replace(".0", "", regex=False).str.strip()
        s_df = s_df[~s_df['code'].isin(['nan', 'NaN', 'None', '', '9999'])]
        n_df = n_raw.dropna(subset=['title']).copy() if n_raw is not None else pd.DataFrame()
        return s_df, n_df
    except: return pd.DataFrame(columns=["group", "code", "name"]), pd.DataFrame()

stocks_df, notes_df = load_all_v6()

# --- 1. 頂部導覽與大盤 ---
c_title, c_sync = st.columns([5, 1])
with c_title: st.title("🇹🇼 台股投資戰情室 3.0")
with c_sync:
    if st.button("🔄 同步雲端", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

try:
    twii = yf.Ticker("^TWII")
    t_h = twii.history(period="3d")
    if not t_h.empty:
        now_v, pre_v = t_h.iloc[-1]['Close'], t_h.iloc[-2]['Close']
        diff, pct = now_v - pre_v, (now_v - pre_v)/pre_v * 100
        icon = "🔴" if diff > 0 else "🟢"
        c1, c2, c3 = st.columns(3)
        c1.metric("加權指數", f"{now_v:,.0f}", f"{icon} {diff:+.2f} ({pct:+.2f}%)")
        c2.metric("數據狀態", "✅ 已連線", f"更新: {datetime.now().strftime('%H:%M')}")
        c3.metric("市場情緒", "波動觀察中", "")
except: pass

st.divider()

# --- 2. 核心管理中心 (補回類別管理) ---
with st.expander("⚙️ 系統管理中心", expanded=False):
    # 第一列：新增個股
    with st.container(border=True):
        st.markdown("#### 🚀 新增個股")
        g_opts = list(stocks_df['group'].unique()) if not stocks_df.empty else []
        ca1, ca2, ca3 = st.columns([2, 1, 1])
        with ca1: t_g = st.selectbox("選擇群組", g_opts if g_opts else ["(請先建立群組)"], key="sel_g")
        with ca2: i_c = st.text_input("代碼", key="in_c")
        with ca3: i_n = st.text_input("名稱", key="in_n")
        if st.button("🌟 存入自選清單", use_container_width=True, type="primary"):
            if i_c and t_g != "(請先建立群組)":
                clean = stocks_df[~((stocks_df['group'] == t_g) & (stocks_df['code'] == "9999"))]
                new_row = pd.DataFrame([{"group": t_g, "code": str(i_c).strip(), "name": i_n}])
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=pd.concat([clean, new_row]))
                st.cache_data.clear()
                st.rerun()

    # 第二列：類別管理 (補回這塊)
    col_l, col_r = st.columns(2)
    with col_l:
        with st.container(border=True):
            st.markdown("#### 📂 新增群組(類別)")
            new_g_name = st.text_input("新群組名稱", key="new_g_f")
            if st.button("建立新群組", use_container_width=True):
                if new_g_name:
                    new_ph = pd.DataFrame([{"group": new_g_name, "code": "9999", "name": "PH"}])
                    conn.update(spreadsheet=SP_URL, worksheet="stocks", data=pd.concat([stocks_df, new_ph]))
                    st.cache_data.clear()
                    st.rerun()
    with col_r:
        with st.container(border=True):
            st.markdown("#### 🗑️ 刪除群組(類別)")
            del_g_target = st.selectbox("要刪除的群組", ["(選擇群組)"] + g_opts, key="del_g_f")
            if st.button("確認刪除整個群組", use_container_width=True):
                if del_g_target != "(選擇群組)":
                    remained = stocks_df[stocks_df['group'] != del_g_target]
                    conn.update(spreadsheet=SP_URL, worksheet="stocks", data=remained)
                    st.cache_data.clear()
                    st.rerun()

# --- 3. 市場情緒資訊區 (補回這塊) ---
st.header("📊 市場情緒觀察")
try:
    c_m1, c_m2, c_m3 = st.columns(3)
    # 這裡可以串接更多 Yahoo Finance 的指標，目前先以台指期或權值股作為情緒基準
    vix = yf.Ticker("^VIX").history(period="1d").iloc[-1]['Close']
    c_m1.info(f"恐慌指數 (VIX): {vix:.2f}")
    c_m2.success("法人動向: 待同步")
    c_m3.warning("融資餘額: 數據更新中")
except:
    st.caption("情緒數據整理中...")

st.divider()

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
with st.form("note_form_v6", clear_on_submit=True):
    n_t, n_k = st.text_input("主題"), st.text_input("標籤")
    n_c = st.text_area("內容")
    if st.form_submit_button("💾 儲存筆記"):
        if n_t:
            new_n = pd.DataFrame([{"title": n_t, "tags": n_k, "content": n_c, "date": datetime.now().strftime("%Y-%m-%d")}])
            conn.update(spreadsheet=SP_URL, worksheet="notes", data=pd.concat([notes_df, new_n], ignore_index=True))
            st.cache_data.clear(); st.rerun()

if not notes_df.empty:
    for _, n in notes_df.iloc[::-1].iterrows():
        with st.expander(f"📌 {n['title']} ({n['date']})"):
            st.write(f"**標籤：** {n['tags']}\n\n{n['content']}")
            n_del_p = urllib.parse.urlencode({"delete_note_title": n['title'], "delete_note_date": n['date']})
            st.markdown(f'<div style="text-align: right;"><a href="./?{n_del_p}" target="_self" style="text-decoration: none; background: #ff4b4b; color: white; padding: 5px 12px; border-radius: 6px; font-size: 0.8rem;">🗑️ 刪除筆記</a></div>', unsafe_allow_html=True)
