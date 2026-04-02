import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="台股投資戰情室 3.0", layout="wide")

# 強制紅綠配色
st.markdown("""
    <style>
    .stMetric [data-testid="stMetricDelta"] > div:nth-child(2) { color: #FF0000 !important; }
    [data-testid="stMetricDelta"] svg { fill: #FF0000 !important; }
    </style>
    """, unsafe_allow_html=True)

if 'stock_groups' not in st.session_state:
    st.session_state.stock_groups = {"電子": ["2330"], "金融": ["2881"], "ETF": ["0050"]}
if 'notes' not in st.session_state: st.session_state.notes = []

# --- 1. 置頂：大盤狀況 (優化成交量與名稱) ---
st.title("🇹🇼 台股投資戰情室 3.0")
try:
    # 嘗試抓取 0050 作為市場熱度參考 (因為大盤指數成交量常為 0)
    market_ref = yf.Ticker("0050.TW")
    m_hist = market_ref.history(period="5d")
    
    twii = yf.Ticker("^TWII")
    t_hist = twii.history(period="5d")
    
    if not t_hist.empty:
        now = t_hist.iloc[-1]
        prev = t_hist.iloc[-2]
        change = now['Close'] - prev['Close']
        pct = (change / prev['Close']) * 100
        
        # 使用 0050 的量能比作為市場熱度參考
        vol_now = m_hist.iloc[-1]['Volume']
        vol_avg = m_hist['Volume'].mean()
        vol_ratio = vol_now / vol_avg
        
        c1, c2, c3 = st.columns(3)
        c1.metric("加權指數", f"{now['Close']:,.2f}", f"{change:+.2f} ({pct:+.2f}%)")
        c2.metric("市場熱度 (以0050為準)", f"{vol_now/10**6:,.1f} 百萬股", f"量能比: {vol_ratio:.2f}x")
        with c3:
            st.write(f"**量能狀態：** {'🔥 放量' if vol_ratio > 1.1 else '❄️ 縮量'}")
            st.write(f"**最後更新：** {datetime.now().strftime('%H:%M:%S')}")
except:
    st.error("大盤數據讀取中...")

st.divider()

# --- 2. 財經焦點 (換個方式呈現新聞) ---
st.header("📰 今日財經焦點")
try:
    # 直接抓取 Yahoo Finance 全球財經新聞中有關 Taiwan 的部分
    tw_news = yf.Search('Taiwan Market', news_count=3).news
    if tw_news:
        n_cols = st.columns(3)
        for i, item in enumerate(tw_news):
            with n_cols[i]:
                st.info(f"**{item['title']}**")
                st.write(f"[閱讀全文]({item['link']})")
    else:
        st.write("目前無即時新聞。")
except:
    st.write("新聞功能維護中。")

st.divider()

# --- 3. 自選股群組管理 (加入中文名稱) ---
st.header("🗂️ 自選股群組管理")

with st.expander("⚙️ 管理群組與新增個股"):
    g1, g2 = st.columns(2)
    new_g = g1.text_input("建立新分類")
    if g1.button("新增"):
        if new_g: st.session_state.stock_groups[new_g] = []
    
    target_g = g2.selectbox("選擇分類", list(st.session_state.stock_groups.keys()))
    s_code = g2.text_input("輸入代碼")
    if g2.button("加入"):
        if s_code: st.session_state.stock_groups[target_g].append(s_code)

for group, stocks in st.session_state.stock_groups.items():
    if stocks:
        st.subheader(f"📁 {group}")
        for code in stocks:
            try:
                t = yf.Ticker(f"{code}.TW")
                # 獲取中文名稱 (Yahoo Finance 台灣個股通常有中文名)
                c_name = t.info.get('shortName', '未知名稱')
                
                h = t.history(period="2d")
                cur = h['Close'].iloc[-1]
                prev = h['Close'].iloc[0]
                diff = cur - prev
                mark = "🔴" if diff > 0 else "🟢" if diff < 0 else "⚪"
                
                sc1, sc2, sc3, sc4 = st.columns([2, 2, 2, 1])
                sc1.write(f"**{code} {c_name}**")
                sc2.write(f"價: {cur:.2f}")
                sc3.write(f"{mark} {diff:+.2f} ({((diff/prev)*100):+.2f}%)")
                if sc4.button("❌", key=f"del_{group}_{code}"):
                    st.session_state.stock_groups[group].remove(code)
                    st.rerun()
            except:
                st.caption(f"{code} 數據讀取中...")

st.divider()

# --- 4. 筆記 (保留) ---
st.header("📝 討論筆記紀錄")
with st.form("note_final"):
    nt = st.text_input("主題")
    nk = st.text_input("標籤")
    nc = st.text_area("筆記內容")
    if st.form_submit_button("儲存"):
        st.session_state.notes.append({"T": nt, "K": [k.strip() for k in nk.split(",")], "C": nc})

if st.session_state.notes:
    for n in reversed(st.session_state.notes):
        with st.expander(f"📌 {n['T']}"):
            st.write(n['C'])
