import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CẤU HÌNH TRANG ---
st.set_page_config(layout="wide")

# --- KẾT NỐI & LOAD DỮ LIỆU ---
@st.cache_data(ttl=60)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Load tab Customer_MST và loại bỏ các dòng trống
    df = conn.read(worksheet="Customer_MST").dropna(how='all')
    return df

try:
    df_mst = load_data()
except Exception as e:
    st.error(f"Lỗi kết nối: {e}")
    st.stop()

# --- A_1: SIDE MENU (LEFT SIDE) ---
with st.sidebar:
    st.title("MENU")
    menu_opt = st.radio("Chuyên mục:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- A_2 & B_FUNCTIONS: SPARE PART QUOTATION ---
if menu_opt == "Spare Part Quotation":
    # Tạo 2 button bên phải
    col_n1, col_n2, _ = st.columns([2, 2, 5])
    btn_new = col_n1.button("New Spare Part Offer", use_container_width=True)
    btn_manage = col_n2.button("Order Management", use_container_width=True)

    # Quản lý trạng thái hiển thị bằng Session State
    if "view" not in st.session_state: st.session_state.view = None
    if btn_new: st.session_state.view = "New"
    if btn_manage: st.session_state.view = "Manage"

    # 1. Chức năng Click "New Spare Part Offer"
    if st.session_state.view == "New":
        st.markdown("---")
        
        # + Customer Name: Drop menu (Ref Col C -> index 2)
        cust_list = df_mst.iloc[:, 2].dropna().unique().tolist()
        selected_name = st.selectbox("Customer Name:", options=cust_list)
        
        # Lấy row dữ liệu tương ứng với Name đã chọn
        cust_row = df_mst[df_mst.iloc[:, 2] == selected_name].iloc[0]
        
        # + Customer No: (Ref Col B -> index 1)
        # Convert sang string và xóa đuôi .0 nếu có
        c_no = str(cust_row.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=c_no, disabled=True)
        
        # + Tax Code: (Ref Col F -> index 5)
        tax_code = str(cust_row.iloc[5]) if not pd.isna(cust_row.iloc[5]) else ""
        st.text_input("Tax Code:", value=tax_code, disabled=True)

    elif st.session_state.view == "Manage":
        st.info("Trang Order Management")

# --- SERVICE QUOTATION ---
else:
    st.write("Nội dung Service Quotation")
