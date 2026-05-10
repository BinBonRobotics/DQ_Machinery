import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="D&Q Spare Part System", layout="wide")

# --- HÀM LOAD DỮ LIỆU ---
@st.cache_data(ttl=600)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc tất cả các tab cần thiết
    df_mst = conn.read(worksheet="Customer_MST")
    df_contact = conn.read(worksheet="Customer_Contact")
    df_staff = conn.read(worksheet="Staff")
    df_machines = conn.read(worksheet="List_of_ machines")
    df_sp = conn.read(worksheet="SP_List")
    
    return df_mst, df_contact, df_staff, df_machines, df_sp

# Load data ban đầu
try:
    df_mst, df_contact, df_staff, df_machines, df_sp = load_data()
except Exception as e:
    st.error(f"Lỗi kết nối Google Sheets: {e}")
    st.stop()

# --- KHỞI TẠO SESSION STATE ---
if 'cart' not in st.session_state:
    st.session_state.cart = pd.DataFrame(columns=[
        'Part Number', 'Part Name', 'Qty', 'Unit', 'VAT', 'Unit Price', '% Discount', 'Amount'
    ])
if 'current_page' not in st.session_state:
    st.session_state.current_page = "New Offer"

# --- A_1: SIDE MENU ---
with st.sidebar:
    st.title("Main Menu")
    option = st.radio("Select Menu:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh"):
        st.cache_data.clear()
        st.rerun()

# --- A_2 & B: CHỨC NĂNG CHÍNH ---
if option == "Spare Part Quotation":
    # 2 Button điều hướng
    col_nav1, col_nav2 = st.columns([1, 4])
    if col_nav1.button("New Spare Part Offer"):
        st.session_state.current_page = "New Offer"
    if col_nav2.button("Order Management"):
        st.session_state.current_page = "Management"

    if st.session_state.current_page == "New Offer":
        # --- B_1: NEW SPARE PART OFFER (HEADER) ---
        
        # 1. Customer Name (Col C - Index 2)
        cust_names = df_mst.iloc[:, 2].dropna().unique().tolist()
        selected_cust = st.selectbox("Customer Name:", options=cust_names)
        
        # Lấy row dữ liệu khách hàng được chọn
        cust_info = df_mst[df_mst.iloc[:, 2] == selected_cust].iloc[0]
        
        # 2. Customer No (Col B - Index 1) - Show as string
        cust_no = str(cust_info.iloc[1]).split('.')[0]
        st.text(f"Customer No: {cust_no}")
        
        # 3. Tax Code (Col F - Index 5) - Show as string
        tax_code = str(cust_info.iloc[5])
        st.text(f"Tax Code: {tax_code}")
        
        # 4. Address (Col E - Index 4)
        address = str(cust_info.iloc[4])
        st.text(f"Address: {address}")
        
        # 5. Contact Person (Tab Customer_Contact/Col H - Index 7 lọc theo Cust No ở Col B - Index 1)
        # Ép kiểu string để so khớp chính xác
        contacts_filtered = df_contact[df_contact.iloc[:, 1].astype(str).str.contains(cust_no)]
        contact_options = contacts_filtered.iloc[:, 7].dropna().tolist() if not contacts_filtered.empty else ["No contact found"]
        st.selectbox("Contact Person:", options=contact_options)
        
        # 6. Officer (Tab Staff/Col B - Index 1)
        staff_options = df_staff.iloc[:, 1].dropna().tolist()
        st.selectbox("Officer:", options=staff_options)
        
        # 7. Machine Number (Tab List_of_machines/Col O - Index 14 lọc theo Cust No ở Col B - Index 1)
        machines_filtered = df_machines[df_machines.iloc[:, 1].astype(str).str.contains(cust_no)]
        machine_options = machines_filtered.iloc[:, 14].dropna().tolist() if not machines_filtered.empty else ["No machine found"]
        st.selectbox("Machine Number:", options=machine_options)
        
        # 8. Offer Date
        offer_date = st.date_input("Offer Date:", value=datetime.now())
        
        # 9. Offer No (UI key in)
        default_offer_no = f"{offer_date.year}-{offer_date.month:02d}-0001"
        st.text_input("Offer No:", value=default_offer_no)

        # Đường kẻ phân cách
        st.markdown("---")

        # --- OFFER DESCRIPTIONS ---
        st.subheader("Search Part Number")
        search_input = st.text_input("Input Part Number(s) separated by ';'", placeholder="2024956492;2031956280")
        
        col_btn1, col_btn2, _ = st.columns([1, 1, 4])
        add_to_cart = col_btn1.button("Add to Cart")
        delete_cart = col_btn2.button("Delete Cart")

        if delete_cart:
            st.session_state.cart = pd.DataFrame(columns=st.session_state.cart.columns)
            st.rerun()

        if add_to_cart and search_input:
            input_list = [x.strip() for x in search_input.split(";")]
            
            for pn in input_list:
                # Tìm PN trong SP_List/Col B (Index 1)
                # Đảm bảo PN là string để tìm kiếm
                match = df_sp[df_sp.iloc[:, 1].astype(str).str.contains(pn, na=False)]
                
                if not match.empty:
                    res = match.iloc[0]
                    # Tạo hàng mới
                    new_item = {
                        'Part Number': str(res.iloc[1]), # Col B
                        'Part Name': res.iloc[4],       # Col E
                        'Qty': 1,
                        'Unit': res.iloc[7],            # Col H
                        'VAT': res.iloc[12],            # Col M
                        'Unit Price': float(res.iloc[18]) if pd.notnull(res.iloc[18]) else 0.0, # Col S
                        '% Discount': 0.0,
                        'Amount': 0.0
                    }
                    # Append vào session state
                    st.session_state.cart = pd.concat([st.session_state.cart, pd.DataFrame([new_item])], ignore_index=True)
                else:
                    st.error(f"Part Number {pn} is not available")
            st.rerun()

        # --- HIỂN THỊ GIỎ HÀNG ---
        if not st.session_state.cart.empty:
            # Cho phép sửa Qty và % Discount trực tiếp
            edited_df = st.data_editor(
                st.session_state.cart,
                column_config={
                    "Part Number": st.column_config.TextColumn(disabled=True),
                    "Part Name": st.column_config.TextColumn(disabled=True),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(disabled=True),
                    "Unit Price": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Amount": st.column_config.NumberColumn(format="%d", disabled=True),
                },
                num_rows="dynamic",
                use_container_width=True,
                key="cart_editor"
            )

            # Tính toán lại Amount cho từng dòng: (Price * Qty * Discount) / 100 theo yêu cầu của bạn
            # Lưu ý: Nếu bạn muốn tính "Giá sau chiết khấu" thì công thức sẽ khác, 
            # nhưng đây là công thức bạn yêu cầu: (Col 7 * Col 8) / 100
            edited_df['Amount'] = (edited_df['Unit Price'] * edited_df['% Discount']) / 100
            
            # Cập nhật lại session state
            st.session_state.cart = edited_df

    elif st.session_state.current_page == "Management":
        st.write("Management Page (Coming Soon)")
