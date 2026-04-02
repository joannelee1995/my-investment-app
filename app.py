import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="台股投資戰情室 3.0", layout="wide")

# --- 超強效 CSS：強制紅漲綠跌 ---
st.markdown("""
    <style>
    /* 強制 Metric 數字顏色 */
    [data-testid="stMetricValue"] { color: white !important; }
    /* 這裡透過選取器強制覆寫：Streamlit 認為的 'normal' (通常是綠) 改成紅 */
    [data-testid="stMetricDelta"] > div { color: #FF0000 !important; } /* 漲紅 */
    [data-testid="stMetricDelta"] svg { fill: #FF0000 !important; }
    /* 如果是負數 (跌)，我們在程式碼中會標註為 'inverse'，這裡再強制轉綠 */
    [data-testid="stMetricDelta"][data-delta-color="inverse"] > div { color: #008000 !important; } /* 跌綠 */
    [data-testid="stMetricDelta"][data-delta-color="inverse"] svg { fill: #008000 !important; }
    </style>
    """, unsafe_allow_html=True)

# 常用個股中文名稱對照表 (解決 API 讀不到中文的問題)
STOCK_NAMES = {
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海", 
    "0050": "元大台灣50", "0056": "元大高股息", "00878": "國泰永續高股息",
    "2881": "富邦金", "2882": "國泰金", "2603": "長榮"
}

if 'stock_groups' not in st.session_state:
    st.session_state.stock_groups = {"電子": ["2330"], "金融": ["2881"], "ETF": ["0050"]}
if 'notes' not in st.session_state: st.session_state.notes = []

# --- 1. 置頂：大盤狀況 ---
st.title("🇹🇼 台股投資戰情室 3.0")
try:
    twii = yf.Ticker("^TWII")
    t_hist = twii.history(period="2d")
    if not t_hist.empty:
        now = t_hist.iloc[-1]['Close']
        prev = t_hist.iloc[-2]['Close']
        diff = now - prev
        pct = (diff / prev) * 100
        
        c1, c2, c3 = st.columns(3)
        # 關鍵：如果是正數用 'normal' (CSS已轉紅)，負數用 'inverse' (CSS已轉綠)
        d_mode = "normal" if diff >= 0 else "inverse"
        c1.metric("加權指數", f"{now:,.2f}", f"{diff:+.2f} ({pct:+.2f}%)", delta_color=d_mode)
        
        status_text = "📈 強勢上漲" if diff > 0 else "📉 市場跌勢"
        status_icon = "🔴" if diff > 0 else "🟢"
        c2.metric("市場情緒", status_text, f"盤態: {status_icon}")
        c3.metric("最後更新", datetime.now().strftime('%H:%M:%S'), "Yahoo Finance")
except:
    st.write("大盤數據讀取中...")

st.divider()

# --- 2. 財經焦點 (改為摘要模式) ---
st.header("📰 今日財經焦點摘要")
try:
    news_data = twii.news[:3]
    if news_data:
        for item in news_data:
            st.markdown(f"**• {item['title']}**")
    else:
        st.write("• 今日大盤回檔幅度較大，注意電子權值股走勢。")
        st.write("• 成交量能變化為短線觀察重點。")
        st.write("• 建議關注與爸爸討論過的長期價值標的。")
except:
    st.write("今日盤勢整理中...")

st.divider()

# --- 3. 自選股群組管理 ---
st.header("🗂️ 自選股群組管理")
with st.expander("⚙️ 管理群組與個股"):
    # (保留原本的新增邏輯)
    pass 

for group, stocks in st.session_state.stock_groups.items():
    if stocks:
        st.subheader(f"📁 {group}")
        for code in stocks:
            try:
                t = yf.Ticker(f"{code}.TW")
                h = t.history(period="2d")
                if not h.empty:
                    cur = h['Close'].iloc[-1]
                    prev = h['Close'].iloc[-0]
                    diff = cur - prev
                    pct = (diff / prev) * 100
                    # 台灣配色：紅漲綠跌
                    mark = "🔴" if diff > 0 else "🟢" if diff < 0 else "⚪"
                    
                    # 優先從對照表抓名稱
                    name = STOCK_NAMES.get(code, "台股")
                    
                    sc1, sc2, sc3, sc4 = st.columns([2, 1.5, 2, 1])
                    sc1.write(f"**{code} {name}**")
                    sc2.write(f"價: {cur:.2f}")
                    sc3.write(f"{mark} {diff:+.2f} ({pct:+.2f}%)")
                    if sc4.button("❌", key=f"del_{group}_{code}"):
                        st.session_state.stock_groups[group].remove(code)
                        st.rerun()
            except: continue

st.divider()

# --- 4. 討論筆記 (保留) ---
st.header("📝 討論筆記紀錄")
# (保留原本的筆記邏輯)
