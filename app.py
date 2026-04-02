import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 網頁基本設定
st.set_page_config(page_title="台股投資戰情室", layout="wide")

# 隱藏預設箭頭
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_html=True)

# 1. 連接 Google Sheets
SP_URL = "https://docs.google.com/spreadsheets/d/1pSVEg5J_-tg0wetPxNUVb9cU6kapUL_NIEV_Xz84PDM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        s_df = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl="1s")
        n_df = conn.read(spreadsheet=SP_URL, worksheet="notes", ttl="1s")
        # 強制轉為字串，避免數字格式出現 .0
        s_df['code'] = s_df['code'].astype(str).str.replace(".0", "", regex=False)
        return s_df.dropna(how='all'), n_df.dropna(how='all')
    except:
        return pd.DataFrame(columns=["group", "code", "name"]), pd.DataFrame(columns=["title", "tags", "content", "date"])

stocks_df, notes_df = load_data()

# --- 2. 大盤與動態焦點 ---
st.title("🇹🇼 台股投資戰情室 3.0")
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
        avg_vol = t_hist['Volume'].tail(5).mean()
        v_ratio = now['Volume'] / avg_vol if avg_vol > 0 else 0
        v_desc = "放量" if v_ratio > 1.2 else "縮量" if v_ratio < 0.8 else "量能持平"
        st.info(f"🔍 **實質觀察：** 權值股({', '.join(w_status)})。量能比 {v_ratio:.2f}x ({v_desc})。")
except:
    st.write("大盤載入中...")

st.divider()

# --- 3. 自選股管理 ---
st.header("🗂️ 自選股群組管理")
with st.expander("⚙️ 點此管理分類或個股", expanded=False):
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.write("**分類管理**")
        new_g = st.text_input("輸入新分類名稱")
        if st.button("建立分類"):
            if new_g and new_g not in stocks_df['group'].unique():
                new_row = pd.DataFrame([{"group": new_g, "code": "9999", "name": "PLACEHOLDER"}])
                updated = pd.concat([stocks_df, new_row], ignore_index=True)
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
                st.rerun()
    with col_g2:
        st.write("**刪除管理**")
        all_gs = ["請選擇"] + list(stocks_df['group'].unique())
        target_g_del = st.selectbox("選擇要刪除的分類", all_gs)
        if st.button("⚠️ 刪除整個分類"):
            if target_g_del != "請選擇":
                updated = stocks_df[stocks_df['group'] != target_g_del]
                conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
                st.rerun()
    st.write("---")
    st.write("**個股新增**")
    current_gs = list(stocks_df['group'].unique())
    target_g_add = st.selectbox("選擇存入分類", current_gs if current_gs else ["請先建立分類"])
    col_s1, col_s2 = st.columns(2)
    in_c = col_s1.text_input("股票代碼 (例: 2330)")
    in_n = col_s2.text_input("股票名稱")
    if st.button("🚀 確認永久存入個股"):
        if target_g_add != "請先建立分類" and in_c:
            # 去除 placeholder
            clean_df = stocks_df[~((stocks_df['group'] == target_g_add) & (stocks_df['code'] == "9999"))]
            new_s = pd.DataFrame([{"group": target_g_add, "code": str(in_c), "name": in_n}])
            updated = pd.concat([clean_df, new_s], ignore_index=True)
            conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
            st.rerun()

# 顯示與過濾邏輯
for g in stocks_df['group'].unique():
    st.subheader(f"📁 {g}")
    sub_df = stocks_df[stocks_df['group'] == g]
    if len(sub_df) == 1 and str(sub_df.iloc[0]['code']) == "9999":
        st.caption("目前無個股")
        continue
    for _, row in sub_df.iterrows():
        t_c = str(row['code']).split('.')[0] # 再次確保沒有 .0
        if t_c == "9999" or not t_c: continue
        try:
            t_n = str(row['name'])
            # 自動補上 .TW
            yf_code = f"{t_c}.TW" if "." not in t_c else t_c
            tk = yf.Ticker(yf_code)
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
                    updated = stocks_df[~((stocks_df['group'] == g) & (stocks_df['code'].astype(str) == row['code']))]
                    conn.update(spreadsheet=SP_URL, worksheet="stocks", data=updated)
                    st.rerun()
        except:
            st.caption(f"{t_c} 讀取中...")

st.divider()

# --- 4. 討論筆記區 ---
st.header("📝 雲端筆記")
with st.form("note_persistent", clear_on_submit=True):
    n_t, n_k = st.text_input("主題"), st.text_input("標籤")
    n_c = st.text_area("討論筆記內容")
    if st.form_submit_button("儲存筆記"):
        if n_t:
            new_n = pd.DataFrame([{"title": n_t, "tags": n_k, "content": n_c, "date": datetime.now().strftime("%Y-%m-%d")}])
            updated = pd.concat([notes_df, new_n], ignore_index=True)
            conn.update(spreadsheet=SP_URL, worksheet="notes", data=updated)
            st.rerun()

if not notes_df.empty:
    for _, n in notes_df.iloc[::-1].iterrows():
        with st.expander(f"📌 {n['title']} ({n['date']})"):
            st.write(n['content'])
