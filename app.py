import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 網頁基本設定
st.set_page_config(page_title="台股投資戰情室", layout="wide")

# 介面美化 CSS：強制手機版不要把欄位拆得太散
st.markdown("""
<style>
    [data-testid="stMetricDelta"] svg { display: none; }
    .stMetric { background-color: #1e2129; padding: 10px; border-radius: 10px; }
    @media (max-width: 640px) {
        .stock-row { font-size: 14px; margin-bottom: 5px; border-bottom: 1px solid #333; padding-bottom: 5px; }
    }
</style>
""", unsafe_allow_html=True)

# 1. 連接 Google Sheets
SP_URL = "https://docs.google.com/spreadsheets/d/1pSVEg5J_-tg0wetPxNUVb9cU6kapUL_NIEV_Xz84PDM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=15)
def load_data_cached():
    try:
        s_df = conn.read(spreadsheet=SP_URL, worksheet="stocks")
        n_df = conn.read(spreadsheet=SP_URL, worksheet="notes")
        def format_code(x):
            s = str(x).replace(".0", "").strip()
            if s.isdigit() and len(s) < 4: return s.zfill(4)
            return s
        s_df['code'] = s_df['code'].apply(format_code)
        return s_df.dropna(how='all'), n_df.dropna(how='all')
    except:
        return None, None

stocks_df, notes_df = load_data_cached()

# 頂部標題與同步按鈕
c_t, c_s = st.columns([4, 1])
with c_t: st.title("🇹🇼 台股投資戰情室 3.0")
with c_s: 
    if st.button("🔄 同步"):
        st.cache_data.clear()
        st.rerun()

# --- 2. 大盤與市場情緒 (修復版) ---
try:
    twii = yf.Ticker("^TWII")
    t_hist = twii.history(period="10d")
    if not t_hist.empty:
        now, prev = t_hist.iloc[-1], t_hist.iloc[-2]
        diff, pct = now['Close'] - prev['Close'], (now['Close'] - prev['Close']) / prev['Close'] * 100
        icon = "🔴" if diff > 0 else "🟢"
        
        # 市場情緒邏輯：根據漲跌幅與量能判斷
        avg_vol = t_hist['Volume'].tail(5).mean()
        v_ratio = now['Volume'] / avg_vol
        if pct > 0.5 and v_ratio > 1.1: mood = "🔥 多方攻擊"
        elif pct < -0.5 and v_ratio > 1.1: mood = "😨 恐慌殺盤"
        elif abs(pct) < 0.2: mood = "💤 盤整縮量"
        else: mood = "⚖️ 多空拉鋸"

        col1, col2, col3 = st.columns(3)
        col1.metric("加權指數", f"{now['Close']:,.0f}", f"{icon} {diff:+.2f} ({pct:+.2f}%)")
        col2.metric("市場情緒", mood, f"量能比: {v_ratio:.2f}x")
        col3.metric("最後更新", datetime.now().strftime('%H:%M:%S'), "")
except:
    st.info("大盤數據讀取中...")

st.divider()

# --- 3. 管理區 (保持摺疊避免佔空間) ---
with st.expander("⚙️ 管理中心", expanded=False):
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        new_g = st.text_input("新建群組")
        if st.button("建立"):
            if new_g:
                new_row = pd.DataFrame([{"group": new_g, "code": "9999", "name": "PH"}])
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=pd.concat([stocks_df, new_row]))
                st.cache_data.clear()
                st.rerun()
    with m_col2:
        target_g_del = st.selectbox("刪除群組", ["請選擇"] + list(stocks_df['group'].unique()))
        if st.button("確認刪除"):
            conn.update(spreadsheet=SP_URL, worksheet="stocks", data=stocks_df[stocks_df['group'] != target_g_del])
            st.cache_data.clear()
            st.rerun()
    st.write("---")
    target_g = st.selectbox("目標群組", stocks_df['group'].unique())
    c_s1, c_s2 = st.columns(2)
    in_c, in_n = c_s1.text_input("代碼"), c_s2.text_input("名稱")
    if st.button("🚀 存入雲端"):
        if in_c:
            clean = stocks_df[~((stocks_df['group'] == target_g) & (stocks_df['code'] == "9999"))]
            new_s = pd.DataFrame([{"group": target_g, "code": str(in_c).strip(), "name": in_n}])
            conn.update(spreadsheet=SP_URL, worksheet="stocks", data=pd.concat([clean, new_s]))
            st.cache_data.clear()
            st.rerun()

# --- 4. 個股清單 (手機排版優化版) ---
if stocks_df is not None:
    for g in stocks_df['group'].unique():
        st.subheader(f"📁 {g}")
        sub = stocks_df[stocks_df['group'] == g]
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
                        
                        # --- 核心優化：整合卡片與微型刪除鍵 ---
                        # 這裡把比例調成 20:1，讓刪除鍵變得很邊緣
                        card_col, del_col = st.columns([20, 1]) 
                        with card_col:
                            st.markdown(f"""
                            <div style="display: flex; justify-content: space-between; align-items: center; background: #1e2129; padding: 8px 12px; border-radius: 6px; margin-bottom: 4px; border-left: 3px solid {color};">
                                <div style="flex: 1.2;">
                                    <div style="font-size: 0.7rem; color: #888; line-height: 1;">{t_c}</div>
                                    <div style="font-size: 0.95rem; font-weight: 600;">{row['name']}</div>
                                </div>
                                <div style="flex: 1; text-align: center; font-size: 1.05rem; font-weight: 700;">{cp:.2f}</div>
                                <div style="flex: 1.2; text-align: right; color: {color}; font-size: 0.85rem; line-height: 1.1;">
                                    <b>{m_icon} {abs(d):.2f}</b><br><span style="font-size: 0.75rem;">({p:+.2f}%)</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        with del_col:
                            # 移除紅色背景，改用透明的小叉叉
                            if st.button("×", key=f"del_{g}_{t_c}", help="移除"):
                                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=stocks_df[~((stocks_df['group'] == g) & (stocks_df['code'] == t_c))])
                                st.cache_data.clear()
                                st.rerun()
                        success = True
                        break
            except:
                continue

st.divider()
st.header("📝 雲端筆記")
with st.form("note_v5", clear_on_submit=True):
    n_t, n_k = st.text_input("主題"), st.text_input("標籤")
    n_c = st.text_area("內容")
    if st.form_submit_button("儲存筆記"):
        if n_t:
            new_n = pd.DataFrame([{"title": n_t, "tags": n_k, "content": n_c, "date": datetime.now().strftime("%Y-%m-%d")}])
            conn.update(spreadsheet=SP_URL, worksheet="notes", data=pd.concat([notes_df, new_n]))
            st.cache_data.clear()
            st.rerun()

if notes_df is not None and not notes_df.empty:
    for _, n in notes_df.iloc[::-1].iterrows():
        with st.expander(f"📌 {n['title']} ({n['date']})"):
            st.write(n['content'])
