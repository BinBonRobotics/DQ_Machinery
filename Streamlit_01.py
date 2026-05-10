import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Spare Part Management", layout="wide")

# Link Google Sheet của bạn
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

# --- A_1: SIDEBAR LAYOUT ---
with st.sidebar:
    st.header("📋 MENU")
    menu_option = st.radio(
        "Lựa chọn dịch vụ:",
        ["Spare Part Quotation", "Service Quotation"]
    )
    st.write("---")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# --- HÀM TẢI DỮ LIỆU ---
@st.cache_data(ttl=600)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = {
        "mst": conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST"),
        "contact": conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact"),
        "staff": conn.read(spreadsheet=SHEET_URL, worksheet="Staff"),
        "machines": conn.read(spreadsheet=SHEET_URL, worksheet="List_of_ machines"),
    }
    return data

# --- LOGIC XỬ LÝ CHÍNH ---
data = load_data()

if menu_option == "Spare Part Quotation":
    # --- A_2: TWO BUTTONS ON RIGHT ---
    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav1:
        btn_new = st.button("➕ New Spare Part Offer", use_container_width=True)
    with col_nav2:
        btn_manage = st.button("📋 Order Management", use_container_width=True)

    # Quản lý trạng thái hiển thị
    if "sub_page" not in st.session_state:
        st.session_state.sub_page = "new"
    
    if btn_new: st.session_state.sub_page = "new"
    if btn_manage: st.session_state.sub_page = "manage"

    # --- B: FUNCTIONS - NEW SPARE PART OFFER ---
    if st.session_state.sub_page == "new":
        st.subheader("🆕 Create New Spare Part Offer")
        
        # 1. Customer Name (Tab: Customer_MST, Col C)
        mst_df = data["mst"]
        # Col C là index 2 (Customer name)
        cust_list = mst_df.iloc[:, 2].dropna().unique()
        selected_cust = st.selectbox("👤 Customer Name:", options=cust_list)

        # Lấy row tương ứng với khách hàng được chọn
        cust_row = mst_df[mst_df.iloc[:, 2] == selected_cust]

        if not cust_row.empty:
            # 2. Customer No (Col B - index 1)
            cust_no = str(cust_row.iloc[0, 1])
            st.text_input("🆔 Customer No:", value=cust_no, disabled=True)

            # 3. Tax Code (Col F - index 5)
            tax_code = str(cust_row.iloc[0, 5])
            st.text_input("📑 Tax Code:", value=tax_code, disabled=True)

            # 4. Address (Col E - index 4)
            address = str(cust_row.iloc[0, 4])
            st.text_area("📍 Address:", value=address, disabled=True, height=80)

            col1, col2 = st.columns(2)
            
            with col1:
                # 5. Contact Person (Tab: Customer_Contact, Col H - index 7)
                # Filter bằng Customer No
                contact_df = data["contact"]
                # Ép kiểu string để so sánh
                contact_df.iloc[:, 1] = contact_df.iloc[:, 1].astype(str)
                filtered_contacts = contact_df[contact_df.iloc[:, 1] == cust_no].iloc[:, 7].dropna().unique()
                st.selectbox("📞 Contact Person:", options=filtered_contacts if len(filtered_contacts)>0 else ["N/A"])

                # 6. Officer (Tab: Staff, Col B - index 1)
                staff_list = data["staff"].iloc[:, 1].dropna().unique()
                st.selectbox("👨‍💼 Officer:", options=staff_list)

            with col2:
                # 7. Machine Number (Tab: List_of_machines, Col O - index 14)
                # Filter bằng Customer No (Col B - index 1)
                mac_df = data["machines"]
                mac_df.iloc[:, 1] = mac_df.iloc[:, 1].astype(str)
                filtered_mac = mac_df[mac_df.iloc[:, 1] == cust_no].iloc[:, 14].dropna().unique()
                st.selectbox("🤖 Machine Number:", options=filtered_mac if len(filtered_mac)>0 else ["N/A"])

                # 8. Offer Date
                st.date_input("📅 Offer Date:", value=datetime.now())

            # 9. Offer No (Year-Month-0001)
            default_offer_no = f"{datetime.now().year}-{datetime.now().month:02d}-0001"
            st.text_input("🆔 Offer No:", value=default_offer_no)
            
            st.write("---")
            st.info("Tính năng nhập Part Number và tính toán giá sẽ ở phần tiếp theo.")

    elif st.session_state.sub_page == "manage":
        st.subheader("📋 Order Management System")
        st.warning("Tính năng đang được xây dựng...")

elif menu_option == "Service Quotation":
    st.title("🛠️ Service Quotation")
    st.write("Đây là trang dành cho báo giá dịch vụ.")
