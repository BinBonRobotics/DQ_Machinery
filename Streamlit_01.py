import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH ---
st.set_page_config(page_title="Spare Part Management", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

# Hàm xử lý chuẩn hóa ID khách hàng (Chuyển 84366.0 thành "84366")
def clean_id(id_val):
    if pd.isna(id_val): return ""
    return str(id_val).split('.')[0].strip()

# --- A_1: SIDEBAR ---
with st.sidebar:
    st.header("📋 MENU")
    menu_option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- LOAD DATA ---
@st.cache_data(ttl=600)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST")
    contact = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact")
    staff = conn.read(spreadsheet=SHEET_URL, worksheet="Staff")
    machines = conn.read(spreadsheet=SHEET_URL, worksheet="List_of_ machines")
    return mst, contact, staff, machines

df_mst, df_contact, df_staff, df_mac = load_data()

# --- CHƯƠNG TRÌNH CHÍNH ---
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

        # 1. Lấy Customer Name (Cột C - Index 2)
        cust_names = df_mst.iloc[:, 2].dropna().unique()
        selected_cust = st.selectbox("👤 Customer Name:", options=cust_names)

        # Lấy thông tin Header từ Customer_MST
        cust_row = df_mst[df_mst.iloc[:, 2] == selected_cust].iloc[0]
        
        # 2. Customer No (Cột B) - CHUẨN HÓA ID
        c_no_val = clean_id(cust_row.iloc[1])
        st.text_input("🆔 Customer No:", value=c_no_val, disabled=True)

        # 3. Tax Code (Cột F) & 4. Address (Cột E)
        st.text_input("📑 Tax Code:", value=str(cust_row.iloc[5]), disabled=True)
        st.text_area("📍 Address:", value=str(cust_row.iloc[4]), disabled=True, height=70)

        col_l, col_r = st.columns(2)

        with col_l:
            # 5. Contact Person (Tab: Customer_Contact / Col H: Index 7)
            # So sánh Customer No ở Tab Contact (Cột B: Index 1)
            df_contact_clean = df_contact.copy()
            df_contact_clean.iloc[:, 1] = df_contact_clean.iloc[:, 1].apply(clean_id)
            
            contacts = df_contact_clean[df_contact_clean.iloc[:, 1] == c_no_val].iloc[:, 7].dropna().unique()
            st.selectbox("📞 Contact Person:", options=contacts if len(contacts)>0 else ["N/A"])

            # 6. Officer (Tab: Staff / Col B: Index 1)
            staff_list = df_staff.iloc[:, 1].dropna().unique()
            st.selectbox("👨‍💼 Officer:", options=staff_list)

        with col_r:
            # 7. Machine Number (Tab: List_of_ machines / Col O: Index 14)
            # So sánh Customer No ở Tab Machines (Cột B: Index 1)
            df_mac_clean = df_mac.copy()
            df_mac_clean.iloc[:, 1] = df_mac_clean.iloc[:, 1].apply(clean_id)
            
            # Lấy cột O (Index 14)
            macs = df_mac_clean[df_mac_clean.iloc[:, 1] == c_no_val].iloc[:, 14].dropna().unique()
            st.selectbox("🤖 Machine Number:", options=macs if len(macs)>0 else ["N/A"])

            st.date_input("📅 Offer Date:", value=datetime.now())

        # 9. Offer No
        off_no = f"{datetime.now().year}-{datetime.now().month:02d}-0001"
        st.text_input("🆔 Offer No:", value=off_no)

    elif st.session_state.offer_mode == "manage":
        st.info("Order Management - Coming Soon")
