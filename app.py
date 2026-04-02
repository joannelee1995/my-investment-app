import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="台股投資戰情室 3.0", layout="wide")

# 修正：台股配色 CSS (漲紅跌綠)
st.markdown("""
    <style>
    .stMetric [data-testid="stMetricDelta"] > div:nth-child(2) { color: #FF0000 !important; } /* 漲紅 */
    [data-testid="stMetricDelta"] svg { fill: #FF0000 !important; }
    </style>
    """, unsafe_allow_html=True)

# 初始化資料
if 'stock_groups' not in st.session_state:
    st.session_state.stock_groups = {"電子": ["2330"], "金融": ["2881"], "ETF": ["0050"]}
if 'notes' not in st.session_state: st.session_state.notes = []

# --- 1. 置頂：大盤狀況 ---
st.title("🇹🇼 台股投資戰情室 3.0")
try:
    twii = yf.Ticker("^TWII")
    hist = twii.history(period="5d")
    if not hist.empty:
        now = hist.iloc[-1]
        prev = hist.iloc[-2]
        change = now['Close'] - prev['Close']
        pct = (change / prev['Close']) * 100
        
        # 成交量處理 (台股張數換算，yfinance 單位較跳躍，這裡做格式化呈現)
        vol_raw = now['Volume']
        avg_vol = hist['Volume'].mean()
        vol_ratio = vol_raw / avg_vol if avg_vol > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        # 設定顏色屬性
        d_color = "normal" if change >= 0 else "inverse" # Streamlit 預設 normal 為綠，這裡需配合 CSS
        
        c1.metric("加權指數", f"{now['Close']:,.2f}", f"{change:+.2f} ({pct:+.2f}%)", delta_color=d_color)
        c2.metric("成交量指標", f"{vol_raw/10**6:,.0f} 單位", f"量能比: {vol_ratio:.2f}x")
        
        with c3:
            st.write(f"**量能狀態：** {'量增' if vol_ratio > 1 else '量縮'}")
            st.write(f"**更新時間：** {datetime.now().strftime('%H:%M:%S')}")
except Exception as e:
    st.error(f"大盤數據加載中，請稍候重整...")

st.divider()

# --- 2. 財經焦點 (新聞) ---
st.header("📰 今日財經焦點")
try:
    news = twii.news
    if news:
        n_cols = st.columns(3)
        for i, item in enumerate(news[:3]):
            with n_cols[i]:
                st.info(f"**{item['title']}**")
                st.caption(f"來源: {item.get('publisher', '財經新聞')}")
                st.write(f"[點此閱讀原文]({item['link']})")
    else:
        st.write("目前暫無最新新聞。")
except:
    st.write("無法連結至新聞伺服器。")

st.divider()

# --- 3. 自選股群組管理 (包含刪除與配色修正) ---
st.header("🗂️ 自選股群組管理")

with st.expander("⚙️ 管理群組與新增個股"):
    g1, g2 = st.columns(2)
    new_g = g1.text_input("建立新分類 (例如: 食品)")
    if g1.button("新增分類"):
        if new_g and new_g not in st.session_state.stock_groups:
            st.session_state.stock_groups[new_g] = []
            st.rerun()
    
    target_g = g2.selectbox("選擇要加入的分類", list(st.session_state.stock_groups.keys()))
    s_code = g2.text_input("輸入台股代碼 (數字即可)")
    if g2.button("確認加入個股"):
        if s_code and s_code not in st.session_state.stock_groups[target_g]:
            st.session_state.stock_groups[target_g].append(s_code)
            st.rerun()

# 顯示分組
for group, stocks in st.session_state.stock_groups.items():
    if stocks or group:
        st.subheader(f"📁 {group}")
        if not stocks:
            st.caption("此分類目前沒有股票")
            continue
            
        for code in stocks:
            try:
                t = yf.Ticker(f"{code}.TW")
                h = t.history(period="2d")
                cur = h['Close'].iloc[-1]
                prev = h['Close'].iloc[0]
                diff = cur - prev
                # 台灣習慣：漲紅點 🔴，跌綠點 🟢
                p_mark = "🔴" if diff > 0 else "🟢" if diff < 0 else "⚪"
                
                sc1, sc2, sc3, sc4 = st.columns([1, 2, 2, 1])
                sc1.write(f"**{code}**")
                sc2.write(f"價格: {cur:.2f}")
                sc3.write(f"{p_mark} {diff:+.2f} ({((diff/prev)*100):+.2f}%)")
                if sc4.button("❌", key=f"del_{group}_{code}"):
                    st.session_state.stock_groups[group].remove(code)
                    st.rerun()
            except:
                st.caption(f"代碼 {code} 數據暫時無法讀取")

st.divider()

# --- 4. 討論紀錄與議題地圖 ---
st.header("📝 討論筆記紀錄")
with st.form("note_v3"):
    n_c1, n_c2 = st.columns(2)
    nt = n_c1.text_input("討論主題")
    nk = n_c2.text_input("關鍵標籤 (以逗號隔開)")
    nc = st.text_area("詳細討論筆記內容")
    if st.form_submit_button("儲存紀錄"):
        if nt:
            st.session_state.notes.append({"T": nt, "K": [k.strip() for k in nk.split(",")], "C": nc})
            st.success("紀錄已儲存")

if st.session_state.notes:
    all_tags = list(set([k for n in st.session_state.notes for k in n["K"] if k]))
    sel = st.multiselect("💡 點選標籤進行議題關聯分析 (心智圖概念)", all_tags)
    for n in reversed(st.session_state.notes):
        if not sel or any(tag in sel for tag in n["K"]):
            with st.expander(f"📌 {n['T']} (標籤: {', '.join(n['K'])})"):
                st.write(n['C'])
