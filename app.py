import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import urllib.parse

# 1. 基本設定
st.set_page_config(page_title="台股投資戰情室", layout="wide")

# 隱藏預設元件樣式
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_html=True)

# 2. 連接 Google Sheets
SP_URL = "https://docs.google.com/spreadsheets/d/1pSVEg5J_-tg0wetPxNUVb9cU6kapUL_NIEV_Xz84PDM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- A. 處理網址刪除參數 (維持邏輯) ---
query_params = st.query_params
if "delete_code" in query_params:
    d_c, d_g = query_params["delete_code"], query_params["delete_group"]
    try:
        tmp = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl=0)
        # 強制轉字串處理
        tmp['code'] = tmp['code'].astype(str).str.replace(".0", "", regex=False).str.strip()
        updated = tmp[~((tmp['group'] == d_g) & (tmp['code'] == d_c))]
        conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
        st.query_params.clear()
        st.rerun()
    except:
        st.query_params.clear()

# --- B. 強大防呆讀取邏輯 (修復 nan 的關鍵) ---
@st.cache_data(ttl=10)
def load_data_safe():
    try:
        # 分開讀取
        s_raw = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl=0)
        n_raw = conn.read(spreadsheet=SP_URL, worksheet="notes", ttl=0)
        
        # 處理股票：徹底剔除空白與無效值
        if s_raw is not None and not s_raw.empty:
            s_df = s_raw.dropna(subset=['group', 'code']).copy() # 關鍵：code 為空的一律丟掉
            s_df['code'] = s_df['code'].astype(str).str.replace(".0", "", regex=False).str.strip()
            s_df = s_df[s_df['code'] != "nan"] # 排除 nan 字串
            def fix_code(x):
                if str(x).isdigit() and len(str(x)) < 4: return str(x).zfill(4)
                return str(x)
            s_df['code'] = s_df['code'].apply(fix_code)
        else:
            s_df = pd.DataFrame(columns=["group", "code", "name"])

        # 處理筆記：剔除標題為空的列
        if n_raw is not None and not n_raw.empty:
            n_df = n_raw.dropna(subset=['title']).copy()
        else:
            n_df = pd.DataFrame(columns=["title", "tags", "content", "date"])
            
        return s_df, n_df
    except:
        return pd.DataFrame(columns=["group", "code", "name"]), pd.DataFrame(columns=["title", "tags", "content", "date"])

stocks_df, notes_df = load_data_safe()

# 標題區
c_t, c_s = st.columns([5, 1])
with c_t: st.title("🇹🇼 台股投資戰情室 3.0")
with c_s: 
    if st.button("🔄 同步"):
        st.cache_data.clear()
        st.rerun()

# --- 2. 大盤摘要 (增加錯誤保護) ---
try:
    twii = yf.Ticker("^TWII")
    t_h = twii.history(period="5d")
    if not t_h.empty:
        now, prev = t_h.iloc[-1], t_h.iloc[-2]
        diff, pct = now['Close'] - prev['Close'], (now['Close'] - prev['Close']) / prev['Close'] * 100
        icon = "🔴" if diff > 0 else "🟢"
        c1, c2, c3 = st.columns(3)
        c1.metric("加權指數", f"{now['Close']:,.0f}", f"{icon} {diff:+.0f} ({pct:+.2f}%)")
        
        # 市場情緒分析
        v_r = now['Volume'] / t_h['Volume'].mean()
        mood = "⚖️ 區間震盪"
        if pct > 0.5 and v_r > 1.1: mood = "🔥 多方攻擊"
        elif pct < -0.5 and v_r > 1.1: mood = "😨 恐慌殺盤"
        c2.metric("市場情緒", mood, f"量能比: {v_r:.2f}x")
        c3.metric("最後更新", datetime.now().strftime('%H:%M:%S'), "")
except:
    st.info("大盤連線中...")

st.divider()

# --- 3. 管理區 (官方卡片美化版) ---
with st.expander("⚙️ 管理中心", expanded=False):
    with st.container(border=True):
        st.markdown("#### 🚀 新增個股 / ETF")
        g_list = stocks_df['group'].unique() if not stocks_df.empty else []
        c_add1, c_add2, c_add3 = st.columns([2, 1, 1])
        with c_add1:
            target_g = st.selectbox("目標群組", g_list if len(g_list)>0 else ["請先建立群組"], key="sel_g")
        with c_add2:
            in_c = st.text_input("代碼", placeholder="0050", key="in_c")
        with c_add3:
            in_n = st.text_input("名稱", placeholder="名稱", key="in_n")
        if st.button("🌟 存入雲端", use_container_width=True, type="primary"):
            if in_c and target_g != "請先建立群組":
                clean = stocks_df[~((stocks_df['group'] == target_g) & (stocks_df['code'] == "9999"))]
                new_data = pd.concat([clean, pd.DataFrame([{"group": target_g, "code": str(in_c).strip(), "name": in_n}])])
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=new_data)
                st.cache_data.clear()
                st.rerun()
    # (群組建立/刪除維持不變...)
# --- 4. 個股清單 (加入強制顯示過濾) ---
if not stocks_df.empty:
    # 確保群組不為 nan
    valid_groups = [g for g in stocks_df['group'].unique() if pd.notna(g) and str(g) != 'nan']
    
    for g in valid_groups:
        st.subheader(f"📁 {g}")
        sub = stocks_df[stocks_df['group'] == g]
        
        main_col, _ = st.columns([10, 1]) 
        with main_col:
            for _, row in sub.iterrows():
                t_c = str(row['code']).strip()
                
                # 硬核檢查：如果是 nan、9999、或是空值，絕對不顯示
                if t_c.lower() in ["nan", "9999", "", "none"] or len(t_c) < 2:
                    continue
                
                try:
                    # 抓取 Yahoo 資料
                    success = False
                    for suffix in [".TW", ".TWO"]:
                        tk = yf.Ticker(f"{t_c}{suffix}")
                        # 使用 fast_info 提升速度並減少報錯
                        h = tk.history(period="2d")
                        if not h.empty:
                            cp, pp = h.iloc[-1]['Close'], h.iloc[0]['Close']
                            # 排除抓到空價格的情況
                            if pd.isna(cp): continue
                            
                            d, p = cp - pp, ((cp - pp)/pp)*100
                            color = "#ff4b4b" if d > 0 else "#00ff41" if d < 0 else "#ffffff"
                            m_icon = "▲" if d > 0 else "▼" if d < 0 else "─"
                            
                            # 刪除連結
                            params = urllib.parse.urlencode({"delete_code": t_c, "delete_group": g})
                            
                            st.markdown(f"""
                            <div style="display: flex; justify-content: space-between; align-items: center; background: #262730; padding: 10px 15px; border-radius: 8px; margin-bottom: 3px; border-left: 4px solid {color};">
                                <div style="flex: 2;">
                                    <div style="font-size: 0.75rem; color: #888;">{t_c}</div>
                                    <div style="font-size: 1rem; font-weight: 700;">{row['name']}</div>
                                </div>
                                <div style="flex: 1.2; text-align: center; font-size: 1.1rem; font-weight: 800;">{cp:.2f}</div>
                                <div style="flex: 1.8; text-align: right; display: flex; align-items: center; justify-content: flex-end; gap: 12px;">
                                    <div style="color: {color}; font-size: 0.85rem;"><b>{m_icon} {abs(d):.2f}</b><br><small>({p:+.2f}%)</small></div>
                                    <a href="./?{params}" target="_self" style="text-decoration: none; color: #666; font-size: 1.2rem; font-weight: bold; padding: 0 5px;">×</a>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            success = True
                            break
                    if not success:
                        pass # 抓不到就不顯示，保持畫面乾淨
                except:
                    continue

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
