import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="台股永久戰情室 4.0", layout="wide")

# 隱藏預設箭頭
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_True=True)

# 連接 Google Sheets (會自動抓 Secrets 的金鑰)
SP_URL = "https://docs.google.com/spreadsheets/d/1pSVEg5J_-tg0wetPxNUVb9cU6kapUL_NIEV_Xz84PDM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# 讀取雲端資料
def load_data():
    try:
        s_df = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl="1s")
        n_df = conn.read(spreadsheet=SP_URL, worksheet="notes", ttl="1s")
        return s_df.dropna(how='all'), n_df.dropna(how='all')
    except:
        return pd.DataFrame(columns=["group", "code", "name"]), pd.DataFrame(columns=["title", "tags", "content", "date"])

stocks_df, notes_df = load_data()

# --- 1. 大盤區 ---
st.title("🇹🇼 台股永久戰情室 4.0")
try:
    twii = yf.Ticker("^TWII")
    t_hist = twii.history(period="5d")
    if not t_hist.empty:
        now, prev = t_hist.iloc[-1], t_hist.iloc[-2]
        diff, pct = now['Close'] - prev['Close'], ((now['Close'] - prev['Close'])/prev['Close'])*100
        icon = "🔴" if diff > 0 else "🟢"
        st.metric("加權指數", f"{now['Close']:,.2f}", f"{icon} {diff:+.2f} ({pct:+.2f}%)")
except:
    st.write("大盤載入中...")

st.divider()

# --- 2. 管理區 ---
st.header("🗂️ 自選股管理 (已連動 Secrets 永久保存)")
with st.expander("⚙️ 點此新增分類或個股"):
    # 新增分類
    new_g = st.text_input("1. 建立新分類")
    if st.button("確認建立"):
        new_row = pd.DataFrame([{"group": new_g, "code": "9999", "name": "PLACEHOLDER"}])
        updated = pd.concat([stocks_df, new_row], ignore_index=True)
        conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
        st.rerun()
    
    st.write("---")
    # 新增個股
    target_g = st.selectbox("2. 選擇分類", list(stocks_df['group'].unique()))
    c1, c2 = st.columns(2)
    sc, sn = c1.text_input("股票代碼"), c2.text_input("股票名稱")
    if st.button("🚀 確認永久存入"):
        clean_df = stocks_df[~((stocks_df['group'] == target_g) & (stocks_df['code'] == "9999"))]
        new_s = pd.DataFrame([{"group": target_g, "code": sc, "name": sn}])
        updated = pd.concat([clean_df, new_s], ignore_index=True)
        conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
        st.rerun()

# 顯示與刪除邏輯
for g in stocks_df['group'].unique():
    st.subheader(f"📁 {g}")
    sub_df = stocks_df[stocks_df['group'] == g]
    for _, row in sub_df.iterrows():
        if str(row['code']) == "9999": continue
        sc1, sc2, sc3 = st.columns([3, 2, 1])
        sc1.write(f"**{row['code']} {row['name']}**")
        if sc3.button("❌", key=f"del_{g}_{row['code']}"):
            updated = stocks_df[~((stocks_df['group'] == g) & (stocks_df['code'] == row['code']))]
            conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
            st.rerun()

st.divider()

# --- 3. 筆記區 ---
st.header("📝 雲端筆記")
with st.form("note_cloud"):
    n1, n2, n3 = st.text_input("主題"), st.text_input("標籤"), st.text_area("內容")
    if st.form_submit_button("永久儲存筆記"):
        new_n = pd.DataFrame([{"title": n1, "tags": n2, "content": n3, "date": datetime.now().strftime("%Y-%m-%d")}])
        updated = pd.concat([notes_df, new_n], ignore_index=True)
        conn.update(spreadsheet=SP_URL, worksheet="notes", data=updated)
        st.rerun()

if not notes_df.empty:
    for _, n in notes_df.iloc[::-1].iterrows():
        with st.expander(f"📌 {n['title']}"):
            st.write(n['content'])
