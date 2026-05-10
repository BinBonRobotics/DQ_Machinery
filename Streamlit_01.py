import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Spare Part System", layout="wide")

# --- LOAD DATA ---
@st.cache_data(ttl=300)
def load_all_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Load các tab theo yêu cầu
    df_mst = conn.read(worksheet="Customer_MST")
    df_contact = conn.read(worksheet="Customer_Contact")
    df_staff = conn.read(worksheet="Staff")
    df_machines = conn.read(worksheet="List_of_ machines")
    df_sp = conn.read(worksheet="SP_List")
    
    # Chuẩn hóa tên cột (xóa khoảng trắng thừa)
    for df in [df_mst, df_contact, df_staff, df_machines, df_sp]:
        df.columns = df.columns.str.strip()
        
    return df_mst, df_contact, df_staff, df_machines, df_sp

try:
    df_mst, df_contact, df_staff, df_machines, df_sp = load_all_data()
except Exception as e:
    st.error(f"Lỗi kết nối dữ liệu: {e}")
    st.stop()

# --- SESSION STATE ---
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'page' not in st.session_state:
    st.session_state.page = "Main"

# --- A_1: SIDE MENU ---
with st.sidebar:
    st.title("MENU")
    menu = st.radio("Chuyên mục:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- MAIN PAGE ---
if menu == "Spare Part Quotation":
    # A_2: Hai nút bấm bên phải
    col_n1, col_n2, _ = st.columns([1.5, 1.5, 4])
    btn_new = col_n1.button("New Spare Part Offer", use_container_width=True)
    btn_manage = col_n2.button("Order Management", use_container_width=True)
    
    if btn_new: st.session_state.page = "NewOffer"
    if btn_manage: st.session_state.page = "Manage"

    st.markdown("---")

    if st.session_state.page == "NewOffer":
        # B_1: OFFER HEADER (Layout hàng dọc từ trên xuống)
        
        # 1. Customer Name (Col C)
        cust_list = df_mst.iloc[:, 2].dropna().unique().tolist()
        selected_cust = st.selectbox("Customer Name:", options=cust_list)
        
        # Lấy dữ liệu khách hàng được chọn
        cust_info = df_mst[df_mst.iloc[:, 2] == selected_cust].iloc[0]
        
        # 2. Customer No (Col B)
        c_no = str(cust_info.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=c_no, disabled=True)
        
        # 3. Tax Code (Col F)
        t_code = str(cust_info.iloc[5])
        st.text_input("Tax Code:", value=t_code, disabled=True)
        
        # 4. Address (Col E)
        addr = str(cust_info.iloc[4])
        st.text_area("Address:", value=addr, height=70, disabled=True)
        
        # 5. Contact Person (Tab Customer_Contact/Col H lọc theo Cust No)
        # Giả định Col B trong Contact là Customer No
        f_contacts = df_contact[df_contact.iloc[:, 1].astype(str).str.contains(c_no)]
        contact_list = f_contacts.iloc[:, 7].dropna().tolist() if not f_contacts.empty else ["N/A"]
        st.selectbox("Contact Person:", options=contact_list)
        
        # 6. Officer (Tab Staff/Col B)
        officer_list = df_staff.iloc[:, 1].dropna().tolist()
        st.selectbox("Officer:", options=officer_list)
        
        # 7. Machine Number (Tab List_of_machines/Col O lọc theo Cust No)
        f_machines = df_machines[df_machines.iloc[:, 1].astype(str).str.contains(c_no)]
        machine_list = f_machines.iloc[:, 14].dropna().tolist() if not f_machines.empty else ["N/A"]
        st.selectbox("Machine Number:", options=machine_list)
        
        # 8. Offer Date
        off_date = st.date_input("Offer Date:", value=datetime.now())
        
        # 9. Offer No
        off_no_default = f"{off_date.year}-{off_date.month:02d}-0001"
        st.text_input("Offer No:", value=off_no_default)

        # Dòng kẻ ngăn cách Offer Header và Offer Description
        st.markdown("<hr style='border:2px solid gray'>", unsafe_allow_html=True)

        # B_2: OFFER DESCRIPTIONS
        st.subheader("Search Part Number")
        search_input = st.text_input("Input Part Number (separate by ';'):", placeholder="2024956492;2031956280")
        
        col_b1, col_b2, _ = st.columns([1, 1, 4])
        add_to_cart = col_b1.button("Add to Cart", type="primary")
        delete_cart = col_b2.button("Delete Cart")

        if delete_cart:
            st.session_state.cart = []
            st.rerun()

        if add_to_cart and search_input:
            parts_to_search = [p.strip() for p in search_input.split(";")]
            for p_num in parts_to_search:
                # Tìm trong SP_List/Col B
                match = df_sp[df_sp.iloc[:, 1].astype(str) == p_num]
                if not match.empty:
                    res = match.iloc[0]
                    # Thêm vào giỏ hàng (Tránh trùng lặp nếu cần)
                    st.session_state.cart.append({
                        "Part Number": str(res.iloc[1]), # Col B
                        "Part Name": res.iloc[4],       # Col E
                        "Qty": 1,
                        "Unit": res.iloc[7],            # Col H
                        "VAT": res.iloc[12],            # Col M
                        "Unit Price": float(res.iloc[18]) if not pd.isna(res.iloc[18]) else 0, # Col S
                        "% Discount": 0.0
                    })
                else:
                    st.error(f"Part Number {p_num} is not available")
            st.rerun()

        # HIỂN THỊ BẢNG GIỎ HÀNG (Nếu có hàng)
        if st.session_state.cart:
            df_display = pd.DataFrame(st.session_state.cart)
            
            # Tính toán Column 9: Amount = (UnitPrice * Discount) / 100
            df_display["Amount"] = (df_display["Unit Price"] * df_display["% Discount"]) / 100
            
            # Thêm cột No (Số thứ tự)
            df_display.insert(0, "No", range(1, len(df_display) + 1))
            
            # Thêm cột Delete (Checkbox)
            df_display["Delete"] = False

            # Sử dụng data_editor để UI có thể chỉnh sửa Qty và % Discount
            edited_df = st.data_editor(
                df_display,
                column_config={
                    "No": st.column_config.NumberColumn(disabled=True),
                    "Part Number": st.column_config.TextColumn(disabled=True),
                    "Part Name": st.column_config.TextColumn(disabled=True),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(disabled=True),
                    "Unit Price": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Qty": st.column_config.NumberColumn(min_value=1),
                    "% Discount": st.column_config.NumberColumn(min_value=0, max_value=100),
                    "Amount": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Delete": st.column_config.CheckboxColumn("Xóa")
                },
                hide_index=True,
                use_container_width=True
            )

            # Xử lý cập nhật Qty/Discount hoặc Xóa dòng
            # Nếu người dùng nhấn chọn Delete hoặc thay đổi số liệu
            if not edited_df.equals(df_display):
                # Loại bỏ những dòng bị tích chọn 'Delete'
                new_cart_df = edited_df[edited_df["Delete"] == False]
                # Cập nhật lại session state (bỏ các cột tạm No, Amount, Delete)
                st.session_state.cart = new_cart_df.drop(columns=["No", "Amount", "Delete"]).to_dict('records')
                st.rerun()

    elif st.session_state.page == "Manage":
        st.write("Dữ liệu Order Management sẽ hiển thị ở đây.")
