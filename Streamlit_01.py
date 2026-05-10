import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH ---
st.set_page_config(page_title="Spare Part Management", layout="wide")
# Thay link Google Sheet của bạn vào đây
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

# --- A_1: SIDEBAR ---
with st.sidebar:
    st.header("📋 MENU")
    menu_option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    st.write("---")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- HÀM TẢI DỮ LIỆU AN TOÀN ---
@st.cache_data(ttl=600)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST")
    contact = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact")
    staff = conn.read(spreadsheet=SHEET_URL, worksheet="Staff")
    machines = conn.read(spreadsheet=SHEET_URL, worksheet="List_of_ machines")
    return mst, contact, staff, machines

# Xử lý lỗi kết nối ban đầu
try:
    df_mst, df_contact, df_staff, df_mac = load_data()
except Exception as e:
    st.error(f"Không thể kết nối Google Sheets. Vui lòng kiểm tra link hoặc quyền chia sẻ. Lỗi: {e}")
    st.stop()

# --- CHƯƠNG TRÌNH CHÍNH ---
if menu_option == "Spare Part Quotation":
    # A_2: Điều hướng
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("➕ New Spare Part Offer", use_container_width=True):
            st.session_state.offer_mode = "new"
    with c_btn2:
        if st.button("📋 Order Management", use_container_width=True):
            st.session_state.offer_mode = "manage"

    if "offer_mode" not in st.session_state:
        st.session_state.offer_mode = "new"

    # B_1: NEW SPARE PART OFFER
    if st.session_state.offer_mode == "new":
        st.subheader("🆕 Create New Spare Part Offer")

        # --- LẤY DỮ LIỆU KHÁCH HÀNG (Sửa lỗi KeyError ở đây) ---
        # Tìm cột "Customer name" (thường là cột C)
        col_name = "Customer name" if "Customer name" in df_mst.columns else df_mst.columns[2]
        col_no = "Customer\nno" if "Customer\nno" in df_mst.columns else df_mst.columns[1]
        col_tax = "Mã số thuế" if "Mã số thuế" in df_mst.columns else df_mst.columns[5]
        col_addr = "Địa chỉ" if "Địa chỉ" in df_mst.columns else df_mst.columns[4]

        cust_list = df_mst[col_name].dropna().unique()
        selected_cust = st.selectbox("👤 Customer Name:", options=cust_list)

        # Lọc thông tin khách hàng đã chọn
        cust_info = df_mst[df_mst[col_name] == selected_cust].iloc[0]
        
        # 2, 3, 4: Customer No, Tax Code, Address (Ép kiểu chuỗi)
        c_no_val = str(cust_info[col_no]).replace('.0', '')
        st.text_input("🆔 Customer No:", value=c_no_val, disabled=True)
        st.text_input("📑 Tax Code:", value=str(cust_info[col_tax]), disabled=True)
        st.text_area("📍 Address:", value=str(cust_info[col_addr]), disabled=True, height=80)

        # Cột chia đôi cho Contact, Officer, Machine...
        col_left, col_right = st.columns(2)

        with col_left:
            # 5. Contact Person (Tab: Customer_Contact)
            # Dùng cột "Customer contact" (Index 7) và "Customer no" (Index 1) để filter
            df_contact["Customer\nno"] = df_contact.iloc[:, 1].astype(str).str.replace('.0', '', regex=False)
            filtered_contacts = df_contact[df_contact["Customer\nno"] == c_no_val].iloc[:, 7].dropna().unique()
            st.selectbox("📞 Contact Person:", options=filtered_contacts if len(filtered_contacts) > 0 else ["N/A"])

            # 6. Officer (Tab: Staff, Cột B - Index 1)
            staff_list = df_staff.iloc[:, 1].dropna().unique()
            st.selectbox("👨‍💼 Officer:", options=staff_list)

        with col_right:
            # 7. Machine Number (Tab: List_of_ machines)
            # Cột B (Index 1) là Customer No, Cột O (Index 14) là Machine No.
            df_mac.iloc[:, 1] = df_mac.iloc[:, 1].astype(str).str.replace('.0', '', regex=False)
            filtered_mac = df_mac[df_mac.iloc[:, 1] == c_no_val].iloc[:, 14].dropna().unique()
            st.selectbox("🤖 Machine Number:", options=filtered_mac if len(filtered_mac) > 0 else ["N/A"])

            # 8. Offer Date
            st.date_input("📅 Offer Date:", value=datetime.now())

        # 9. Offer No
        off_no_default = f"{datetime.now().year}-{datetime.now().month:02d}-0001"
        st.text_input("🆔 Offer No:", value=off_no_default)

    elif st.session_state.offer_mode == "manage":
        st.info("Trang Quản lý đơn hàng (Đang phát triển)")

else:
    st.write("### Service Quotation - Coming Soon")
