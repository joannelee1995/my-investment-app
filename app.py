import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="台股投資戰情室 3.0", layout="wide")

# 漲紅跌綠配色
st.markdown("""
    <style>
    .stMetric [data-testid="stMetricDelta"] > div:nth-child(2) { color: #FF0000 !important; }
    [data-testid="stMetricDelta"] svg { fill: #FF0000 !important; }
    </style>
    """, unsafe_allow_html=True)

if 'stock_groups' not in st.session_state:
    st.session_state.stock_groups = {"電子": ["2330", "2454"], "金融": ["2881", "2882"], "ETF": ["0050", "00878"]}
if 'notes' not in st.session_state: st.session_state.notes = []

# --- 1. 置頂：大盤狀況 ---
st.title("🇹🇼 台股投資戰情室 3.0")
try:
    twii = yf.Ticker("^TWII")
    t_hist = twii.history(period="2d")
    
    if not t_hist.empty:
        now = t_hist.iloc[-1]
        prev = t_hist.iloc[-2]
        change = now['Close'] - prev['Close']
        pct = (change / prev['Close']) * 100
        
        c1, c2, c3 = st.columns(3)
        c1.metric("加權指數", f"{now['Close']:,.2f}", f"{change:+.2f} ({pct:+.2f}%)")
        c2.metric("最後更新", datetime.now().strftime('%H:%M:%S'), f"量能狀態: {'活躍' if now['Volume']>0 else '待更新'}")
        with c3:
            st.write(f"**市場情緒：** {'🔴 指數上揚' if change > 0 else '🟢 指數拉回'}")
            st.caption("數據由 Yahoo Finance 提供")
except:
    st.write("大盤數據讀取中...")

st.divider()

# --- 2. 財經焦點 ---
st.header("📰 今日財經焦點")
st.info("💡 點擊下方連結查看最新台股新聞：")
n_c1, n_c2, n_c3 = st.columns(3)
n_c1.write("[Yahoo 股市新聞](https://tw.stock.yahoo.com/news/)")
n_c2.write("[工商時報 - 股市](https://www.ctee.com.tw/livenews/aj)")
n_c3.write("[經濟日報 - 證券](https://money.udn.com/money/cate/5589)")

st.divider()

# --- 3. 自選股群組管理 (優化讀取速度) ---
st.header("🗂️ 自選股群組管理")

with st.expander("⚙️ 管理群組與新增個股"):
    g1, g2 = st.columns(2)
    new_g = g1.text_input("建立新分類")
    if g1.button("新增"):
        if new_g: st.session_state.stock_groups[new_g] = []
    
    target_g = g2.selectbox("選擇分類", list(st.session_state.stock_groups.keys()))
    s_code = g2.text_input("輸入代碼 (數字)")
    if g2.button("加入"):
        if s_code: 
            st.session_state.stock_groups[target_g].append(s_code)
            st.rerun()

for group, stocks in st.session_state.stock_groups.items():
    if stocks:
        st.subheader(f"📁 {group}")
        for code in stocks:
            try:
                # 抓取 2 天歷史紀錄
                t = yf.Ticker(f"{code}.TW")
                h = t.history(period="2d")
                
                if not h.empty:
                    cur = h['Close'].iloc[-1]
                    prev = h['Close'].iloc[0]
                    diff = cur - prev
                    mark = "🔴" if diff > 0 else "🟢" if diff < 0 else "⚪"
                    
                    sc1, sc2, sc3, sc4 = st.columns([2, 1.5, 2, 1])
                    # 嘗試快速獲取名稱，若卡住則只顯示代碼
                    name = f"{code} 台股"
                    sc1.write(f"**{name}**")
                    sc2.write(f"價: {cur:.2f}")
                    sc3.write(f"{mark} {diff:+.2f} ({((diff/prev)*100):+.2f}%)")
                    if sc4.button("❌", key=f"del_{group}_{code}"):
                        st.session_state.stock_groups[group].remove(code)
                        st.rerun()
                else:
                    st.write(f"⚠️ {code} 暫無數據")
            except:
                st.write(f"❌ {code} 讀取錯誤")

st.divider()

# --- 4. 討論筆記紀錄 ---
st.header("📝 討論筆記紀錄")
with st.form("note_v4"):
    nt = st.text_input("主題")
    nk = st.text_input("關鍵標籤")
    nc = st.text_area("筆記內容")
    if st.form_submit_button("儲存這週討論"):
        st.session_state.notes.append({"T": nt, "K": [k.strip() for k in nk.split(",")], "C": nc})

if st.session_state.notes:
    for n in reversed(st.session_state.notes):
        with st.expander(f"📌 {n['T']} ({', '.join(n['K'])})"):
            st.write(n['C'])
