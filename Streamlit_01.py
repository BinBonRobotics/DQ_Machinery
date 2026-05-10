import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- A_General layout ---
st.set_page_config(page_title="Spare Part Quotation System", layout="wide")

# Hàm load dữ liệu an toàn
@st.cache_data(ttl=60)
def load_all_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Đọc tất cả các tab cần thiết
    df_mst = conn.read(worksheet="Customer_MST")
    df_contact = conn.read(worksheet="Customer_Contact")
    df_staff = conn.read(worksheet="Staff")
    df_machines = conn.read(worksheet="List_of_ machines")
    df_sp = conn.read(worksheet="SP_List")
    return df_mst, df_contact, df_staff, df_machines, df_sp

try:
    df_mst, df_contact, df_staff, df_machines, df_sp = load_all_data()
except Exception as e:
    st.error(f"Lỗi kết nối Google Sheets: {e}")
    st.stop()

# Khởi tạo session state
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'sub_page' not in st.session_state:
    st.session_state.sub_page = "New"

# --- A_1: Side menu ---
with st.sidebar:
    st.header("MENU")
    menu_opt = st.radio("Options:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- A_2: Spare Part Quotation ---
if menu_opt == "Spare Part Quotation":
    col_nav1, col_nav2, _ = st.columns([2, 2, 5])
    if col_nav1.button("New Spare Part Offer", use_container_width=True):
        st.session_state.sub_page = "New"
    if col_nav2.button("Order Management", use_container_width=True):
        st.session_state.sub_page = "Manage"

    st.divider()

    if st.session_state.sub_page == "New":
        # --- B_1: Offer Header (Top to Bottom) ---
        
        # 1. Customer Name (Col C -> index 2)
        cust_names = df_mst.iloc[:, 2].dropna().unique().tolist()
        selected_name = st.selectbox("Customer Name:", options=cust_names)
        
        # Lấy dòng thông tin khách hàng
        cust_row = df_mst[df_mst.iloc[:, 2] == selected_name].iloc[0]
        
        # 2. Customer No (Col B -> index 1)
        c_no_val = str(cust_row.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=c_no_val, disabled=True)
        
        # 3. Tax Code (Col F -> index 5)
        tax_val = str(cust_row.iloc[5])
        st.text_input("Tax Code:", value=tax_val, disabled=True)
        
        # 4. Address (Col E -> index 4)
        addr_val = str(cust_row.iloc[4])
        st.text_area("Address:", value=addr_val, height=80, disabled=True)
        
        # 5. Contact Person (Tab Customer_Contact / Col H -> index 7)
        # Lọc theo Customer No (Tab Contact / Col B -> index 1)
        f_contacts = df_contact[df_contact.iloc[:, 1].astype(str).str.contains(c_no_val)]
        contact_list = f_contacts.iloc[:, 7].dropna().tolist() if not f_contacts.empty else ["N/A"]
        st.selectbox("Contact Person:", options=contact_list)
        
        # 6. Officer (Tab Staff / Col B -> index 1)
        staff_list = df_staff.iloc[:, 1].dropna().tolist()
        st.selectbox("Officer:", options=staff_list)
        
        # 7. Machine Number (Tab List_of_machines / Col O -> index 14)
        # Lọc theo Customer No (Tab Machines / Col B -> index 1)
        f_machines = df_machines[df_machines.iloc[:, 1].astype(str).str.contains(c_no_val)]
        machine_list = f_machines.iloc[:, 14].dropna().tolist() if not f_machines.empty else ["N/A"]
        st.selectbox("Machine Number:", options=machine_list)
        
        # 8. Offer Date
        off_date = st.date_input("Offer Date:", value=datetime.now())
        
        # 9. Offer No
        off_no = st.text_input("Offer No:", value=f"{off_date.year}-{off_date.month:02d}-0001")

        # --- Đường kẻ ngăn cách ---
        st.markdown("<hr style='border:1px solid #ccc'>", unsafe_allow_html=True)

        # --- B_2: Offer Descriptions ---
        search_input = st.text_input("Search Part Number (vd: 2024956492;2031956280):")
        
        col_c1, col_c2, _ = st.columns([1.5, 1.5, 4])
        if col_c1.button("Add to Cart", type="primary", use_container_width=True):
            if search_input:
                codes = [c.strip() for c in search_input.split(';')]
                for code in codes:
                    # Tìm trong SP_List / Col B -> index 1
                    match = df_sp[df_sp.iloc[:, 1].astype(str) == code]
                    if not match.empty:
                        item = match.iloc[0]
                        # Thêm vào giỏ hàng
                        st.session_state.cart.append({
                            "Part Number": str(item.iloc[1]), # Col B
                            "Part Name": item.iloc[4],       # Col E
                            "Qty": 1,
                            "Unit": item.iloc[7],            # Col H
                            "VAT": item.iloc[12],           # Col M
                            "Unit Price": float(item.iloc[18]) if not pd.isna(item.iloc[18]) else 0.0, # Col S
                            "% Discount": 0.0
                        })
                    else:
                        st.warning(f"Part Number {code} is not available")
                st.rerun()

        if col_c2.button("Delete Cart", use_container_width=True):
            st.session_state.cart = []
            st.rerun()

        # Hiển thị bảng Cart
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            
            # Tính Amount = (Unit Price * % Discount) / 100
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
                    "Qty": st.column_config.NumberColumn(min_value=1),
                    "% Discount": st.column_config.NumberColumn(min_value=0, max_value=100),
                    "Amount": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Delete": st.column_config.CheckboxColumn("Xóa")
                },
                hide_index=True,
                use_container_width=True,
                key="cart_editor"
            )

            # Cập nhật session state khi UI thay đổi (Qty, Discount, Delete)
            if not edited_df.equals(df_cart):
                new_cart = edited_df[edited_df["Delete"] == False].drop(columns=["No", "Amount", "Delete"]).to_dict('records')
                st.session_state.cart = new_cart
                st.rerun()

    elif st.session_state.sub_page == "Manage":
        st.info("Trang Order Management")
