import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="HOMAG Offer Management", layout="wide")

# --- ĐƯỜNG DẪN FILE (Đảm bảo file này nằm cùng thư mục với file .py) ---
EXCEL_FILE = "Test_Streamlit (5).xlsx"

# --- HÀM LOAD DỮ LIỆU ---
@st.cache_data
def load_data():
    if not os.path.exists(EXCEL_FILE):
        st.error(f"Không tìm thấy file '{EXCEL_FILE}'. Vui lòng kiểm tra lại tên file trong thư mục.")
        return None
    
    try:
        data = {
            "staff": pd.read_excel(EXCEL_FILE, sheet_name="Staff"),
            "customers": pd.read_excel(EXCEL_FILE, sheet_name="Customer_MST"),
            "contacts": pd.read_excel(EXCEL_FILE, sheet_name="Customer_Contact"),
            "products": pd.read_excel(EXCEL_FILE, sheet_name="SP_List"),
            "machines": pd.read_excel(EXCEL_FILE, sheet_name="List_of_ machines")
        }
        return data
    except Exception as e:
        st.error(f"Lỗi khi đọc các Sheet: {e}")
        return None

# --- GIAO DIỆN ĐĂNG NHẬP ---
def login_screen(df_staff):
    st.title("🔑 Đăng nhập hệ thống")
    col1, col2 = st.columns(2)
    with col1:
        email = st.text_input("Email")
        password = st.text_input("Mật khẩu", type="password")
        
        if st.button("Đăng nhập"):
            # Kiểm tra trong sheet Staff
            user = df_staff[(df_staff['Email'] == email) & (df_staff['Password'].astype(str) == str(password))]
            if not user.empty:
                st.session_state['logged_in'] = True
                st.session_state['user_name'] = user.iloc[0]['Name']
                st.rerun()
            else:
                st.error("Sai email hoặc mật khẩu!")

# --- GIAO DIỆN CHÍNH (TẠO OFFER) ---
def main_app(data):
    st.sidebar.title(f"Chào, {st.session_state['user_name']}")
    if st.sidebar.button("Đăng xuất"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.title("📄 Tạo Báo giá (Offer)")

    # --- PHẦN 1: THÔNG TIN KHÁCH HÀNG ---
    with st.expander("1. Thông tin khách hàng", expanded=True):
        col1, col2 = st.columns(2)
        
        # Chọn khách hàng từ sheet Customer_MST
        cust_list = data['customers']['Customer name'].unique()
        selected_cust = col1.selectbox("Chọn khách hàng", cust_list)
        
        # Lấy thông tin chi tiết của khách hàng đó
        cust_info = data['customers'][data['customers']['Customer name'] == selected_cust].iloc[0]
        
        vat_code = col1.text_input("Mã số thuế", value=cust_info['Tax_Code'])
        address = col2.text_area("Địa chỉ", value=cust_info['Địa chỉ'], height=100)

    # --- PHẦN 2: THÔNG TIN SẢN PHẨM ---
    with st.expander("2. Chi tiết hàng hóa", expanded=True):
        # Tạo bảng chọn sản phẩm (giả lập dòng)
        if 'items' not in st.session_state:
            st.session_state.items = []

        # Chọn sản phẩm từ SP_List
        prod_list = data['products']['Part number'].astype(str) + " - " + data['products']['Part name']
        selected_prod_full = st.selectbox("Tìm sản phẩm (Part Number)", prod_list)
        
        col_q1, col_q2, col_q3 = st.columns([1, 1, 2])
        qty = col_q1.number_input("Số lượng", min_value=1, value=1)
        
        # Lấy giá bán từ cột 'Giá bán' trong sheet SP_List
        part_no = selected_prod_full.split(" - ")[0]
        prod_detail = data['products'][data['products']['Part number'].astype(str) == part_no].iloc[0]
        unit_price = prod_detail['Giá bán']
        
        if st.button("➕ Thêm vào danh sách"):
            st.session_state.items.append({
                "Part Number": part_no,
                "Description": prod_detail['Part name'],
                "Qty": qty,
                "Unit Price": unit_price,
                "Total": qty * unit_price
            })

        # Hiển thị danh sách đã thêm
        if st.session_state.items:
            df_items = pd.DataFrame(st.session_state.items)
            st.table(df_items)
            
            # Tính toán tổng
            subtotal = df_items['Total'].sum()
            vat_amount = subtotal * 0.08 # Giả định VAT 8%
            grand_total = subtotal + vat_amount
            
            st.write(f"**Tạm tính:** {subtotal:,.0f} VND")
            st.write(f"**Thuế VAT (8%):** {vat_amount:,.0f} VND")
            st.subheader(f"TỔNG CỘNG: {grand_total:,.0f} VND")

    if st.button("💾 Lưu và Xuất Offer"):
        st.success("Tính năng lưu vào sheet Offer_Header đang được thực hiện...")

# --- CHẠY CHƯƠNG TRÌNH ---
data = load_data()

if data:
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_screen(data['staff'])
    else:
        main_app(data)
