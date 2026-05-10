import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Spare Part Management", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0 (Thay link của bạn tại đây)"

# --- A_1: SIDEBAR ---
with st.sidebar:
    st.header("📋 MENU")
    menu_option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    st.write("---")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- LOAD DATA ---
@st.cache_data(ttl=600)
def load_all_tabs():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Tải toàn bộ các tab cần thiết
    mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST")
    contact = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact")
    staff = conn.read(spreadsheet=SHEET_URL, worksheet="Staff")
    machines = conn.read(spreadsheet=SHEET_URL, worksheet="List_of_ machines")
    return mst, contact, staff, machines

try:
    df_mst, df_contact, df_staff, df_mac = load_all_tabs()
except Exception as e:
    st.error(f"Lỗi kết nối Google Sheets: {e}")
    st.stop()

# --- CHƯƠNG TRÌNH CHÍNH ---
if menu_option == "Spare Part Quotation":
    # A_2: 2 Button điều hướng
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        btn_new = st.button("➕ New Spare Part Offer", use_container_width=True)
    with col_btn2:
        btn_manage = st.button("📋 Order Management", use_container_width=True)

    # State quản lý tab
    if "offer_mode" not in st.session_state:
        st.session_state.offer_mode = "new"
    if btn_new: st.session_state.offer_mode = "new"
    if btn_manage: st.session_state.offer_mode = "manage"

    # B_1: CHỨC NĂNG TẠO OFFER MỚI
    if st.session_state.offer_mode == "new":
        st.write("### 🆕 New Spare Part Offer")
        
        # 1. Customer Name (Col C - Index 2)
        cust_list = df_mst.iloc[:, 2].dropna().unique()
        selected_cust = st.selectbox("👤 Customer Name:", options=cust_list)

        # Lấy thông tin từ Customer_MST
        cust_row = df_mst[df_mst.iloc[:, 2] == selected_cust]
        
        if not cust_row.empty:
            # 2. Customer No (Col B - Index 1) - Ép về String để hiển thị và filter
            cust_no_val = str(cust_row.iloc[0, 1]).split('.')[0] # Bỏ phần .0 nếu là số
            st.text_input("🆔 Customer No:", value=cust_no_val, disabled=True)

            # 3. Tax Code (Col F - Index 5)
            tax_code = str(cust_row.iloc[0, 5]) if pd.notnull(cust_row.iloc[0, 5]) else "N/A"
            st.text_input("📑 Tax Code:", value=tax_code, disabled=True)

            # 4. Address (Col E - Index 4)
            address = str(cust_row.iloc[0, 4])
            st.text_area("📍 Address:", value=address, disabled=True, height=100)

            # Chia cột cho các drop menu tiếp theo
            c1, c2 = st.columns(2)

            with c1:
                # 5. Contact Person (Tab: Customer_Contact / Col H - Index 7)
                # Quan trọng: Filter bằng Customer No (Tab Contact nằm ở Col B - Index 1)
                # Ép kiểu toàn bộ cột ID của tab Contact về string để so sánh
                df_contact.iloc[:, 1] = df_contact.iloc[:, 1].astype(str).str.split('.').str[0]
                
                filtered_contacts = df_contact[df_contact.iloc[:, 1] == cust_no_val].iloc[:, 7].dropna().unique()
                st.selectbox("📞 Contact Person:", options=filtered_contacts if len(filtered_contacts) > 0 else ["No contact found"])

                # 6. Officer (Tab: Staff / Col B - Index 1)
                staff_list = df_staff.iloc[:, 1].dropna().unique()
                st.selectbox("👨‍💼 Officer:", options=staff_list)

            with c2:
                # 7. Machine Number (Tab: List_of_machines / Col O - Index 14)
                # Filter bằng Customer No (Tab Machines nằm ở Col B - Index 1)
                df_mac.iloc[:, 1] = df_mac.iloc[:, 1].astype(str).str.split('.').str[0]
                
                filtered_mac = df_mac[df_mac.iloc[:, 1] == cust_no_val].iloc[:, 14].dropna().unique()
                st.selectbox("🤖 Machine Number:", options=filtered_mac if len(filtered_mac) > 0 else ["No machine found"])

                # 8. Offer Date
                st.date_input("📅 Offer Date:", value=datetime.now())

            # 9. Offer No (User nhập tay hoặc theo mẫu)
            curr_year = datetime.now().year
            curr_month = datetime.now().month
            default_off_no = f"{curr_year}-{curr_month:02d}-0001"
            st.text_input("🆔 Offer No:", value=default_off_no)

            st.divider()
            st.success("Thông tin Header đã sẵn sàng. Bạn có thể tiếp tục thiết kế phần nhập liệu Part Number bên dưới.")

    elif st.session_state.offer_mode == "manage":
        st.info("Trang Order Management đang được cập nhật...")

else:
    st.title("🛠️ Service Quotation")
    st.write("Tính năng này hiện chưa có yêu cầu chi tiết.")
