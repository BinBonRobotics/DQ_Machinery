import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Spare Part System")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8/edit#gid=903775380"

# --- LOAD DATA ---
@st.cache_data(ttl=60)
def load_all_tabs():
    conn = st.connection("gsheets", type=GSheetsConnection)
    mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST").dropna(how='all')
    contact = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact").dropna(how='all')
    staff = conn.read(spreadsheet=SHEET_URL, worksheet="Staff").dropna(how='all')
    machines = conn.read(spreadsheet=SHEET_URL, worksheet="List_of_ machines").dropna(how='all')
    sp = conn.read(spreadsheet=SHEET_URL, worksheet="SP_List").dropna(how='all')
    return mst, contact, staff, machines, sp

df_mst, df_contact, df_staff, df_machines, df_sp = load_all_tabs()

# Khởi tạo giỏ hàng và trạng thái trang
if 'cart' not in st.session_state: st.session_state.cart = []
if 'view' not in st.session_state: st.session_state.view = "New"

# --- A_1: SIDE MENU ---
with st.sidebar:
    st.header("MENU")
    option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- A_2 & B_FUNCTIONS: SPARE PART QUOTATION ---
if option == "Spare Part Quotation":
    c1, c2, _ = st.columns([2, 2, 5])
    if c1.button("New Spare Part Offer", use_container_width=True): st.session_state.view = "New"
    if c2.button("Order Management", use_container_width=True): st.session_state.view = "Manage"

    if st.session_state.view == "New":
        st.divider()
        # --- B_1: OFFER HEADER (TOP DOWN) ---
        # 1. Customer Name (Col C - index 2)
        names = df_mst.iloc[:, 2].dropna().unique().tolist()
        cust_name = st.selectbox("Customer Name:", options=names)
        cust_row = df_mst[df_mst.iloc[:, 2] == cust_name].iloc[0]
        
        # 2. Customer No (Col B - index 1)
        c_no = str(cust_row.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=c_no, disabled=True)
        
        # 3. Tax Code (Col F - index 5)
        tax = str(cust_row.iloc[5]) if not pd.isna(cust_row.iloc[5]) else ""
        st.text_input("Tax Code:", value=tax, disabled=True)
        
        # 4. Address (Col E - index 4)
        addr = str(cust_row.iloc[4]) if not pd.isna(cust_row.iloc[4]) else ""
        st.text_area("Address:", value=addr, height=70, disabled=True)
        
        # 5. Contact Person (Tab: Contact / Col H - index 7 / Filter by C_No ở Col B - index 1)
        f_contacts = df_contact[df_contact.iloc[:, 1].astype(str).str.contains(c_no)]
        contact_list = f_contacts.iloc[:, 7].dropna().tolist() if not f_contacts.empty else ["N/A"]
        st.selectbox("Contact Person:", options=contact_list)
        
        # 6. Officer (Tab: Staff / Col B - index 1)
        staff_list = df_staff.iloc[:, 1].dropna().tolist()
        st.selectbox("Officer:", options=staff_list)
        
        # 7. Machine Number (Tab: Machines / Col O - index 14 / Filter by C_No ở Col B - index 1)
        f_machines = df_machines[df_machines.iloc[:, 1].astype(str).str.contains(c_no)]
        machine_list = f_machines.iloc[:, 14].dropna().tolist() if not f_machines.empty else ["N/A"]
        st.selectbox("Machine Number:", options=machine_list)
        
        # 8. Offer Date & 9. Offer No
        off_date = st.date_input("Offer Date:", value=datetime.now())
        st.text_input("Offer No:", value=f"{off_date.year}-{off_date.month:02d}-0001")

        # --- SEPARATION LINE ---
        st.markdown("---")
        st.subheader("Offer Descriptions")

        # --- B_2: OFFER DESCRIPTIONS ---
        search_val = st.text_input("Search Part Number:", placeholder="2024956492;2031956280...")
        
        act1, act2, _ = st.columns([1.5, 1.5, 6])
        if act1.button("Add to Cart", type="primary"):
            if search_val:
                codes = [c.strip() for c in search_val.split(';')]
                for code in codes:
                    # Tìm trong SP_List (Col B - index 1)
                    match = df_sp[df_sp.iloc[:, 1].astype(str) == code]
                    if not match.empty:
                        item = match.iloc[0]
                        st.session_state.cart.append({
                            "Part Number": str(item.iloc[1]), # Col B
                            "Part Nname": item.iloc[4],       # Col E
                            "Qty": 1,
                            "Unit": item.iloc[7],            # Col H
                            "VAT": item.iloc[12],            # Col M
                            "Unit Price": float(item.iloc[18]) if not pd.isna(item.iloc[18]) else 0.0, # Col S
                            "% Distcount": 0.0
                        })
                    else: st.error(f"Part Number {code} is not available")
                st.rerun()

        if act2.button("Delete Cart"):
            st.session_state.cart = []
            st.rerun()

        # Hiển thị bảng giỏ hàng
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            # Tính Col 9: Amount = (UnitPrice * %Discount) / 100
            df_cart["Amount"] = (df_cart["Unit Price"] * df_cart["% Distcount"]) / 100
            df_cart.insert(0, "No", range(1, len(df_cart) + 1))
            df_cart["Delete"] = False

            edited_df = st.data_editor(
                df_cart,
                column_config={
                    "No": st.column_config.NumberColumn(disabled=True),
                    "Part Number": st.column_config.TextColumn(disabled=True),
                    "Part Nname": st.column_config.TextColumn(disabled=True),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(format="%.2f", disabled=True),
                    "Unit Price": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Qty": st.column_config.NumberColumn(min_value=1),
                    "% Distcount": st.column_config.NumberColumn(min_value=0, max_value=100),
                    "Amount": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Delete": st.column_config.CheckboxColumn()
                },
                hide_index=True, use_container_width=True, key="cart_table"
            )

            # Cập nhật khi user sửa Qty/Discount hoặc chọn Delete
            if not edited_df.equals(df_cart):
                new_cart = edited_df[edited_df["Delete"] == False].drop(columns=["No", "Amount", "Delete"]).to_dict('records')
                st.session_state.cart = new_cart
                st.rerun()

    elif st.session_state.view == "Manage":
        st.info("Management View")
