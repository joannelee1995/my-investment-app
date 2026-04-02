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

# --- B. 終極暴力讀取邏輯 ---
@st.cache_data(ttl=5)
def load_data_ultimate():
    try:
        s_raw = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl=0)
        n_raw = conn.read(spreadsheet=SP_URL, worksheet="notes", ttl=0)
        
        if s_raw is not None and not s_raw.empty:
            df = s_raw.copy()
            # 1. 移除全空的列
            df = df.dropna(subset=['code'])
            # 2. 強制轉為字串並去除 .0
            df['code'] = df['code'].astype(str).str.replace(".0", "", regex=False).str.strip()
            # 3. 排除 nan 或無效字串
            df = df[~df['code'].isin(['nan', 'NaN', 'None', '', '9999'])]
            # 4. 補零邏輯
            df['code'] = df['code'].apply(lambda x: x.zfill(4) if (x.isdigit() and len(x) < 4) else x)
            return df, n_raw.dropna(subset=['title']) if n_raw is not None else pd.DataFrame()
        return pd.DataFrame(columns=["group", "code", "name"]), pd.DataFrame()
    except:
        return pd.DataFrame(columns=["group", "code", "name"]), pd.DataFrame()

stocks_df, notes_df = load_data_ultimate()

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
        c2.metric("市場情緒", "📊 數據連線正常", "")
        c3.metric("最後更新", datetime.now().strftime('%H:%M:%S'), "")
except:
    pass

st.divider()

# --- 3. 管理中心 (維持美化版) ---
with st.expander("⚙️ 管理中心", expanded=False):
    with st.container(border=True):
        st.markdown("#### 🚀 新增個股 / ETF")
        g_opts = list(stocks_df['group'].unique()) if not stocks_df.empty else []
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: t_g = st.selectbox("目標群組", g_opts if g_opts else ["請先建立"], key="add_g")
        with c2: i_c = st.text_input("代碼", key="in_c")
        with c3: i_n = st.text_input("名稱", key="in_n")
        if st.button("🌟 存入雲端", use_container_width=True, type="primary"):
            if i_c and t_g != "請先建立":
                # 移除該組的 PH
                clean = stocks_df[~((stocks_df['group'] == t_g) & (stocks_df['code'] == "9999"))]
                new_row = pd.DataFrame([{"group": t_g, "code": str(i_c).strip(), "name": i_n}])
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=pd.concat([clean, new_row]))
                st.cache_data.clear()
                st.rerun()

# --- 4. 個股清單 (強制渲染版) ---
if not stocks_df.empty:
    for g in stocks_df['group'].unique():
        st.subheader(f"📁 {g}")
        sub = stocks_df[stocks_df['group'] == g]
        m_col, _ = st.columns([10, 1])
        with m_col:
            for _, row in sub.iterrows():
                t_c = str(row['code']).strip()
                # 雙重檢查：不符合台灣股票格式的直接跳過
                if len(t_c) < 2 or t_c.lower() == "nan": continue
                
                try:
                    # 同時嘗試 .TW 和 .TWO
                    success = False
                    for suffix in [".TW", ".TWO"]:
                        tk = yf.Ticker(f"{t_c}{suffix}")
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
                except: continue
