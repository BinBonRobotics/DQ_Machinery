import streamlit as st
import pandas as pd
from datetime import datetime

# Cấu hình trang
st.set_page_config(layout="wide", page_title="Quotation System")

# --- ĐỌC DỮ LIỆU TỪ FILE ---
# Giả định các file bạn upload đã được load vào DataFrame
@st.cache_data
def load_data():
    cust_mst = pd.read_csv("Test_Streamlit (5).xlsx - Customer_MST.csv")
    cust_contact = pd.read_csv("Test_Streamlit (5).xlsx - Customer_Contact.csv")
    staff = pd.read_csv("Test_Streamlit (5).xlsx - Staff.csv")
    machines = pd.read_csv("Test_Streamlit (5).xlsx - List_of_ machines.csv")
    sp_list = pd.read_csv("Test_Streamlit (5).xlsx - SP_List.csv")
    return cust_mst, cust_contact, staff, machines, sp_list

cust_mst_df, cust_contact_df, staff_df, machines_df, sp_list_df = load_data()

# --- A_1: SIDE MENU ---
with st.sidebar:
    st.title("Menu")
    option = st.radio("Select Option", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh"):
        st.rerun()

# --- A_2: SPARE PART QUOTATION ---
if option == "Spare Part Quotation":
    col_r1, col_r2 = st.columns([1, 1])
    with col_r2:
        col_btn1, col_btn2 = st.columns(2)
        new_offer_btn = col_btn1.button("New Spare Part Offer")
        order_mgmt_btn = col_btn2.button("Order Management")

    # --- B_FUNCTIONS: NEW SPARE PART OFFER ---
    if "show_form" not in st.session_state:
        st.session_state.show_form = False

    if new_offer_btn:
        st.session_state.show_form = True

    if st.session_state.show_form:
        st.header("New Spare Part Offer")
        
        # --- Offer Header ---
        col1, col2 = st.columns(2)
        
        with col1:
            # Customer Name (Drop menu) - Ref: Customer_MST Col C
            customer_name = st.selectbox("Customer Name", cust_mst_df.iloc[:, 2].unique())
            
            # Lấy thông tin khách hàng dựa trên Name
            cust_info = cust_mst_df[cust_mst_df.iloc[:, 2] == customer_name].iloc[0]
            cust_no = str(cust_info.iloc[1]) # Col B
            tax_code = str(cust_info.iloc[5]) # Col F
            address = cust_info.iloc[4] # Col E
            
            st.text(f"Customer No: {cust_no}")
            st.text(f"Tax Code: {tax_code}")
            st.text_area("Address", value=address, height=70, disabled=True)

        with col2:
            # Contact Person - Ref: Customer_Contact Col H dựa trên Customer No
            contacts = cust_contact_df[cust_contact_df.iloc[:, 1].astype(str) == cust_no].iloc[:, 7].tolist()
            contact_person = st.selectbox("Contact Person", contacts if contacts else ["N/A"])
            
            # Officer - Ref: Staff Col B
            officer = st.selectbox("Officer", staff_df.iloc[:, 1].unique())
            
            # Machine Number - Ref: List_of_machines Col O dựa trên Customer No
            m_list = machines_df[machines_df.iloc[:, 1].astype(str) == cust_no].iloc[:, 14].tolist()
            machine_no = st.selectbox("Machine Number", m_list if m_list else ["N/A"])
            
            # Date & Offer No
            offer_date = st.date_input("Offer Date", datetime.now())
            offer_no_input = st.text_input("Offer No", placeholder="e.g. 2026-05-0001")

        st.markdown("---") # Đường kẻ phân cách (A line to separate)
        
        # --- Offer Descriptions (Cart System) ---
        st.subheader("Offer Descriptions")
        
        if 'cart' not in st.session_state:
            st.session_state.cart = pd.DataFrame(columns=[
                "No", "Part Number", "Part Name", "Qty", "Unit", "VAT", "Unit Price", "% Discount", "Amount"
            ])

        search_input = st.text_input("Search Part Number (Separate by ';')")
        
        col_c1, col_c2 = st.columns([1, 5])
        with col_c1:
            add_btn = st.button("Add to Cart")
        with col_c2:
            if st.button("Delete Cart"):
                st.session_state.cart = st.session_state.cart.iloc[0:0]
                st.rerun()

        if add_btn and search_input:
            part_numbers = [p.strip() for p in search_input.split(";")]
            for p_num in part_numbers:
                # Tìm trong SP_List Col B
                match = sp_list_df[sp_list_df.iloc[:, 1].astype(str) == p_num]
                
                if not match.empty:
                    row = match.iloc[0]
                    new_item = {
                        "No": len(st.session_state.cart) + 1,
                        "Part Number": str(row.iloc[1]), # Col B
                        "Part Name": row.iloc[4],        # Col E
                        "Qty": 1,                        # Default
                        "Unit": row.iloc[7],             # Col H
                        "VAT": row.iloc[12],             # Col M
                        "Unit Price": row.iloc[18],      # Col S (Giá bán)
                        "% Discount": 0,
                        "Amount": 0.0
                    }
                    # Tính Amount sơ bộ
                    new_item["Amount"] = (new_item["Unit Price"] * (100 - new_item["% Discount"])) / 100
                    st.session_state.cart = pd.concat([st.session_state.cart, pd.DataFrame([new_item])], ignore_index=True)
                else:
                    st.error(f"Part Number {p_num} is not available")

        # Hiển thị bảng Cart và cho phép chỉnh sửa
        if not st.session_state.cart.empty:
            edited_cart = st.data_editor(
                st.session_state.cart,
                column_config={
                    "Delete": st.column_config.CheckboxColumn("Delete row?", default=False),
                    "Amount": st.column_config.NumberColumn("Amount", disabled=True)
                },
                num_rows="dynamic",
                key="cart_editor"
            )
            
            # Logic tính toán lại Amount khi UI thay đổi Qty hoặc Discount
            edited_cart["Amount"] = (edited_cart["Unit Price"] * edited_cart["Qty"] * (100 - edited_cart["% Discount"])) / 100
            st.session_state.cart = edited_cart
            
            total_val = edited_cart["Amount"].sum()
            st.write(f"**Total Amount: {total_val:,.0f} VND**")
