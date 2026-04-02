import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="台股投資戰情室", layout="wide")

# 隱藏預設箭頭
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_html=True)

# 常用個股對照
STOCK_NAMES = {"2330": "台積電", "2454": "聯發科", "2317": "鴻海", "0050": "元大台灣50"}

# 初始化資料
if 'stock_groups' not in st.session_state:
    st.session_state.stock_groups = {"電子": [{"code": "2330", "name": "台積電"}]}
if 'notes' not in st.session_state: 
    st.session_state.notes = []

# --- 1. 大盤區與實質分析 ---
st.title("🇹🇼 台股投資戰情室 3.0")
try:
    twii = yf.Ticker("^TWII")
    t_hist = twii.history(period="10d") # 抓久一點算均量
    if not t_hist.empty:
        now = t_hist.iloc[-1]
        prev = t_hist.iloc[-2]
        diff = now['Close'] - prev['Close']
        pct = (diff / prev['Close']) * 100
        
        # 情緒判定
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

        # --- 2. 實質財經焦點優化 (動態分析) ---
        st.header("📰 今日財經焦點摘要")
        
        # A. 權值股動向分析
        weights = ["2330", "2454", "2317"]
        w_status = []
        for w in weights:
            t_w = yf.Ticker(f"{w}.TW")
            h_w = t_w.history(period="2d")
            w_diff = h_w.iloc[-1]['Close'] - h_w.iloc[0]['Close']
            w_mark = "🔴漲" if w_diff > 0 else "🟢跌" if w_diff < 0 else "⚪平"
            w_status.append(f"{STOCK_NAMES[w]}{w_mark}")
        
        # B. 量能實質變化
        avg_vol = t_hist['Volume'].tail(5).mean()
        v_ratio = now['Volume'] / avg_vol
        v_desc = "放量 (超過5日均量)" if v_ratio > 1.2 else "縮量 (低於5日均量)" if v_ratio < 0.8 else "量能持平"
        
        # C. 產業題材 (抓取新聞標題)
        try:
            news = twii.news[:2]
            n_titles = [f"• {n['title']}" for n in news]
        except:
            n_titles = ["• 暫無即時新聞摘要"]

        st.info(f"""
        🔍 **實質觀察重點：**
        1. **權值股表現：** {', '.join(w_status)}。
        2. **量能變化：** 今日量能比為 {v_ratio:.2f}x，呈現 **{v_desc}**。
        3. **即時題材：**
        {chr(10).join(n_titles)}
        """)
except:
    st.write("數據讀取中...")

st.divider()

# --- 3. 自選股管理 ---
st.header("🗂️ 自選股群組管理")
with st.expander("⚙️ 管理分類與個股", expanded=False): # 預設關閉讓畫面乾淨
    col_g1, col_g2 = st.columns(2)
    new_g = col_g1.text_input("建立新分類")
    if col_g1.button("新增分類"):
        if new_g and new_g not in st.session_state.stock_groups:
            st.session_state.stock_groups[new_g] = []
            st.rerun()
            
    del_g = col_g2.selectbox("選擇要刪除的分類", ["請選擇"] + list(st.session_state.stock_groups.keys()))
    if col_g2.button("⚠️ 刪除整個分類"):
        if del_g != "請選擇":
            del st.session_state.stock_groups[del_g]
            st.rerun()
    
    st.write("---")
    target = st.selectbox("選擇存入分類", list(st.session_state.stock_groups.keys()))
    c_id = st.text_input("股票代碼")
    c_nm = st.text_input("股票名稱 (選填)")
    if st.button("確認加入個股"):
        if c_id:
            nm = c_nm if c_nm else STOCK_NAMES.get(c_id, "台股")
            st.session_state.stock_groups[target].append({"code": c_id, "name": nm})
            st.rerun()

# 顯示分組
for group_name, stock_list in st.session_state.stock_groups.items():
    st.subheader(f"📁 {group_name}")
    if not stock_list:
        st.caption("尚無個股")
        continue
    
    for item in stock_list:
        try:
            t_code = item['code']
            t_name = item['name']
            ticker = yf.Ticker(f"{t_code}.TW")
            h = ticker.history(period="2d")
            if not h.empty:
                c_p = h.iloc[-1]['Close']
                p_p = h.iloc[0]['Close']
                d = c_p - p_p
                p = (d / p_p) * 100
                m = "🔴" if d > 0 else "🟢" if d < 0 else "⚪"
                
                sc1, sc2, sc3, sc4 = st.columns([2, 1.5, 2, 1])
                sc1.write(f"**{t_code} {t_name}**")
                sc2.write(f"價: {c_p:.2f}")
                sc3.write(f"{m} {d:+.2f} ({p:+.2f}%)")
                if sc4.button("❌", key=f"del_{group_name}_{t_code}"):
                    st.session_state.stock_groups[group_name].remove(item)
                    st.rerun()
        except:
            st.caption(f"{item.get('code')} 讀取中...")

st.divider()

# --- 4. 討論筆記 ---
st.header("📝 討論筆記紀錄")
with st.form("note_form_v_final_3", clear_on_submit=True):
    n_t = st.text_input("議題主題")
    n_k = st.text_input("標籤")
    n_c = st.text_area("討論筆記")
    if st.form_submit_button("儲存紀錄"):
        if n_t:
            st.session_state.notes.append({"T": n_t, "K": [k.strip() for k in n_k.split(",")], "C": n_c})
            st.success("儲存成功")

if st.session_state.notes:
    tags = list(set([k for n in st.session_state.notes for k in n["K"] if k]))
    sel_tag = st.multiselect("💡 標籤過濾", tags)
    for n in reversed(st.session_state.notes):
        if not sel_tag or any(t in sel_tag for t in n["K"]):
            with st.expander(f"📌 {n['T']}"):
                st.write(n['C'])
