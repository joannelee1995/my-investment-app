import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf

st.set_page_config(page_title="Lee 投資戰情室 2.0", layout="wide")

# --- 初始化資料儲存 (實際應用建議串接 Google Sheets，目前為暫時儲存) ---
if 'notes' not in st.session_state:
    st.session_state.notes = []
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = set(["2330.TW", "0050.TW"])
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

st.title("👨‍👦 Lee 投資戰情室 2.0")

# --- 第一部分：討論紀錄與議題關聯 ---
st.header("📝 討論紀錄與議題地圖")
with st.expander("➕ 新增討論筆記", expanded=True):
    with st.form("note_form", clear_on_submit=True):
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            topic = st.text_input("討論主題")
        with t_col2:
            keywords = st.text_input("關鍵字 (請用逗號隔開, 如: 半導體, 殖利率)")
        content = st.text_area("討論重點摘要")
        if st.form_submit_button("儲存筆記"):
            if topic and keywords:
                st.session_state.notes.append({
                    "主題": topic, 
                    "關鍵字": [k.strip() for k in keywords.split(",")], 
                    "內容": content
                })
                st.success("筆記已存檔！")

# 呈現關聯性 (以關鍵字篩選)
if st.session_state.notes:
    all_tags = []
    for n in st.session_state.notes:
        all_tags.extend(n["關鍵字"])
    unique_tags = list(set(all_tags))
    
    st.write("🔍 **點擊關鍵字篩選相關議題：**")
    selected_tag = st.multiselect("選擇標籤以查看關聯紀錄", unique_tags)
    
    for n in reversed(st.session_state.notes):
        if not selected_tag or any(tag in selected_tag for tag in n["關鍵字"]):
            with st.expander(f"📌 {n['主題']} | 標籤: {', '.join(n['關鍵字'])}"):
                st.write(n['內容'])

st.divider()

# --- 第二部分：即時個股追蹤 ---
st.header("📈 自選股監控")
add_stock = st.text_input("新增自選股代碼 (如: 0056.TW)", "").upper()
if st.button("加入清單"):
    st.session_state.watchlist.add(add_stock)

if st.session_state.watchlist:
    stock_data = []
    for symbol in st.session_state.watchlist:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            # 取得漲跌與漲跌幅
            prev_close = ticker.history(period="2d")['Close'].iloc[0]
            current_price = info['last_price']
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100
            
            stock_data.append({
                "代碼": symbol,
                "現價": f"{current_price:.2f}",
                "漲跌": f"{change:+.2f}",
                "漲跌幅": f"{change_pct:+.2f}%"
            })
        except:
            continue
    
    st.table(pd.DataFrame(stock_data))

st.divider()

# --- 第三部分：資產配置圖像化 ---
st.header("💰 資產配置明細")
with st.expander("➕ 新增持有部位"):
    with st.form("asset_form"):
        a_col1, a_col2, a_col3 = st.columns(3)
        with a_col1:
            a_name = st.text_input("投資項目/股票名稱")
        with a_col2:
            a_cost = st.number_input("買入總成本 (萬)", min_value=0.0)
        with a_col3:
            a_type = st.selectbox("類型", ["台股", "美股", "ETF", "現金/定存"])
        if st.form_submit_button("加入配置"):
            st.session_state.portfolio.append({"名稱": a_name, "成本": a_cost, "類型": a_type})

if st.session_state.portfolio:
    df_p = pd.DataFrame(st.session_state.portfolio)
    # 圖表呈現
    fig_type = px.pie(df_p, values='成本', names='類型', title="依資產類型分佈", hole=0.4)
    fig_name = px.sunburst(df_p, path=['類型', '名稱'], values='成本', title="資產明細結構")
    
    p_col1, p_col2 = st.columns(2)
    with p_col1:
        st.plotly_chart(fig_type, use_container_width=True)
    with p_col2:
        st.plotly_chart(fig_name, use_container_width=True)
