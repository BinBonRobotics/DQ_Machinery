import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH ---
st.set_page_config(page_title="Spare Part Management", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

# --- TẢI DỮ LIỆU ---
@st.cache_data(ttl=600)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Ép kiểu string toàn bộ bảng để không mất số 0 đầu ở Tax Code và Customer No
    mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST", dtype=str)
    contact = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact", dtype=str)
    staff = conn.read(spreadsheet=SHEET_URL, worksheet="Staff", dtype=str)
    machines = conn.read(spreadsheet=SHEET_URL, worksheet="List_of_ machines", dtype=str)
    return mst, contact, staff, machines

# Xử lý lỗi kết nối
try:
    df_mst, df_contact, df_staff, df_mac = load_data()
except Exception as e:
    st.error(f"Lỗi kết nối dữ liệu: {e}")
    st.stop()

# --- CHƯƠNG TRÌNH CHÍNH ---
with st.sidebar:
    st.header("📋 MENU")
    menu_option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if menu_option == "Spare Part Quotation":
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("➕ New Spare Part Offer", use_container_width=True):
            st.session_state.offer_mode = "new"
    with c_btn2:
        if st.button("📋 Order Management", use_container_width=True):
            st.session_state.offer_mode = "manage"

    if "offer_mode" not in st.session_state:
        st.session_state.offer_mode = "new"

    if st.session_state.offer_mode == "new":
        st.subheader("🆕 Create New Spare Part Offer")

        # 1. Customer Name (Cột C - Index 2)
        cust_list = df_mst.iloc[:, 2].dropna().unique()
        selected_cust = st.selectbox("👤 Customer Name:", options=cust_list)

        # Lấy thông tin khách hàng
        cust_info = df_mst[df_mst.iloc[:, 2] == selected_cust].iloc[0]
        
        # 2. Customer No (Cột B - Index 1) - Hiện dạng Text gốc
        c_no_val = str(cust_info.iloc[1]).strip()
        st.text_input("🆔 Customer No:", value=c_no_val, disabled=True)

        # 3. Tax Code (Cột F - Index 5) - GIỮ NGUYÊN SỐ 0 ĐẦU
        tax_val = str(cust_info.iloc[5]).strip()
        # Nếu Tax Code bị null trong sheet thì hiện trống
        tax_display = "" if tax_val.lower() == "nan" else tax_val
        st.text_input("📑 Tax Code:", value=tax_display, disabled=True)

        # 4. Address (Cột E - Index 4)
        st.text_area("📍 Address:", value=str(cust_info.iloc[4]), disabled=True, height=70)

        col_l, col_r = st.columns(2)

        with col_l:
            # 5. Contact Person (Tab: Customer_Contact)
            # Filter theo Customer No (Cột B - Index 1 của tab Contact)
            # Lấy giá trị tại cột H (Index 7)
            contacts = df_contact[df_contact.iloc[:, 1].str.strip() == c_no_val].iloc[:, 7].dropna().unique()
            st.selectbox("📞 Contact Person:", options=contacts if len(contacts) > 0 else ["N/A"])

            # 6. Officer (Tab: Staff - Cột B)
            staff_list = df_staff.iloc[:, 1].dropna().unique()
            st.selectbox("👨‍💼 Officer:", options=staff_list)

        with col_r:
            # 7. Machine Number (Tab: List_of_ machines)
            # Filter theo Customer No (Cột B - Index 1 của tab Machines)
            # Lấy giá trị tại cột O (Index 14)
            # Dùng try-except để tránh lỗi nếu bảng không đủ cột
            try:
                machines_list = df_mac[df_mac.iloc[:, 1].str.strip() == c_no_val].iloc[:, 14].dropna().unique()
            except:
                machines_list = []
            st.selectbox("🤖 Machine Number:", options=machines_list if len(machines_list) > 0 else ["N/A"])

            st.date_input("📅 Offer Date:", value=datetime.now())

        # 9. Offer No
        off_no = f"{datetime.now().year}-{datetime.now().month:02d}-0001"
        st.text_input("🆔 Offer No:", value=off_no)

    elif st.session_state.offer_mode == "manage":
        st.info("Order Management Mode")
