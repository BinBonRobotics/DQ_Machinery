import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(layout="wide", page_title="Quotation System")

# URL Google Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8/edit#gid=903775380"

# --- 2. HÀM LOAD DỮ LIỆU ---
@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST").dropna(how='all')
        contact = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact").dropna(how='all')
        staff = conn.read(spreadsheet=SHEET_URL, worksheet="Staff").dropna(how='all')
        machines = conn.read(spreadsheet=SHEET_URL, worksheet="List_of_ machines").dropna(how='all')
        sp = conn.read(spreadsheet=SHEET_URL, worksheet="SP_List").dropna(how='all')
        return mst, contact, staff, machines, sp
    except Exception as e:
        st.error(f"Lỗi kết nối Sheet: {e}")
        return None, None, None, None, None

df_mst, df_contact, df_staff, df_machines, df_sp = load_data()

if 'cart' not in st.session_state: st.session_state.cart = []
if 'page_view' not in st.session_state: st.session_state.page_view = "New"

# --- 3. SIDE MENU ---
with st.sidebar:
    st.header("MENU")
    option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 4. CHỨC NĂNG CHÍNH ---
if df_mst is not None and option == "Spare Part Quotation":
    col_b1, col_b2, _ = st.columns([2, 2, 5])
    if col_b1.button("New Spare Part Offer", use_container_width=True): st.session_state.page_view = "New"
    if col_b2.button("Order Management", use_container_width=True): st.session_state.page_view = "Manage"

    if st.session_state.page_view == "New":
        st.markdown("### New Spare Part Offer")
        
        # --- B_1: OFFER HEADER ---
        names = df_mst.iloc[:, 2].dropna().unique().tolist()
        selected_name = st.selectbox("Customer Name:", options=names)
        cust_row = df_mst[df_mst.iloc[:, 2] == selected_name].iloc[0]
        
        c_no = str(cust_row.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=c_no, disabled=True)
        
        t_val = cust_row.iloc[5]
        t_code = str(t_val).split('.')[0].strip() if not pd.isna(t_val) else ""
        if len(t_code) == 9: t_code = "0" + t_code
        st.text_input("Tax Code:", value=t_code, disabled=True)
        
        st.text_area("Address:", value=str(cust_row.iloc[4]) if not pd.isna(cust_row.iloc[4]) else "", height=70, disabled=True)
        
        # --- B_2: OFFER DESCRIPTIONS ---
        st.markdown("---")
        st.subheader("Offer Descriptions")
        search_input = st.text_input("Search Part Number:", placeholder="Nhập mã, ví dụ: 2024956492;3202181000")
        
        col_act1, col_act2, _ = st.columns([1.5, 1.5, 6])
        
        if col_act1.button("Add to Cart", type="primary", use_container_width=True):
            if search_input:
                codes = [c.strip() for c in search_input.split(';')]
                not_found = []
                for code in codes:
                    match = df_sp[df_sp.iloc[:, 1].astype(str).str.strip() == code]
                    if not match.empty:
                        item = match.iloc[0]
                        raw_vat = item.iloc[12]
                        # Xử lý VAT trống hoặc 0.08
                        if pd.isna(raw_vat) or raw_vat == "None":
                            display_vat = 0
                        else:
                            try:
                                display_vat = int(float(raw_vat) * 100) if float(raw_vat) < 1 else int(float(raw_vat))
                            except: display_vat = 0
                        
                        st.session_state.cart.append({
                            "Part Number": str(item.iloc[1]),
                            "Part Nname": str(item.iloc[4]),
                            "Qty": 1,
                            "Unit": str(item.iloc[7]),
                            "VAT": display_vat,
                            "Unit Price": float(item.iloc[18]) if not pd.isna(item.iloc[18]) else 0.0,
                            "% Distcount": 0
                        })
                    else:
                        not_found.append(code)
                
                if not_found:
                    st.error(f"Không tìm thấy Part: {', '.join(not_found)}")
                st.rerun()

        # Nút Xóa giỏ hàng (Đã khôi phục)
        if col_act2.button("Delete Cart", use_container_width=True):
            st.session_state.cart = []
            st.rerun()

        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            
            # CÔNG THỨC: Amount = (Qty * Price) * (1 - Discount/100)
            df_cart["Amount"] = df_cart["Qty"] * df_cart["Unit Price"] * (1 - df_cart["% Distcount"]/100)
            
            df_cart.insert(0, "No", range(1, len(df_cart) + 1))
            df_cart["Xóa"] = False

            # Cấu hình bảng: Chỉ cho edit Qty, % Distcount và Xóa
            edited_df = st.data_editor(
                df_cart,
                column_config={
                    "No": st.column_config.NumberColumn(disabled=True),
                    "Part Number": st.column_config.TextColumn(disabled=True),
                    "Part Nname": st.column_config.TextColumn(disabled=True),
                    "Qty": st.column_config.NumberColumn(min_value=1, step=1, required=True),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(format="%d", disabled=True), 
                    "Unit Price": st.column_config.NumberColumn(format="%d", disabled=True), 
                    "% Distcount": st.column_config.NumberColumn(min_value=0, max_value=100, format="%d%%"),
                    "Amount": st.column_config.NumberColumn(format="%d", disabled=True), 
                    "Xóa": st.column_config.CheckboxColumn(label="Xóa")
                },
                hide_index=True,
                use_container_width=True,
                key="editor"
            )

            # Xử lý cập nhật giỏ hàng khi người dùng thao tác trên bảng
            if not edited_df.equals(df_cart):
                new_cart = edited_df[edited_df["Xóa"] == False].drop(columns=["No", "Amount", "Xóa"]).to_dict('records')
                st.session_state.cart = new_cart
                st.rerun()

    elif st.session_state.page_view == "Manage":
        st.info("Trang Order Management")
