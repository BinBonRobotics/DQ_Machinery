import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="HOMAG Spare Part System", layout="wide")

# --- HÀM LOAD DỮ LIỆU ---
@st.cache_data(ttl=300) # Lưu bộ nhớ đệm trong 5 phút
def load_all_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Đọc dữ liệu từ các tab
    df_mst = conn.read(worksheet="Customer_MST")
    df_contact = conn.read(worksheet="Customer_Contact")
    df_staff = conn.read(worksheet="Staff")
    df_machines = conn.read(worksheet="List_of_ machines")
    df_sp = conn.read(worksheet="SP_List")
    
    # Làm sạch dữ liệu: Xóa khoảng trắng ở đầu/cuối tên cột
    for df in [df_mst, df_contact, df_staff, df_machines, df_sp]:
        df.columns = df.columns.str.strip()
        
    return df_mst, df_contact, df_staff, df_machines, df_sp

# Load dữ liệu
try:
    df_mst, df_contact, df_staff, df_machines, df_sp = load_all_data()
except Exception as e:
    st.error(f"❌ Không thể kết nối dữ liệu: {e}. Vui lòng kiểm tra lại tên Tab trên Google Sheets.")
    st.stop()

# --- KHỞI TẠO SESSION STATE ---
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'page' not in st.session_state:
    st.session_state.page = "New Offer"

# --- A_1: SIDE MENU ---
with st.sidebar:
    st.title("Menu Hệ Thống")
    menu_option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- CHỨC NĂNG CHÍNH ---
if menu_option == "Spare Part Quotation":
    # A_2: Hai nút điều hướng
    col_nav1, col_nav2, _ = st.columns([1.5, 1.5, 4])
    if col_nav1.button("➕ New Spare Part Offer", use_container_width=True):
        st.session_state.page = "New Offer"
    if col_nav2.button("📋 Order Management", use_container_width=True):
        st.session_state.page = "Management"

    st.divider()

    if st.session_state.page == "New Offer":
        # --- B_1: OFFER HEADER (LAYOUT HÀNG DỌC) ---
        
        # 1. Customer Name (Tab: Customer_MST, Col: Customer name)
        cust_list = df_mst['Customer name'].dropna().unique().tolist()
        cust_name = st.selectbox("🎯 Customer Name:", options=cust_list)
        
        # Lấy thông tin chi tiết khách hàng
        cust_row = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
        
        # 2. Customer No (Col: Customer no)
        # Chuyển về string để hiển thị
        cust_no_val = str(cust_row['Customer no']).split('.')[0]
        st.text_input("🆔 Customer No:", value=cust_no_val, disabled=True)
        
        # 3. Tax Code (Col: Tax_Code)
        tax_val = str(cust_row['Tax_Code']) if 'Tax_Code' in df_mst.columns else ""
        st.text_input("🧾 Tax Code:", value=tax_val, disabled=True)
        
        # 4. Address (Col: Địa chỉ)
        addr_val = str(cust_row['Địa chỉ'])
        st.text_area("📍 Address:", value=addr_val, height=80, disabled=True)
        
        # 5. Contact Person (Tab: Customer_Contact, Col: Customer contact)
        # Lọc contact dựa trên Customer No
        f_contacts = df_contact[df_contact['Customer no'].astype(str).str.contains(cust_no_val)]
        contact_list = f_contacts['Customer contact'].dropna().tolist() if not f_contacts.empty else ["No contact available"]
        st.selectbox("👤 Contact Person:", options=contact_list)
        
        # 6. Officer (Tab: Staff, Col: Name)
        staff_list = df_staff['Name'].dropna().tolist()
        st.selectbox("✍️ Officer:", options=staff_list)
        
        # 7. Machine Number (Tab: List_of_ machines, Col: Machine No.)
        f_machines = df_machines[df_machines['Customer no'].astype(str).str.contains(cust_no_val)]
        machine_list = f_machines['Machine No.'].dropna().tolist() if not f_machines.empty else ["No machine found"]
        st.selectbox("🤖 Machine Number:", options=machine_list)
        
        # 8. Offer Date (Calendar)
        offer_date = st.date_input("📅 Offer Date:", value=datetime.now())
        
        # 9. Offer No (Year-Month-0001)
        offer_no_default = f"{offer_date.year}-{offer_date.month:02d}-0001"
        st.text_input("📄 Offer No:", value=offer_no_default)

        # --- Dòng kẻ ngăn cách ---
        st.markdown("---")

        # --- B_2: OFFER DESCRIPTIONS ---
        st.subheader("🛒 Part List")
        
        search_input = st.text_input("🔍 Search Part Number (ví dụ: 2024956492;2031956280):")
        
        col_c1, col_c2, _ = st.columns([1, 1, 4])
        if col_c1.button("📦 Add to Cart", type="primary", use_container_width=True):
            if search_input:
                codes = [c.strip() for c in search_input.split(';')]
                for code in codes:
                    # Tìm trong SP_List, cột 'Part number'
                    match = df_sp[df_sp['Part number'].astype(str) == str(code)]
                    if not match.empty:
                        item = match.iloc[0]
                        # Kiểm tra xem mã đã có trong giỏ chưa để tránh trùng
                        if not any(d['Part Number'] == code for d in st.session_state.cart):
                            st.session_state.cart.append({
                                "Part Number": str(item['Part number']),
                                "Part Name": item['Part name'],
                                "Qty": 1,
                                "Unit": item['Unit'],
                                "VAT": item['VAT'],
                                "Unit Price": float(item['Giá bán']) if not pd.isna(item['Giá bán']) else 0.0,
                                "% Discount": 0.0
                            })
                    else:
                        st.warning(f"⚠️ Part Number {code} is not available")
                st.rerun()

        if col_c2.button("🗑️ Delete Cart", use_container_width=True):
            st.session_state.cart = []
            st.rerun()

        # Hiển thị bảng giỏ hàng
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            
            # Đánh số thứ tự (Column 1: No)
            df_cart.insert(0, "No", range(1, len(df_cart) + 1))
            
            # Tính toán Column 9: Amount = (Price * Discount) / 100
            # Lưu ý: Đây là số tiền giảm giá theo yêu cầu của bạn.
            # Nếu muốn tính tiền phải trả, công thức là: (Price * Qty) - ((Price * Qty * Discount)/100)
            df_cart['Amount'] = (df_cart['Unit Price'] * df_cart['% Discount']) / 100
            
            # Column 10: Delete (Sử dụng data_editor để có checkbox xóa)
            df_cart['Delete'] = False
            
            edited_df = st.data_editor(
                df_cart,
                column_config={
                    "No": st.column_config.NumberColumn(disabled=True),
                    "Part Number": st.column_config.TextColumn(disabled=True),
                    "Part Name": st.column_config.TextColumn(disabled=True),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(format="%.2f", disabled=True),
                    "Unit Price": st.column_config.NumberColumn(format="%.0f", disabled=True),
                    "Qty": st.column_config.NumberColumn(min_value=1, step=1),
                    "% Discount": st.column_config.NumberColumn(min_value=0, max_value=100, step=1),
                    "Amount": st.column_config.NumberColumn(format="%.0f", disabled=True),
                    "Delete": st.column_config.CheckboxColumn("Xóa dòng")
                },
                hide_index=True,
                use_container_width=True
            )

            # Xử lý cập nhật dữ liệu hoặc xóa dòng
            if not edited_df.equals(df_cart):
                # Lọc bỏ những dòng bị tích chọn 'Delete'
                new_cart = edited_df[edited_df['Delete'] == False].drop(columns=['No', 'Amount', 'Delete']).to_dict('records')
                st.session_state.cart = new_cart
                st.rerun()

    elif st.session_state.page == "Management":
        st.info("Trang Order Management đang được phát triển...")
