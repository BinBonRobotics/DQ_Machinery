import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Spare Part Quotation System", layout="wide")

# --- HÀM LOAD DỮ LIỆU AN TOÀN ---
@st.cache_data(ttl=60)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Load các tab chính
    df_mst = conn.read(worksheet="Customer_MST")
    df_contact = conn.read(worksheet="Customer_Contact")
    df_staff = conn.read(worksheet="Staff")
    df_machines = conn.read(worksheet="List_of_ machines")
    df_sp = conn.read(worksheet="SP_List")
    
    # Xử lý tiêu đề cột: Loại bỏ khoảng trắng và ký tự xuống dòng
    for df in [df_mst, df_contact, df_staff, df_machines, df_sp]:
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        
    return df_mst, df_contact, df_staff, df_machines, df_sp

# Thử tải dữ liệu
try:
    df_mst, df_contact, df_staff, df_machines, df_sp = load_data()
except Exception as e:
    st.error(f"Lỗi kết nối Google Sheets: {e}")
    st.stop()

# --- KHỞI TẠO BIẾN TẠM (SESSION STATE) ---
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'sub_page' not in st.session_state:
    st.session_state.sub_page = "New Offer"

# --- A_1: SIDE MENU ---
with st.sidebar:
    st.title("Main Menu")
    main_option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- A_2: GIAO DIỆN CHÍNH ---
if main_option == "Spare Part Quotation":
    col_nav1, col_nav2, _ = st.columns([2, 2, 5])
    if col_nav1.button("New Spare Part Offer", use_container_width=True):
        st.session_state.sub_page = "New Offer"
    if col_nav2.button("Order Management", use_container_width=True):
        st.session_state.sub_page = "Management"

    st.markdown("---")

    if st.session_state.sub_page == "New Offer":
        # --- B_1: OFFER HEADER (Layout hàng dọc) ---
        
        # 1. Customer Name (Tab: Customer_MST, Col C: "Customer name")
        # Sử dụng iloc để lấy cột thứ 3 (index 2) đề phòng tên cột sai biệt
        cust_list = df_mst.iloc[:, 2].dropna().unique().tolist()
        cust_name = st.selectbox("Customer Name:", options=cust_list)
        
        # Lấy row khách hàng đã chọn
        cust_row = df_mst[df_mst.iloc[:, 2] == cust_name].iloc[0]
        
        # 2. Customer No (Tab: Customer_MST, Col B: index 1)
        c_no = str(cust_row.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=c_no, disabled=True)
        
        # 3. Tax Code (Tab: Customer_MST, Col F: index 5)
        t_code = str(cust_row.iloc[5])
        st.text_input("Tax Code:", value=t_code, disabled=True)
        
        # 4. Address (Tab: Customer_MST, Col E: index 4)
        addr = str(cust_row.iloc[4])
        st.text_area("Address:", value=addr, height=80, disabled=True)
        
        # 5. Contact Person (Tab: Customer_Contact, Col H: index 7, lọc theo Cust No)
        # Lọc danh sách liên hệ theo Customer No (cột thứ 2 - index 1 trong tab Contact)
        f_contacts = df_contact[df_contact.iloc[:, 1].astype(str).str.contains(c_no)]
        contact_list = f_contacts.iloc[:, 7].dropna().tolist() if not f_contacts.empty else ["N/A"]
        st.selectbox("Contact Person:", options=contact_list)
        
        # 6. Officer (Tab: Staff, Col B: index 1)
        staff_list = df_staff.iloc[:, 1].dropna().tolist()
        st.selectbox("Officer:", options=staff_list)
        
        # 7. Machine Number (Tab: List_of_ machines, Col O: index 14)
        # Lọc máy theo Customer No (cột thứ 2 - index 1 trong tab Machines)
        f_machines = df_machines[df_machines.iloc[:, 1].astype(str).str.contains(c_no)]
        machine_list = f_machines.iloc[:, 14].dropna().tolist() if not f_machines.empty else ["N/A"]
        st.selectbox("Machine Number:", options=machine_list)
        
        # 8. Offer Date
        off_date = st.date_input("Offer Date:", value=datetime.now())
        
        # 9. Offer No (Input tay)
        default_no = f"{off_date.year}-{off_date.month:02d}-0001"
        st.text_input("Offer No:", value=default_no)

        st.markdown("---") # Đường kẻ tách biệt

        # --- B_2: OFFER DESCRIPTIONS ---
        st.subheader("Search Part Number")
        search_val = st.text_input("Input Part Number (tách nhau bằng dấu ';'):", placeholder="2024956492;2031956280")
        
        col_act1, col_act2, _ = st.columns([1.5, 1.5, 4])
        if col_act1.button("Add to Cart", type="primary"):
            if search_val:
                input_codes = [x.strip() for x in search_val.split(";")]
                for code in input_codes:
                    # Tìm trong SP_List, cột B (index 1)
                    match = df_sp[df_sp.iloc[:, 1].astype(str) == code]
                    if not match.empty:
                        res = match.iloc[0]
                        # Thêm vào list giỏ hàng
                        st.session_state.cart.append({
                            "Part Number": str(res.iloc[1]),
                            "Part Name": res.iloc[4], # Col E
                            "Qty": 1,
                            "Unit": res.iloc[7], # Col H
                            "VAT": res.iloc[12], # Col M
                            "Unit Price": float(res.iloc[18]) if not pd.isna(res.iloc[18]) else 0.0, # Col S
                            "% Discount": 0.0
                        })
                    else:
                        st.error(f"Part Number {code} is not available")
                st.rerun()

        if col_act2.button("Delete Cart"):
            st.session_state.cart = []
            st.rerun()

        # HIỂN THỊ BẢNG GIỎ HÀNG
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            
            # Tính toán Column 9: Amount = (UnitPrice * Discount) / 100
            df_cart["Amount"] = (df_cart["Unit Price"] * df_cart["% Discount"]) / 100
            
            # Thêm cột No và cột Delete
            df_cart.insert(0, "No", range(1, len(df_cart) + 1))
            df_cart["Delete"] = False

            edited_df = st.data_editor(
                df_cart,
                column_config={
                    "No": st.column_config.NumberColumn(disabled=True),
                    "Part Number": st.column_config.TextColumn(disabled=True),
                    "Part Name": st.column_config.TextColumn(disabled=True),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(format="%.2f", disabled=True),
                    "Unit Price": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Qty": st.column_config.NumberColumn(min_value=1, step=1),
                    "% Discount": st.column_config.NumberColumn(min_value=0, max_value=100, step=1),
                    "Amount": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Delete": st.column_config.CheckboxColumn("Xóa dòng")
                },
                hide_index=True,
                use_container_width=True,
                key="editor_new"
            )

            # Đồng bộ dữ liệu sau khi sửa
            if not edited_df.equals(df_cart):
                # Lọc bỏ dòng bị tick xóa
                updated_cart = edited_df[edited_df["Delete"] == False].drop(columns=["No", "Amount", "Delete"]).to_dict('records')
                st.session_state.cart = updated_cart
                st.rerun()

    elif st.session_state.sub_page == "Management":
        st.info("Chức năng Quản lý đơn hàng đang được cập nhật.")
