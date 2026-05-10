import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH ---
st.set_page_config(page_title="Spare Part Management", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

# Hàm chuyển đổi giá trị sang String chuẩn (Xử lý cả trường hợp số .0)
def format_to_string(val):
    if pd.isna(val) or val == "":
        return ""
    # Chuyển về string và loại bỏ đuôi .0 nếu có (phòng trường hợp Sheets vẫn gửi về dạng float)
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s

# --- A_1: SIDEBAR ---
with st.sidebar:
    st.header("📋 MENU")
    menu_option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- TẢI DỮ LIỆU ---
@st.cache_data(ttl=600)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    return {
        "mst": conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST"),
        "contact": conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact"),
        "staff": conn.read(spreadsheet=SHEET_URL, worksheet="Staff"),
        "machines": conn.read(spreadsheet=SHEET_URL, worksheet="List_of_ machines")
    }

data = load_data()

if menu_option == "Spare Part Quotation":
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("➕ New Spare Part Offer", use_container_width=True):
            st.session_state.page = "new"
    with col_nav2:
        if st.button("📋 Order Management", use_container_width=True):
            st.session_state.page = "manage"

    if "page" not in st.session_state: st.session_state.page = "new"

    if st.session_state.page == "new":
        st.subheader("🆕 Create New Spare Part Offer")

        df_mst = data["mst"]
        
        # 1. Customer Name (Tab: Customer_MST / Col: C)
        # Lấy theo tên cột để tránh lỗi lệch index
        cust_name_col = "Customer name"
        cust_list = df_mst[cust_name_col].dropna().unique()
        selected_cust = st.selectbox("👤 Customer Name:", options=cust_list)

        # Lấy dòng dữ liệu khách hàng được chọn
        cust_row = df_mst[df_mst[cust_name_col] == selected_cust].iloc[0]

        # 2. Customer No (Col: B): Convert to string and show
        # Cột B thường có tiêu đề là "Customer\nno" hoặc "Customer no"
        cust_no_col = df_mst.columns[1] 
        cust_no_val = format_to_string(cust_row[cust_no_col])
        st.text_input("🆔 Customer No:", value=cust_no_val, disabled=True)

        # 3. Tax Code (Col: F): Convert to string and show (ĐÃ FIX THEO YÊU CẦU)
        tax_code_col = df_mst.columns[5] # Cột F
        tax_code_val = format_to_string(cust_row[tax_code_col])
        st.text_input("📑 Tax Code:", value=tax_code_val, disabled=True)

        # 4. Address (Col: E)
        addr_col = df_mst.columns[4] # Cột E
        address_val = str(cust_row[addr_col])
        st.text_area("📍 Address:", value=address_val, disabled=True, height=70)

        col_l, col_r = st.columns(2)

        with col_l:
            # 5. Contact Person (Tab: Customer_Contact / Col: H)
            # Dùng Customer No để tìm kiếm
            df_con = data["contact"].copy()
            # Ép kiểu cột so sánh về string
            con_id_col = df_con.columns[1] # Cột B trong tab Contact
            df_con[con_id_col] = df_con[con_id_col].apply(format_to_string)
            
            # Lấy danh sách contact tại cột H (Index 7)
            contact_person_col = df_con.columns[7]
            list_con = df_con[df_con[con_id_col] == cust_no_val][contact_person_col].dropna().unique()
            st.selectbox("📞 Contact Person:", options=list_con if len(list_con) > 0 else ["N/A"])

            # 6. Officer (Tab: Staff / Col: B)
            df_staff = data["staff"]
            staff_list = df_staff.iloc[:, 1].dropna().unique()
            st.selectbox("👨‍💼 Officer:", options=staff_list)

        with col_r:
            # 7. Machine Number (Tab: List_of_ machines / Col: O)
            df_mac = data["machines"].copy()
            # Ép kiểu cột so sánh về string (Tab Machine / Cột B)
            mac_id_col = df_mac.columns[1]
            df_mac[mac_id_col] = df_mac[mac_id_col].apply(format_to_string)
            
            # Lấy danh sách máy tại cột O (Index 14)
            # Dùng .iloc để lấy cột 14 phòng trường hợp tên cột có ký tự lạ
            mac_list_col = df_mac.columns[14]
            list_mac = df_mac[df_mac[mac_id_col] == cust_no_val][mac_list_col].dropna().unique()
            st.selectbox("🤖 Machine Number:", options=list_mac if len(list_mac) > 0 else ["N/A"])

            # 8. Offer Date
            st.date_input("📅 Offer Date:", value=datetime.now())

        # 9. Offer No (YYYY-MM-0001)
        off_no_default = f"{datetime.now().year}-{datetime.now().month:02d}-0001"
        st.text_input("🆔 Offer No:", value=off_no_default)

    elif st.session_state.page == "manage":
        st.info("Trang Order Management")

else:
    st.title("Service Quotation")
