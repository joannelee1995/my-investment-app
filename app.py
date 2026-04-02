import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="台股投資戰情室 3.0", layout="wide")

# 強制台股配色 CSS
st.markdown("""
    <style>
    [data-testid="stMetricDelta"] svg { display: none; } /* 隱藏預設箭頭 */
    .red-up { color: #FF0000 !important; }
    .green-down { color: #008000 !important; }
    </style>
    """, unsafe_content_code=True)

# 初始化資料
if 'stock_groups' not in st.session_state:
    st.session_state.stock_groups = {"電子": ["2330"], "金融": ["2881"], "ETF": ["0050"]}
if 'notes' not in st.session_state: st.session_state.notes = []

# --- 1. 置頂：大盤狀況 ---
st.title("🇹🇼 台股投資戰情室 3.0")
try:
    twii = yf.Ticker("^TWII")
    hist = twii.history(period="5d")
    now = hist.iloc[-1]
    prev = hist.iloc[-2]
    
    change = now['Close'] - prev['Close']
    pct = (change / prev['Close']) * 100
    
    # 台灣成交量通常以「億元」計，yfinance 抓的是「股數/張數單位」，這裡做近似轉換
    vol_amt = now['Volume'] / 10**6 # 粗略轉換
    avg_vol = hist['Volume'].mean()
    vol_ratio = now['Volume'] / avg_vol
    
    c1, c2, c3 = st.columns(3)
    # 台灣配色：漲紅跌綠
    d_color = "normal" if change >= 0 else "inverse" 
    c1.metric("加權指數", f"{now['Close']:,.2f}", f"{change:+.2f} ({pct:+.2f}%)", delta_color=d_color)
    c2.metric("預估成交量指標", f"{vol_amt:,.0f} 單位", f"量能比: {vol_ratio:.2f}x")
    
    with c3:
        st.write(f"**市場狀態：** {'🔴 多方佔優' if change > 0 else '🟢 空方回檔'}")
        st.caption("量能比 > 1 代表今日交易比過去5日平均更熱絡")
except:
    st.error("大盤數據讀取中...")

st.divider()

# --- 2. 財經焦點 ---
st.header("📰 今日財經焦點")
try:
    news = twii.news[:3]
    if news:
        cols = st.columns(3)
        for i, item in enumerate(news):
            with cols[i]:
                st.info(f"**{item['title']}**")
                st.write(f"[點此閱讀原文]({item['link']})")
    else:
        st.write("目前無即時新聞，請稍後再試。")
except:
    st.write("新聞加載失敗")

st.divider()

# --- 3. 自選股群組管理 (含刪除功能) ---
st.header("🗂️ 自選股群組管理")

with st.expander("⚙️ 管理群組與新增個股"):
    g_col1, g_col2 = st.columns(2)
    new_g = g_col1.text_input("建立新分類")
    if g_col1.button("新增分類"):
        if new_g and new_g not in st.session_state.stock_groups:
            st.session_state.stock_groups[new_g] = []
    
    target_g = g_col2.selectbox("選擇分類", list(st.session_state.stock_groups.keys()))
    s_code = g_col2.text_input("輸入代碼 (如: 2454)")
    if g_col2.button("加入個股"):
        if s_code and s_code not in st.session_state.stock_groups[target_g]:
            st.session_state.stock_groups[target_g].append(s_code)

# 顯示分組與刪除鍵
for group, stocks in st.session_state.stock_groups.items():
    st.subheader(f"📁 {group}")
    if not stocks:
        st.write("目前尚無個股")
        continue
    
    for code in stocks:
        try:
            t = yf.Ticker(f"{code}.TW")
            h = t.history(period="2d")
            cur = h['Close'].iloc[-1]
            prev = h['Close'].iloc[0]
            diff = cur - prev
            p_str = "🔴" if diff > 0 else "🟢" if diff < 0 else "⚪"
            
            sc1, sc2, sc3, sc4, sc5 = st.columns([1,1,1,1,1])
            sc1.write(f"**{code}**")
            sc2.write(f"價: {cur:.2f}")
            sc3.write(f"{p_str} {diff:+.2f}")
            if sc5.button("❌", key=f"del_{group}_{code}"):
                st.session_state.stock_groups[group].remove(code)
                st.rerun()
        except:
            st.write(f"代碼 {code} 讀取失敗")

st.divider()

# --- 4. 討論紀錄 (心智圖概念) ---
st.header("📝 我與爸爸的討論紀錄")
with st.form("note_form", clear_on_submit=True):
    n_c1, n_c2 = st.columns(2)
    nt = n_c1.text_input("議題主題")
    nk = n_c2.text_input("關鍵標籤 (逗號隔開)")
    nc = st.text_area("對話重點筆記")
    if st.form_submit_button("儲存這週討論"):
        st.session_state.notes.append({"T": nt, "K": [k.strip() for k in nk.split(",")], "C": nc})

if st.session_state.notes:
    all_tags = list(set([k for n in st.session_state.notes for k in n["K"] if k]))
    sel_tags = st.multiselect("💡 點選標籤查看關聯議題", all_tags)
    
    for n in reversed(st.session_state.notes):
        if not sel_tags or any(tag in sel_tags for tag in n["K"]):
            with st.expander(f"📌 {n['T']} | 標籤: {', '.join(n['K'])}"):
                st.write(n['C'])
