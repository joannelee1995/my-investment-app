import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 基本網頁設定
st.set_page_config(page_title="台股永久戰情室", layout="wide")

# 隱藏預設箭頭
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_html=True)

# 1. 連接 Google Sheets
# 你的試算表網址
SP_URL = "https://docs.google.com/spreadsheets/d/1pSVEg5J_-tg0wetPxNUVb9cU6kapUL_NIEV_Xz84PDM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# 讀取雲端資料函數
def load_cloud_data():
    try:
        s_df = conn.read(spreadsheet=SP_URL, worksheet="stocks")
        n_df = conn.read(spreadsheet=SP_URL, worksheet="notes")
        return s_df.dropna(how='all'), n_df.dropna(how='all')
    except:
        # 若分頁不存在或讀取失敗，回傳空資料表
        return pd.DataFrame(columns=["group", "code", "name"]), pd.DataFrame(columns=["title", "tags", "content", "date"])

stocks_df, notes_df = load_cloud_data()

# --- 2. 大盤與動態焦點 ---
st.title("🇹🇼 台股永久戰情室 3.0")
try:
    twii = yf.Ticker("^TWII")
    t_hist = twii.history(period="10d")
    if not t_hist.empty:
        now = t_hist.iloc[-1]
        prev = t_hist.iloc[-2]
        diff = now['Close'] - prev['Close']
        pct = (diff / prev['Close']) * 100
        
        if pct >= 1.0: stm = "📈 強勢"
        elif 0.2 <= pct < 1.0: stm = "↗️ 上漲"
        elif -0.2 < pct < 0.2: stm = "⚖️ 平盤"
        elif -1.0 < pct <= -0.2: stm = "↘️ 回檔"
        else: stm = "📉 跌幅較大"
        
        icon = "🔴" if diff > 0 else "🟢"
        c1, c2, c3 = st.columns(3)
        c1.metric("加權指數", f"{now['Close']:,.2f}", f"{icon} {diff:+.2f} ({pct:+.2f}%)")
        c2.metric("當前盤勢", stm, f"趨勢: {icon}")
        c3.metric("最後更新時間", datetime.now().strftime('%H:%M:%S'), "")

        st.divider()
        st.header("📰 今日財經焦點摘要")
        
        # 動態分析權值股
        w_status = []
        for w, w_n in {"2330":"台積電", "2454":"聯發科", "2317":"鴻海"}.items():
            h_w = yf.Ticker(f"{w}.TW").history(period="2d")
            w_d = h_w.iloc[-1]['Close'] - h_w.iloc[0]['Close']
            w_m = "🔴漲" if w_d > 0 else "🟢跌" if w_d < 0 else "⚪平"
            w_status.append(f"{w_n}{w_m}")
        
        avg_vol = t_hist['Volume'].tail(5).mean()
        v_ratio = now['Volume'] / avg_vol
        v_desc = "放量" if v_ratio > 1.2 else "縮量" if v_ratio < 0.8 else "量能持平"

        st.info(f"🔍 **實質觀察：** 權值股({', '.join(w_status)})。量能比 {v_ratio:.2f}x ({v_desc})。")
except:
    st.write("數據讀取中...")

st.divider()

# --- 3. 自選股管理 (同步雲端) ---
st.header("🗂️ 自選股群組管理")
with st.expander("⚙️ 管理雲端清單", expanded=False):
    col1, col2 = st.columns(2)
    # A. 新增分類/個股
    with col1:
        st.write("**新增個股**")
        in_g = st.text_input("分類名稱")
        in_c = st.text_input("股票代碼")
        in_n = st.text_input("股票名稱")
        if st.button("確認存入雲端"):
            if in_g and in_c:
                new_data = pd.DataFrame([{"group": in_g, "code": in_c, "name": in_n}])
                updated_stocks = pd.concat([stocks_df, new_data], ignore_index=True)
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated_stocks)
                st.success("已同步至 Google Sheets！")
                st.rerun()

    # B. 刪除分類
    with col2:
        st.write("**刪除管理**")
        all_gs = ["請選擇"] + list(stocks_df['group'].unique())
        target_g = st.selectbox("選擇要刪除的分類", all_gs)
        if st.button("⚠️ 刪除整個分類"):
            if target_g != "請選擇":
                updated_stocks = stocks_df[stocks_df['group'] != target_g]
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated_stocks)
                st.rerun()

# 顯示分組 (從雲端讀取)
for g in stocks_df['group'].unique():
    st.subheader(f"📁 {g}")
    g_list = stocks_df[stocks_df['group'] == g]
    for _, row in g_list.iterrows():
        try:
            t_c, t_n = str(row['code']), row['name']
            tk = yf.Ticker(f"{t_c}.TW")
            h = tk.history(period="2d")
            if not h.empty:
                cp, pp = h.iloc[-1]['Close'], h.iloc[0]['Close']
                d, p = cp - pp, ((cp - pp)/pp)*100
                m = "🔴" if d > 0 else "🟢" if d < 0 else "⚪"
                sc1, sc2, sc3, sc4 = st.columns([2, 1.5, 2, 1])
                sc1.write(f"**{t_c} {t_n}**")
                sc2.write(f"價: {cp:.2f}")
                sc3.write(f"{m} {d:+.2f} ({p:+.2f}%)")
                if sc4.button("❌", key=f"del_{g}_{t_c}"):
                    updated_stocks = stocks_df[~((stocks_df['group']==g) & (stocks_df['code']==row['code']))]
                    conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated_stocks)
                    st.rerun()
        except:
            st.caption(f"{row['code']} 讀取中...")

st.divider()

# --- 4. 討論筆記 (同步雲端) ---
st.header("📝 討論筆記紀錄")
with st.form("cloud_note_form", clear_on_submit=True):
    n_t = st.text_input("議題主題")
    n_k = st.text_input("標籤 (多個請用逗號隔開)")
    n_c = st.text_area("討論筆記內容")
    if st.form_submit_button("永久儲存筆記"):
        if n_t:
            new_note = pd.DataFrame([{
                "title": n_t, "tags": n_k, "content": n_c, 
                "date": datetime.now().strftime("%Y-%m-%d")
            }])
            updated_notes = pd.concat([notes_df, new_note], ignore_index=True)
            conn.update(spreadsheet=SP_URL, worksheet="notes", data=updated_notes)
            st.success("筆記已安全存入雲端！")
            st.rerun()

if not notes_df.empty:
    for _, n in notes_df.iloc[::-1].iterrows(): # 倒序顯示，最新的在上面
        with st.expander(f"📌 {n['title']} ({n['date']})"):
            st.caption(f"標籤: {n['tags']}")
            st.write(n['content'])
