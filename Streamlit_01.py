import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ thống Báo giá", layout="wide")

# Link Google Sheet của bạn
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8/edit#gid=903775380"

# --- 2. HÀM KẾT NỐI VÀ LOAD DỮ LIỆU ---
@st.cache_data(ttl=60)
def load_data():
    try:
        # Kết nối trực tiếp bằng URL để tránh lỗi "Spreadsheet must not be None"
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Đọc tab Customer_MST (Dựa trên ảnh: Col B=No, Col C=Name, Col F=Tax)
        df_mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST").dropna(how='all')
        
        return df_mst
    except Exception as e:
        st.error(f"Lỗi kết nối dữ liệu: {e}")
        return None

df_mst = load_data()

# --- 3. LAYOUT A_1: SIDE MENU ---
with st.sidebar:
    st.header("MENU")
    option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 4. LAYOUT A_2 & B_FUNCTIONS ---
if df_mst is not None and option == "Spare Part Quotation":
    # Tạo 2 button bên phải
    col_btn1, col_btn2, _ = st.columns([2, 2, 5])
    btn_new = col_btn1.button("New Spare Part Offer", use_container_width=True)
    btn_manage = col_btn2.button("Order Management", use_container_width=True)

    # Quản lý trạng thái hiển thị
    if "show_form" not in st.session_state:
        st.session_state.show_form = False
    
    if btn_new: st.session_state.show_form = True
    if btn_manage: st.session_state.show_form = False

    # Hiển thị Form khi bấm "New Spare Part Offer"
    if st.session_state.show_form:
        st.divider()
        
        # B_1: Customer Name (Drop menu từ Cột C - index 2)
        # Dựa trên ảnh: Cột C là 'Customer name'
        names = df_mst.iloc[:, 2].dropna().unique().tolist()
        selected_name = st.selectbox("Customer Name:", options=names)
        
        # Tìm dòng dữ liệu khách hàng
        cust_info = df_mst[df_mst.iloc[:, 2] == selected_name].iloc[0]
        
        # B_2: Customer No (Lấy từ Cột B - index 1)
        # Chuyển về string và xử lý số (ví dụ 54682.0 thành 54682)
        c_no = str(cust_info.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=c_no, disabled=True)
        
        # B_3: Tax Code (Lấy từ Cột F - index 5)
        t_code = str(cust_info.iloc[5]) if not pd.isna(cust_info.iloc[5]) else ""
        st.text_input("Tax Code:", value=t_code, disabled=True)

elif df_mst is None:
    st.warning("Không thể tải dữ liệu. Vui lòng kiểm tra lại quyền chia sẻ của file Google Sheets (Chọn 'Anyone with the link can view').")
