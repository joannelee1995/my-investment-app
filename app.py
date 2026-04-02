import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf

# 設定網頁標題與手機適配
st.set_page_config(page_title="Lee投資戰情室", layout="wide")

st.title("👨‍👦 Lee投資戰情室")

# --- 側邊欄：資產輸入 ---
st.sidebar.header("💰 我的資產配置")
cash = st.sidebar.number_input("剩餘定存/現金 (萬)", value=100)
stock_val = st.sidebar.number_input("目前股市市值 (萬)", value=0)

# --- 第一塊：資產視覺化 ---
st.subheader("📊 資產分佈圖")
df_asset = pd.DataFrame({
    "類別": ["現金/定存", "股市投資"],
    "金額": [cash, stock_val]
})
fig = px.pie(df_asset, values='金額', names='類別', hole=0.4)
st.plotly_chart(fig, use_container_width=True)

# --- 第二塊：股市快查 ---
st.subheader("📈 即時個股追蹤")
symbol = st.text_input("輸入股票代碼 (例如: 2330.TW)", "2330.TW")
if symbol:
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.fast_info['last_price']
        st.metric(label=f"{symbol} 最新價", value=f"{price:.2f}")
    except:
        st.warning("查無此代碼，請確認格式（台股需加 .TW）")

# --- 第三塊：討論紀錄 (心智圖概念) ---
st.subheader("📝 每週討論筆記")
if 'notes' not in st.session_state:
    st.session_state.notes = []

with st.form("note_form", clear_on_submit=True):
    topic = st.text_input("本週議題 (如: 殖利率是什麼?)")
    content = st.text_area("討論重點")
    if st.form_submit_button("儲存筆記"):
        if topic:
            st.session_state.notes.append({"主題": topic, "內容": content})
            st.success("筆記已儲存！")

for note in reversed(st.session_state.notes):
    with st.expander(f"📌 {note['主題']}"):
        st.write(note['內容'])
