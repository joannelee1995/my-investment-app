import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import urllib.parse

# 網頁基本設定 (Wide 模式)
st.set_page_config(page_title="台股投資戰情室", layout="wide")

# 隱藏預設箭頭與 metric 樣式
st.markdown("""
<style>
    [data-testid="stMetricDelta"] svg { display: none; }
    /* 強制設定 Metric 樣式 */
    [data-testid="metric-container"] { background-color: #1e2129; padding: 10px; border-radius: 8px; border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

# 1. 連接 Google Sheets
SP_URL = "https://docs.google.com/spreadsheets/d/1pSVEg5J_-tg0wetPxNUVb9cU6kapUL_NIEV_Xz84PDM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- A. 核心邏輯：處理網址參數刪除請求 ---
# 取得目前的網址參數
query_params = st.query_params

if "delete_code" in query_params and "delete_group" in query_params:
    del_code = query_params["delete_code"]
    del_group = query_params["delete_group"]
    
    # 執行刪除動作 (需先載入資料)
    try:
        tmp_df = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl=0)
        tmp_df['code'] = tmp_df['code'].astype(str).str.replace(".0", "", regex=False).str.strip()
        
        # 精準篩選掉要刪除的個股
        updated_df = tmp_df[~((tmp_df['group'] == del_group) & (tmp_df['code'] == del_code))]
        
        # 寫入雲端
        conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated_df)
        
        # 刪除成功後，清除網址參數並重整，避免重複刪除
        st.query_params.clear()
        st.success(f"已移除 {del_code}，正在重新載入...")
        st.rerun()
    except:
        st.error("刪除失敗，請稍後再試。")
        st.query_params.clear()

# --- B. 讀取資料 ---
@st.cache_data(ttl=10) # 預設 10 秒緩存
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

# 頂部導覽
c_t, c_s = st.columns([5, 1])
with c_t: st.title("🇹🇼 台股投資戰情室 3.0")
with c_s: 
    if st.button("🔄 同步"):
        st.cache_data.clear()
        st.rerun()

# --- 2. 大盤摘要 (維持不變) ---
try:
    twii = yf.Ticker("^TWII")
    t_hist = twii.history(period="5d")
    if not t_hist.empty:
        now, prev = t_hist.iloc[-1], t_hist.iloc[-2]
        diff, pct = now['Close'] - prev['Close'], (now['Close'] - prev['Close']) / prev['Close'] * 100
        icon = "🔴" if diff > 0 else "🟢"
        
        c1, c2, c3 = st.columns(3)
        c1.metric("加權指數", f"{now['Close']:,.0f}", f"{icon} {diff:+.0f} ({pct:+.2f}%)")
        c2.metric("當前盤勢", "分析中...", "")
        c3.metric("最後更新", datetime.now().strftime('%H:%M:%S'), "")
except:
    pass

st.divider()

# --- 3. 管理區 (維持不變) ---
with st.expander("⚙️ 管理中心", expanded=False):
    if stocks_df is not None:
        st.write("**新增個股/ETF**")
        col_g = st.selectbox("存入群組", stocks_df['group'].unique())
        c_s1, c_s2 = st.columns(2)
        in_c, in_n = c_s1.text_input("代碼 (例: 0050)"), c_s2.text_input("名稱")
        if st.button("🚀 存入雲端"):
            if in_c and col_g:
                # 移除 placeholder
                clean = stocks_df[~((stocks_df['group'] == col_g) & (stocks_df['code'] == "9999"))]
                new_s = pd.DataFrame([{"group": col_g, "code": str(in_c).strip(), "name": in_n}])
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=pd.concat([clean, new_s]))
                st.cache_data.clear()
                st.rerun()
        st.write("---")
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

# --- 4. 個股清單 (終極優化：完全捨棄 st.columns，使用純 HTML 鎖定一行) ---
if stocks_df is not None:
    for g in stocks_df['group'].unique():
        st.subheader(f"📁 {g}")
        sub = stocks_df[stocks_df['group'] == g]
        
        # 為了避免電腦版卡片無限拉長，我們外面還是包一層 st.columns，但比例設得很緊
        # 這個 column 比例在電腦上看起來很棒，在手機上即使被拆開也沒關係，因為內容物已經鎖定了
        main_col, _ = st.columns([10, 1]) 
        
        with main_col:
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
                            
                            # 建構刪除的 URL 連結 (核心技巧)
                            params = urllib.parse.urlencode({"delete_code": t_c, "delete_group": g})
                            del_url = f"./?{params}"
                            
                            # --- 終極優化：將資訊與 ❌ 完全鎖在同一個 HTML <div> 內 ---
                            # 不再使用 st.columns 包裝 × 按鈕
                            st.markdown(f"""
                            <div style="display: flex; justify-content: space-between; align-items: center; background: #262730; padding: 10px 15px; border-radius: 8px; margin-bottom: 3px; border-left: 4px solid {color}; border-right: 1px solid #444; position: relative;">
                                <div style="flex: 2;">
                                    <div style="font-size: 0.8rem; color: #888; line-height: 1.1;">{t_c}</div>
                                    <div style="font-size: 1.05rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{row['name']}</div>
                                </div>
                                <div style="flex: 1.2; text-align: center; font-size: 1.15rem; font-weight: 800;">{cp:.2f}</div>
                                <div style="flex: 1.8; text-align: right; display: flex; align-items: center; justify-content: flex-end; gap: 10px;">
                                    <div style="color: {color}; font-size: 0.9rem; line-height: 1.2;">
                                        <b>{m_icon} {abs(d):.2f}</b><br><small>({p:+.2f}%)</small>
                                    </div>
                                    <a href="{del_url}" target="_self" style="text-decoration: none; color: #555; font-size: 1.2rem; font-weight: bold; padding: 0 5px; cursor: pointer; border-radius: 4px;" onmouseover="this.style.color='#ff4b4b'; this.style.background='#444';" onmouseout="this.style.color='#555'; this.style.background='transparent';">×</a>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            success = True
                            break
                    if not success:
                        st.caption(f"{t_c} 暫無資料")
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
