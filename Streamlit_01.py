import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime

# --- CONFIG & STYLING ---
st.set_page_config(page_title="D&Q Machinery System", layout="wide")

# --- HÀM TRỢ GIÚP ---
def clean_code(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).split('.')[0].strip()
    return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

# --- LOAD DATA ---
@st.cache_data(ttl=60)
def load_all_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
        
        df_sp = conn.read(spreadsheet=url, worksheet="SP_List")
        df_mst = conn.read(spreadsheet=url, worksheet="Customer_MST")
        df_con = conn.read(spreadsheet=url, worksheet="Customer_Contact")
        df_mac = conn.read(spreadsheet=url, worksheet="List_of_ machines")
        df_staff = conn.read(spreadsheet=url, worksheet="Staff")
        
        return df_sp, df_mst, df_con, df_mac, df_staff
    except Exception as e:
        st.error(f"❌ Lỗi kết nối dữ liệu: {e}")
        return [None] * 5

def main():
    df_sp, df_mst, df_con, df_mac, df_staff = load_all_data()
    if df_mst is None: return

    # --- A_1: SIDE MENU ---
    with st.sidebar:
        st.title("Menu Chính")
        menu_selection = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Khởi tạo Session State cho giỏ hàng
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'sub_page' not in st.session_state: st.session_state.sub_page = "New Offer"

    # --- A_2: SPARE PART QUOTATION PAGE ---
    if menu_selection == "Spare Part Quotation":
        col_btn1, col_btn2, _ = st.columns([1.5, 1.5, 4])
        if col_btn1.button("➕ New Spare Part Offer", use_container_width=True):
            st.session_state.sub_page = "New Offer"
        if col_btn2.button("🔍 Order Management", use_container_width=True):
            st.session_state.sub_page = "Management"

        st.divider()

        # --- B_FUNCTIONS: NEW SPARE PART OFFER ---
        if st.session_state.sub_page == "New Offer":
            # 1. Header Information
            with st.container():
                r1_c1, r1_c2 = st.columns(2)
                with r1_c1:
                    # Customer Name (Col C - index 2)
                    cust_list = df_mst.iloc[:, 2].dropna().unique().tolist()
                    cust_name = st.selectbox("🎯 Customer Name:", options=cust_list)
                    
                    # Lấy thông tin tương ứng từ Customer_MST
                    cust_row = df_mst[df_mst.iloc[:, 2] == cust_name].iloc[0]
                    
                    # Customer No (Col B - index 1)
                    cust_no = str(cust_row.iloc[1]).split('.')[0]
                    st.text_input("🆔 Customer No:", value=cust_no, disabled=True)
                    
                    # Tax Code (Col F - index 5)
                    tax_code = str(cust_row.iloc[5])
                    st.text_input("🧾 Tax Code:", value=tax_code, disabled=True)

                with r1_c2:
                    # Address (Col E - index 4)
                    address = str(cust_row.iloc[4])
                    st.text_area("📍 Address:", value=address, height=68, disabled=True)
                    
                    # Contact Person (Lọc từ tab Customer_Contact Col H dựa trên Customer No)
                    # Giả định Customer No ở tab Contact nằm ở Col B (index 1)
                    f_conts = df_con[df_con.iloc[:, 1].astype(str).str.contains(cust_no)] if not df_con.empty else pd.DataFrame()
                    contact_list = f_conts.iloc[:, 7].dropna().unique().tolist() if not f_conts.empty else ["N/A"]
                    st.selectbox("👤 Contact Person:", options=contact_list)

                r2_c1, r2_c2, r2_c3 = st.columns(3)
                with r2_c1:
                    # Officer (Staff Col B - index 1)
                    staff_list = df_staff.iloc[:, 1].dropna().tolist()
                    st.selectbox("✍️ Officer:", options=staff_list)
                with r2_c2:
                    # Machine Number (Lọc từ List_of_machines Col O dựa trên Customer No)
                    f_macs = df_mac[df_mac.iloc[:, 1].astype(str).str.contains(cust_no)] if not df_mac.empty else pd.DataFrame()
                    machine_list = f_macs.iloc[:, 14].dropna().unique().tolist() if not f_macs.empty else ["N/A"]
                    st.selectbox("🤖 Machine Number:", options=machine_list)
                with r2_c3:
                    offer_date = st.date_input("📅 Offer Date:", value=datetime.now())
                
                # Offer No
                default_offer_no = f"{offer_date.year}-{offer_date.month:02d}-0001"
                st.text_input("📄 Offer No:", value=default_offer_no)

            st.markdown("---") # Line to separate Header and Description

            # 2. Search & Add to Cart
            st.subheader("🔍 Search Part Number")
            search_input = st.text_input("Nhập Part Number (cách nhau bởi dấu ';'):", placeholder="2024956492;2031956280")
            
            col_act1, col_act2, _ = st.columns([1, 1, 4])
            add_btn = col_act1.button("🛒 Add to Cart", type="primary", use_container_width=True)
            del_cart_btn = col_act2.button("🗑️ Delete Cart", use_container_width=True)

            if del_cart_btn:
                st.session_state.cart = []
                st.rerun()

            if add_btn and search_input:
                codes = [c.strip() for c in search_input.split(';') if c.strip()]
                df_sp['CLEAN_PN'] = df_sp.iloc[:, 1].apply(clean_code) # Col B
                
                for code in codes:
                    match = df_sp[df_sp['CLEAN_PN'] == clean_code(code)]
                    if not match.empty:
                        item = match.iloc[0]
                        # Check trùng trong giỏ
                        if not any(d['Part Number'] == item.iloc[1] for d in st.session_state.cart):
                            st.session_state.cart.append({
                                "Part Number": item.iloc[1],    # Col B
                                "Part Name": item.iloc[4],      # Col E
                                "Qty": 1,                       # Default 1
                                "Unit": item.iloc[7],           # Col H
                                "VAT": item.iloc[12],            # Col M
                                "Unit Price": float(item.iloc[18]) if not pd.isna(item.iloc[18]) else 0.0, # Col S
                                "% Discount": 0.0,
                                "Delete": False
                            })
                    else:
                        st.error(f"⚠️ Part Number {code} is not available")
                st.rerun()

            # 3. Table Description
            if st.session_state.cart:
                df_cart = pd.DataFrame(st.session_state.cart)
                # Tính toán Amount: (Unit Price * Qty) * (1 - Discount/100)
                # Lưu ý: Công thức của bạn là (Col 7 * Col 8)/100 có vẻ là tính số tiền giảm, 
                # thường Amount sẽ là giá sau giảm. Mình sẽ để cột Amount là giá sau giảm:
                df_cart['Amount'] = (df_cart['Unit Price'] * df_cart['Qty']) * (1 - df_cart['% Discount']/100)
                
                # Hiển thị bảng cho phép chỉnh sửa Qty và Discount
                edited_df = st.data_editor(
                    df_cart,
                    column_config={
                        "No": st.column_config.NumberColumn(disabled=True),
                        "Part Number": st.column_config.TextColumn(disabled=True),
                        "Part Name": st.column_config.TextColumn(disabled=True),
                        "Unit": st.column_config.TextColumn(disabled=True),
                        "VAT": st.column_config.NumberColumn(disabled=True),
                        "Unit Price": st.column_config.NumberColumn(format="%,d", disabled=True),
                        "Qty": st.column_config.NumberColumn(min_value=1),
                        "% Discount": st.column_config.NumberColumn(min_value=0, max_value=100),
                        "Amount": st.column_config.NumberColumn(format="%,d", disabled=True),
                        "Delete": st.column_config.CheckboxColumn("Xoá")
                    },
                    use_container_width=True,
                    hide_index=True,
                    key="editor"
                )

                # Xử lý cập nhật số lượng/giảm giá hoặc xoá dòng
                if not edited_df.equals(df_cart):
                    new_cart = []
                    for i, row in edited_df.iterrows():
                        if not row['Delete']:
                            # Cập nhật giá trị mới từ editor
                            row_dict = row.to_dict()
                            del row_dict['Delete']
                            del row_dict['Amount'] # Để tính lại ở vòng render sau
                            new_cart.append(row_dict)
                    st.session_state.cart = new_cart
                    st.rerun()

        elif st.session_state.sub_page == "Management":
            st.info("Trang quản lý đơn hàng đang được cập nhật...")

if __name__ == "__main__":
    main()
