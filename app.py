import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="台股投資戰情室 3.0", layout="wide")

# --- 1. 置頂：大盤狀況 (加入量能呈現) ---
st.title("🇹🇼 台股投資戰情室 3.0")
try:
    twii = yf.Ticker("^TWII")
    # 抓取近 5 日數據以比較量能
    hist = twii.history(period="5d")
    now = hist.iloc[-1]
    prev = hist.iloc[-2]
    
    avg_vol = hist['Volume'].mean() # 5日均量
    vol_ratio = (now['Volume'] / avg_vol) # 今日量能比
    
    c1, c2, c3, c4 = st.columns(4)
    change = now['Close'] - prev['Close']
    pct = (change / prev['Close']) * 100
    
    c1.metric("加權指數", f"{now['Close']:,.2f}", f"{change:+.2f} ({pct:+.2f}%)")
    c2.metric("今日成交量", f"{now['Volume']/10**8:.2f} 億", f"{(now['Volume']-prev['Volume'])/10**8:+.2f} 億")
    
    # 量能視覺化標示
    vol_status = "量增" if now['Volume'] > prev['Volume'] else "量縮"
    c3.write(f"**量能狀態：** {vol_status}")
    c3.progress(min(vol_ratio/2, 1.0), text=f"量能比: {vol_ratio:.2f}x")
    
    c4.write(f"**最後更新：** {datetime.now().strftime('%H:%M:%S')}")
except:
    st.error("大盤數據讀取失敗")

st.divider()

# --- 2. 每日財經精選 (模擬新聞摘要功能) ---
st.header("📰 今日財經焦點")
news_col1, news_col2, news_col3 = st.columns(3)
try:
    # 這裡利用 yfinance 抓取大盤相關新聞標題
    news = twii.news[:3]
    cols = [news_col1, news_col2, news_col3]
    for i, item in enumerate(news):
        with cols[i]:
            st.info(f"**{item['title']}**")
            st.caption(f"來源: {item['publisher']}")
            st.write(f"[閱讀全文]({item['link']})")
except:
    st.write("暫時無法取得新聞資訊")

st.divider()

# --- 3. 自選股分門別類 ---
st.header("🗂️ 自選股群組管理")

# 初始化分類與個股資料
if 'stock_groups' not in st.session_state:
    st.session_state.stock_groups = {
        "電子/半導體": ["2330", "2454"],
        "金融": ["2881", "2882"],
        "ETF": ["0050", "00878"],
        "食品/傳產": []
    }

# 新增/管理分類
with st.expander("⚙️ 管理分類與新增個股"):
    g_col1, g_col2, g_col3 = st.columns(3)
    new_g = g_col1.text_input("建立新分類 (如: 航運)")
    if g_col1.button("新增分類"):
        if new_g and new_g not in st.session_state.stock_groups:
            st.session_state.stock_groups[new_g] = []
    
    target_g = g_col2.selectbox("選擇分類", list(st.session_state.stock_groups.keys()))
    s_code = g_col3.text_input("輸入代碼 (如: 2603)")
    if g_col3.button("將個股加入此分類"):
        if s_code and s_code not in st.session_state.stock_groups[target_g]:
            st.session_state.stock_groups[target_g].append(s_code)

# 呈現分類清單
for group, stocks in st.session_state.stock_groups.items():
    if stocks:
        st.subheader(f"📁 {group}")
        rows = []
        for code in stocks:
            try:
                t = yf.Ticker(f"{code}.TW")
                h = t.history(period="2d")
                cur = h['Close'].iloc[-1]
                prev = h['Close'].iloc[0]
                diff = cur - prev
                diff_p = (diff / prev) * 100
                rows.append({
                    "代碼": code,
                    "現價": f"{cur:.2f}",
                    "漲跌": f"{diff:+.2f}",
                    "幅 %": f"{diff_p:+.2f}%",
                    "趨勢": "🔴" if diff > 0 else "🟢"
                })
            except: continue
        st.table(pd.DataFrame(rows))

st.divider()
# (保留原有的筆記與資產配置功能...)
