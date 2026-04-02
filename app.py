import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 網頁基本設定 (設定為 Wide 模式)
st.set_page_config(page_title="台股投資戰情室", layout="wide")

# 介面美化 CSS (修正手機 columns 堆疊與 metric 顯示)
st.markdown("""
<style>
    [data-testid="stMetricDelta"] svg { display: none; }
    
    /* 核心修復：強制在手機上不要將 Columns 散開 */
    @media (max-width: 640px) {
        div[data-testid="stBlock"] div[data-testid="column"] {
            min-width: unset !important;
            flex: 1 1 auto !important;
            width: fit-content !important;
        }
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
c_t, c_s = st.columns([6, 1])
with c_t: st.title("🇹🇼 台股投資戰情室 3.0")
with c_s: 
    if st.button("🔄 同步"):
        st.cache_data.clear()
        st.rerun()

# --- 2. 大盤與情緒 (修正為 Wide 排版) ---
try:
    twii = yf.Ticker("^TWII")
    t_hist = twii.history(period="10d")
    if not t_hist.empty:
        now, prev = t_hist.iloc[-1], t_hist.iloc[-2]
        diff, pct = now['Close'] - prev['Close'], (now['Close'] - prev['Close']) / prev['Close'] * 100
        icon = "🔴" if diff > 0 else "🟢"
        
        avg_vol = t_hist['Volume'].tail(5).mean()
        v_ratio = now['Volume'] / avg_vol
        if pct > 0.5 and v_ratio > 1.1: mood = "🔥 多方攻擊"
        elif pct < -0.5 and v_ratio > 1.1: mood = "😨 恐慌殺盤"
        elif abs(pct) < 0.2: mood = "💤 盤整縮量"
        else: mood = "⚖️ 多空拉鋸"

        col1, col2, col3 = st.columns(3)
        col1.metric("加權指數", f"{now['Close']:,.0f}", f"{icon} {diff:+.2f} ({pct:+.2f}%)")
        col2.metric("市場情緒", mood, f"量能比: {v_ratio:.2f}x")
        col3.metric("更新時間", datetime.now().strftime('%H:%M:%S'), "")
except:
    pass

st.divider()

# --- 3. 管理區 (摺疊顯示) ---
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
            if target_g_del != "請選擇":
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

# --- 4. 個股清單 (核心修復：使用 HTML/CSS 鎖定排版) ---
if stocks_df is not None:
    for g in stocks_df['group'].unique():
        st.subheader(f"📁 {g}")
        sub = stocks_df[stocks_df['group'] == g]
        
        # 電腦版控制：使用大一點的 Columns 比例來包裝 HTML
        # 手機版控制：在 st.markdown 裡面解決

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
                        
                        # --- 終極優化：將資訊與刪除鍵「鎖在同一列 HTML」內 ---
                        # 電腦版使用 st.columns 來防止卡片無限拉長
                        info_col, del_col = st.columns([8, 1])
                        
                        with info_col:
                            # 資訊卡片 HTML (代碼、名稱、現價、漲跌)
                            st.markdown(f"""
                            <div style="display: flex; justify-content: space-between; align-items: center; background: #262730; padding: 10px 15px; border-radius: 8px; margin-bottom: 2px; border-left: 4px solid {color}; border-right: 1px solid #444;">
                                <div style="flex: 2;">
                                    <div style="font-size: 0.8rem; color: #888; line-height: 1;">{t_c}</div>
                                    <div style="font-size: 1.05rem; font-weight: 700;">{row['name']}</div>
                                </div>
                                <div style="flex: 1.5; text-align: center; font-size: 1.15rem; font-weight: 800;">{cp:.2f}</div>
                                <div style="flex: 1.5; text-align: right; color: {color}; font-size: 0.9rem;">
                                    <b>{m_icon} {abs(d):.2f}</b><br><small>({p:+.2f}%)</small>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        with del_col:
                            # 變成半透明的小文字按鈕，緊貼在卡片右邊，但跟它鎖在同一列
                            # 我們強制給予 padding 防止手機版自動偏移
                            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True) 
                            if st.button("×", key=f"del_{g}_{t_c}", help="移除此股"):
                                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=stocks_df[~((stocks_df['group'] == g) & (stocks_df['code'] == t_c))])
                                st.cache_data.clear()
                                st.rerun()
                        success = True
                        break
            except:
                st.caption(f"{t_c} 載入中...")

st.divider()
st.header("📝 雲端筆記")
with st.form("note_persistent", clear_on_submit=True):
    n_t, n_k = st.text_input("主題"), st.text_input("標籤")
    n_c = st.text_area("內容")
    if st.form_submit_button("儲存筆記"):
        if n_t:
            new_n = pd.DataFrame([{"title": n_t, "tags": n_k, "content": n_c, "date": datetime.now().strftime("%Y-%m-%d")}])
            updated = pd.concat([notes_df, new_n], ignore_index=True)
            conn.update(spreadsheet=SP_URL, worksheet="notes", data=updated)
            st.cache_data.clear()
            st.rerun()

if notes_df is not None and not notes_df.empty:
    for _, n in notes_df.iloc[::-1].iterrows():
        with st.expander(f"📌 {n['title']} ({n['date']})"):
            st.write(n['content'])
