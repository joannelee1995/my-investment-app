import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf

st.set_page_config(page_title="台股投資戰情室", layout="wide")

# 自定義 CSS 讓表格顏色更明顯
st.markdown("""
    <style>
    .red-text { color: #eb4034; font-weight: bold; }
    .green-text { color: #1f822d; font-weight: bold; }
    </style>
    """, unsafe_content_code=True)

if 'notes' not in st.session_state: st.session_state.notes = []
if 'watchlist' not in st.session_state: st.session_state.watchlist = ["2330", "0050"]
if 'portfolio' not in st.session_state: st.session_state.portfolio = []

# --- 置頂：大盤狀況 ---
st.title("🇹🇼 台股投資戰情室")
try:
    twii = yf.Ticker("^TWII") # 加權指數代碼
    hist = twii.history(period="2d")
    now_price = hist['Close'].iloc[-1]
    last_price = hist['Close'].iloc[0]
    change = now_price - last_price
    pct = (change / last_price) * 100
    
    col1, col2, col3 = st.columns(3)
    col1.metric("台股加權指數", f"{now_price:,.2f}", f"{change:+.2f} ({pct:+.2f}%)")
except:
    st.write("目前無法取得大盤即時數據")

st.divider()

# --- 第一部分：即時個股追蹤 (顏色優化) ---
st.header("📈 自選股監控")
new_stock = st.text_input("輸入台股代碼 (直接輸入數字，如: 0056)")
if st.button("加入自選"):
    if new_stock and new_stock not in st.session_state.watchlist:
        st.session_state.watchlist.append(new_stock)

if st.session_state.watchlist:
    # 建立表格呈現
    rows = []
    for code in st.session_state.watchlist:
        try:
            full_code = f"{code}.TW"
            t = yf.Ticker(full_code)
            h = t.history(period="2d")
            cur = h['Close'].iloc[-1]
            prev = h['Close'].iloc[0]
            diff = cur - prev
            diff_p = (diff / prev) * 100
            
            # 根據漲跌決定顏色符號
            color = "🔴" if diff > 0 else "🟢" if diff < 0 else "⚪"
            rows.append({
                "代碼": code,
                "現價": f"{cur:.2f}",
                "漲跌": f"{diff:+.2f}",
                "漲跌幅": f"{diff_p:+.2f}%",
                "趨勢": color
            })
        except: continue
    
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

st.divider()

# --- 第二部分：討論紀錄與標籤 ---
st.header("📝 討論筆記")
with st.form("note_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    topic = c1.text_input("主題")
    tags = c2.text_input("關鍵字 (逗號隔開)")
    content = st.text_area("筆記內容")
    if st.form_submit_button("儲存"):
        st.session_state.notes.append({"T": topic, "K": [k.strip() for k in tags.split(",")], "C": content})

if st.session_state.notes:
    all_k = list(set([k for n in st.session_state.notes for k in n["K"]]))
    sel = st.multiselect("篩選關鍵字", all_k)
    for n in reversed(st.session_state.notes):
        if not sel or any(k in sel for k in n["K"]):
            with st.expander(f"📌 {n['T']} ({', '.join(n['K'])})"):
                st.write(n['C'])

st.divider()

# --- 第三部分：資產配置 ---
st.header("💰 我的資產分佈")
with st.expander("新增持有紀錄"):
    with st.form("p_form"):
        p1, p2, p3 = st.columns(3)
        name = p1.text_input("名稱 (如: 0050)")
        cost = p2.number_input("總投入成本 (萬)", min_value=0.0)
        cat = p3.selectbox("
