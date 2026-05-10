import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- Cấu hình trang ---
st.set_page_config(page_title="Hệ thống Báo giá", layout="wide")

# --- Hàm load dữ liệu an toàn ---
@st.cache_data(ttl=60)
def load_all_tabs():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Đọc các tab quan trọng, bỏ qua dòng trống
        mst = conn.read(worksheet="Customer_MST").dropna(how='all')
        return mst
    except Exception as e:
        st.error(f"Lỗi kết nối: {e}")
        return None

df_mst = load_all_tabs()

# --- A_1: Side menu ---
with st.sidebar:
    st.header("MENU")
    menu = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- A_2: Spare Part Quotation ---
if df_mst is not None and menu == "Spare Part Quotation":
    col1, col2, _ = st.columns([2, 2, 5])
    btn_new = col1.button("New Spare Part Offer", use_container_width=True)
    btn_manage = col2.button("Order Management", use_container_width=True)

    # Khởi tạo view trong session_state
    if "view" not in st.session_state:
        st.session_state.view = None
    if btn_new: st.session_state.view = "new"
    if btn_manage: st.session_state.view = "manage"

    # --- B_Functions: New Spare Part Offer ---
    if st.session_state.view == "new":
        st.divider()
        
        # 1. Customer Name (Cột C)
        # Lấy danh sách từ cột có tiêu đề 'Customer name'
        cust_list = df_mst.iloc[:, 2].dropna().unique().tolist() 
        selected_name = st.selectbox("Customer Name:", options=cust_list)
        
        # Tìm dòng dữ liệu của khách hàng này
        customer_data = df_mst[df_mst.iloc[:, 2] == selected_name].iloc[0]
        
        # 2. Customer No (Cột B)
        # Lấy giá trị, chuyển về string và xử lý nếu là số (ví dụ: 54682.0 -> 54682)
        c_no = str(customer_data.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=c_no, disabled=True)
        
        # 3. Tax Code (Cột F)
        t_code = str(customer_data.iloc[5]) if not pd.isna(customer_data.iloc[5]) else ""
        st.text_input("Tax Code:", value=t_code, disabled=True)

elif df_mst is None:
    st.warning("Vui lòng kiểm tra cấu hình Secrets và URL Google Sheets.")
