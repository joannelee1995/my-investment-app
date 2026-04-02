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

# --- B. 讀取資料 ---
@st.cache_data(ttl=5)
def load_and_clean_final():
    try:
        s_raw = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl=0)
        n_raw = conn.read(spreadsheet=SP_URL, worksheet="notes", ttl=0)
        if s_raw is not None and not s_raw.empty:
            df = s_raw.copy()
            df['code'] = df['code'].astype(str).str.replace(".0", "", regex=False).str.strip()
            df = df[~df['code'].isin(['nan', 'NaN', 'None', '', '9999'])]
        else:
            df = pd.DataFrame(columns=["group", "code", "name"])
        return df, n_raw if n_raw is not None else pd.DataFrame()
    except:
        return pd.DataFrame(columns=["group", "code", "name"]), pd.DataFrame()

stocks_df, notes_df = load_and_clean_final()

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
        now_v = t_h.iloc[-1]['Close']
        pre_v = t_h.iloc[-2]['Close']
        diff, pct = now_v - pre_v, (now_v - pre_v)/pre_v * 100
        icon = "🔴" if diff > 0 else "🟢"
        c1, c2, c3 = st.columns(3)
        c1.metric("加權指數", f"{now_v:,.0f}", f"{icon} {diff:+.2f} ({pct:+.2f}%)")
        c2.metric("連線狀態", "✅ 正常", "")
        c3.metric("更新時間", datetime.now().strftime('%H:%M:%S'), "")
except:
    pass

st.divider()

# --- 3. 管理中心 (省略, 維持之前美化版代碼即可) ---
with st.expander("⚙️ 管理中心", expanded=False):
    st.info("可在此新增或刪除自選股與群組")

# --- 4. 個股清單 (防 nan 核心修復版) ---
if not stocks_df.empty:
    for g in stocks_df['group'].unique():
        if pd.isna(g) or str(g).lower() == 'nan': continue
        st.subheader(f"📁 {g}")
        sub = stocks_df[stocks_df['group'] == g]
        m_col, _ = st.columns([10, 1])
        with m_col:
            for _, row in sub.iterrows():
                t_c = str(row['code']).strip()
                if t_c in ["9999", "nan", "None", ""]: continue
                
                try:
                    success = False
                    d_code = t_c.zfill(4) if (t_c.isdigit() and len(t_c) < 4) else t_c
                    
                    for suffix in [".TW", ".TWO"]:
                        tk = yf.Ticker(f"{d_code}{suffix}")
                        # 先試 history，不行就試 fast_info
                        h = tk.history(period="2d")
                        
                        cp = 0.0
                        if not h.empty and not pd.isna(h.iloc[-1]['Close']):
                            cp = h.iloc[-1]['Close']
                            pp = h.iloc[0]['Close']
                        else:
                            # 備援：嘗試抓取最後成交價
                            cp = tk.fast_info.get('lastPrice', 0)
                            pp = tk.fast_info.get('previousClose', cp)
                        
                        # 只有在價格大於 0 且不是 nan 的情況下才顯示
                        if cp > 0 and not pd.isna(cp):
                            d, p = cp - pp, ((cp - pp)/pp)*100 if pp != 0 else 0
                            color = "#ff4b4b" if d > 0 else "#00ff41" if d < 0 else "#ffffff"
                            m_i = "▲" if d > 0 else "▼" if d < 0 else "─"
                            params = urllib.parse.urlencode({"delete_code": t_c, "delete_group": g})
                            
                            st.markdown(f"""
                            <div style="display: flex; justify-content: space-between; align-items: center; background: #262730; padding: 10px 15px; border-radius: 8px; margin-bottom: 4px; border-left: 4px solid {color};">
                                <div style="flex: 2;">
                                    <div style="font-size: 0.75rem; color: #888;">{d_code}</div>
                                    <div style="font-size: 1rem; font-weight: bold;">{row['name']}</div>
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
                        st.markdown(f"""
                        <div style="background: #1a1c22; padding: 10px; border-radius: 8px; margin-bottom: 4px; color: #555; font-size: 0.9rem;">
                            ⏳ {d_code} {row['name']} 資料結算中...
                        </div>
                        """, unsafe_allow_html=True)
                except:
                    continue

st.divider()
# --- 5. 筆記區 (維持邏輯) ---
