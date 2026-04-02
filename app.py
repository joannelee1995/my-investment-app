import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 網頁設定
st.set_page_config(page_title="台股永久戰情室", layout="wide")

# 隱藏預設箭頭
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_html=True)

# 1. 連接 Google Sheets
SP_URL = "https://docs.google.com/spreadsheets/d/1pSVEg5J_-tg0wetPxNUVb9cU6kapUL_NIEV_Xz84PDM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_cloud_data():
    try:
        s_df = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl="1s")
        n_df = conn.read(spreadsheet=SP_URL, worksheet="notes", ttl="1s")
        return s_df.dropna(how='all'), n_df.dropna(how='all')
    except:
        return pd.DataFrame(columns=["group", "code", "name"]), pd.DataFrame(columns=["title", "tags", "content", "date"])

stocks_df, notes_df = load_cloud_data()

# --- 2. 大盤與動態焦點 ---
st.title("🇹🇼 台股永久戰情室 3.0")
try:
    twii = yf.Ticker("^TWII")
    t_hist = twii.history(period="10d")
    if not t_hist.empty:
        now, prev = t_hist.iloc[-1], t_hist.iloc[-2]
        diff, pct = now['Close'] - prev['Close'], (now['Close'] - prev['Close']) / prev['Close'] * 100
        
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
        st.header("📰 今日財經焦點摘要")
        w_status = []
        for w, w_n in {"2330":"台積電", "2454":"聯發科", "2317":"鴻海"}.items():
            h_w = yf.Ticker(f"{w}.TW").history(period="2d")
            if not h_w.empty:
                w_d = h_w.iloc[-1]['Close'] - h_w.iloc[0]['Close']
                w_m = "🔴漲" if w_d > 0 else "🟢跌" if w_d < 0 else "⚪平"
                w_status.append(f"{w_n}{w_m}")
        st.info(f"🔍 **實質觀察：** 權值股({', '.join(w_status)})。數據由 Yahoo Finance 提供。")
except:
    st.write("數據加載中...")

st.divider()

# --- 3. 自選股管理 (寫入 Google Sheets) ---
st.header("🗂️ 自選股群組管理")
with st.expander("⚙️ 管理雲端清單 (展開編輯)", expanded=True):
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        new_g_name = st.text_input("輸入新分類名稱", key="new_g")
        if st.button("建立空分類"):
            if new_g_name and new_g_name not in stocks_df['group'].unique():
                new_row = pd.DataFrame([{"group": new_g_name, "code": "9999", "name": "新分類標籤"}])
                updated = pd.concat([stocks_df, new_row], ignore_index=True)
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
                st.success(f"分類 {new_g_name} 已同步")
                st.rerun()

    with col_g2:
        all_gs = ["請選擇"] + list(stocks_df['group'].unique())
        target_g = st.selectbox("選擇要刪除的分類", all_gs)
        if st.button("⚠️ 刪除整個分類"):
            if target_g != "請選擇":
                updated = stocks_df[stocks_df['group'] != target_g]
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
                st.rerun()

    st.write("---")
    current_gs = list(stocks_df['group'].unique())
    target_s_g = st.selectbox("選擇存入分類", current_gs if current_gs else ["請先建立分類"])
    col_s1, col_s2 = st.columns(2)
    in_c, in_n = col_s1.text_input("股票代碼"), col_s2.text_input("股票名稱")
    if st.button("🚀 確認存入雲端個股"):
        if target_s_g and in_c:
            clean_df = stocks_df[~((stocks_df['group'] == target_s_g) & (stocks_df['code'] == "9999"))]
            new_data = pd.DataFrame([{"group": target_s_g, "code": in_c, "name": in_n}])
            updated = pd.concat([clean_df, new_data], ignore_index=True)
            conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
            st.success("已同步至雲端！")
            st.rerun()

# 顯示分組與個股
for g in stocks_df['group'].unique():
    st.subheader(f"📁 {g}")
    g_list = stocks_df[stocks_df['group'] == g]
    if len(g_list) == 1 and str(g_list.iloc[0]['code']) == "9999":
        st.caption("此分類目前尚無個股")
        continue
    for _, row in g_list.iterrows():
        if str(row['code']) == "9999": continue
        try:
            t_c, t_n = str(row['code']), str(row['name'])
            tk = yf.Ticker(f"{t_c}.TW")
            h = tk.history(period="2d")
            if not h.empty:
                cp, pp = h.iloc[-1]['Close'], h.iloc[0]['Close']
                d, p = cp - pp, ((cp - pp)/pp)*100
                m = "🔴" if d > 0 else "🟢" if d < 0 else "⚪"
                sc1, sc2, sc3, sc4 = st.columns([2, 1.5, 2, 1])
                sc1.write(f"**{t_c} {t_n}**")
                sc2.write(f"價: {cp:.2f}")
                sc3.write(f"{m} {d:+.2f} ({p:+.2f}%)")
                if sc4.button("❌", key=f"del_{g}_{t_c}"):
                    # 修正：精準刪除對應的個股
                    updated = stocks_df[~((stocks_df['group'] == g) & (stocks_df['code'].astype(str) == t_c))]
                    conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
                    st.rerun()
        except:
            st.caption(f"{row['code']} 讀取中...")

st.divider()

# --- 4. 討論筆記 (同步雲端) ---
st.header("📝 討論筆記紀錄")
with st.form("cloud_note_form", clear_on_submit=True):
    n_t, n_k = st.text_input("議題主題"), st.text_input("標籤")
    n_c = st.text_area("討論筆記內容")
    if st.form_submit_button("永久儲存筆記"):
        if n_t:
            new_note = pd.DataFrame([{"title": n_t, "tags": n_k, "content": n_c, "date": datetime.now().strftime("%Y-%m-%d")}])
            updated = pd.concat([notes_df, new_note], ignore_index=True)
            conn.update(spreadsheet=SP_URL, worksheet="notes", data=updated)
            st.success("筆記已存入雲端！")
            st.rerun()

if not notes_df.empty:
    for _, n in notes_df.iloc[::-1].iterrows(): 
        with st.expander(f"📌 {n['title']} ({n['date']})"):
            st.caption(f"標籤: {n['tags']}")
            st.write(n['content'])
