import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(layout="wide")

# --- LOAD DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)
df_mst = conn.read(worksheet="Customer_MST").dropna(how='all')

# --- A_1: SIDE MENU ---
with st.sidebar:
    st.header("MENU")
    menu = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh"):
        st.cache_data.clear()
        st.rerun()

# --- A_2: MAIN PAGE ---
if menu == "Spare Part Quotation":
    col1, col2, _ = st.columns([2, 2, 5])
    btn_new = col1.button("New Spare Part Offer", use_container_width=True)
    btn_manage = col2.button("Order Management", use_container_width=True)

    # Khởi tạo trạng thái hiển thị
    if "show_new" not in st.session_state: st.session_state.show_new = False
    if btn_new: st.session_state.show_new = True
    if btn_manage: st.session_state.show_new = False

    # --- B_FUNCTIONS: NEW SPARE PART OFFER ---
    if st.session_state.show_new:
        st.markdown("---")
        
        # 1. Customer Name (Col C -> index 2)
        cust_list = df_mst.iloc[:, 2].dropna().unique().tolist()
        customer_name = st.selectbox("Customer Name:", options=cust_list)
        
        # Lấy row dữ liệu
        cust_row = df_mst[df_mst.iloc[:, 2] == customer_name].iloc[0]
        
        # 2. Customer No (Col B -> index 1)
        cust_no = str(cust_row.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=cust_no, disabled=True)
        
        # 3. Tax Code (Col F -> index 5)
        tax_code = str(cust_row.iloc[5]) if not pd.isna(cust_row.iloc[5]) else ""
        st.text_input("Tax Code:", value=tax_code, disabled=True)
