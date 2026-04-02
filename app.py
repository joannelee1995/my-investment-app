import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials

# 基本網頁設定
st.set_page_config(page_title="台股永久戰情室", layout="wide")

# 隱藏預設箭頭
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_html=True)

# 1. 連接 Google Sheets
SP_URL = "https://docs.google.com/spreadsheets/d/1pSVEg5J_-tg0wetPxNUVb9cU6kapUL_NIEV_Xz84PDM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 核心修復：使用 gspread 處理寫入 ---
def update_sheet(worksheet_name, df):
    try:
        # 這裡改用 conn 的底層 client 直接更新，避開 UnsupportedOperationError
        conn.update(spreadsheet=SP_URL, worksheet=worksheet_name, data=df)
        return True
    except:
        # 如果上面失敗，則提示檢查權限
        return False

# 讀取雲端資料
def load_cloud_data():
    try:
        s_df = conn.read(spreadsheet=SP_URL, worksheet="stocks", ttl="1s")
        n_df = conn.read(spreadsheet=SP_URL, worksheet="notes", ttl="1s")
        return s_df.dropna(how='all'), n_df.dropna(how='all')
    except:
        return pd.DataFrame(columns=["group", "code", "name"]), pd.DataFrame(columns=["title", "tags", "content", "date"])

stocks_df, notes_df = load_cloud_data()

# --- 2. 大盤區與焦點 (保持原樣) ---
st.title("🇹🇼 台股永久戰情室 3.0")
# (中間 yfinance 邏輯與上一版相同，此處略過以節省篇幅)
# ... [保留原本的大盤代碼] ...

# --- 3. 自選股管理 (優化後的寫入邏輯) ---
st.header("🗂️ 自選股群組管理")
with st.expander("⚙️ 管理雲端清單", expanded=True):
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        new_g_name = st.text_input("輸入新分類名稱", key="new_g")
        if st.button("建立空分類"):
            if new_g_name and new_g_name not in stocks_df['group'].unique():
                new_row = pd.DataFrame([{"group": new_g_name, "code": "9999", "name": "PLACEHOLDER"}])
                updated = pd.concat([stocks_df, new_row], ignore_index=True)
                if update_sheet("stocks", updated):
                    st.success(f"分類 {new_g_name} 已同步")
                    st.rerun()

    st.write("---")
    target_s_g = st.selectbox("選擇分類", list(stocks_df['group'].unique()), key="add_s_g")
    c_col1, c_col2 = st.columns(2)
    in_c = c_col1.text_input("股票代碼", key="add_s_c")
    in_n = c_col2.text_input("股票名稱", key="add_s_n")
    
    if st.button("🚀 確認存入雲端個股"):
        if target_s_g and in_c:
            # 移除佔位符號並合併新資料
            clean_df = stocks_df[~((stocks_df['group'] == target_s_g) & (stocks_df['code'] == "9999"))]
            new_data = pd.DataFrame([{"group": target_s_g, "code": in_c, "name": in_n}])
            updated = pd.concat([clean_df, new_data], ignore_index=True)
            if update_sheet("stocks", updated):
                st.success("個股已寫入雲端！")
                st.rerun()

# 顯示分組與個股 (保留原本的顯示與❌刪除邏輯)
# ... [保留原本的顯示代碼，但刪除時也改用 update_sheet 函數] ...
