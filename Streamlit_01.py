import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Spare Part System", layout="wide")

# --- HÀM LOAD DỮ LIỆU ---
@st.cache_data(ttl=60)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Load các tab
    mst = conn.read(worksheet="Customer_MST").dropna(how='all')
    contact = conn.read(worksheet="Customer_Contact").dropna(how='all')
    staff = conn.read(worksheet="Staff").dropna(how='all')
    machines = conn.read(worksheet="List_of_ machines").dropna(how='all')
    sp_list = conn.read(worksheet="SP_List").dropna(how='all')
    return mst, contact, staff, machines, sp_list

try:
    df_mst, df_contact, df_staff, df_machines, df_sp = load_data()
except Exception as e:
    st.error(f"Lỗi kết nối dữ liệu: {e}")
    st.stop()

# --- KHỞI TẠO BIẾN TẠM (SESSION STATE) ---
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'page' not in st.session_state:
    st.session_state.page = "New"

# --- A_1: SIDE MENU ---
with st.sidebar:
    st.title("⚙️ MENU")
    menu = st.radio("Chuyên mục:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- CHƯƠNG TRÌNH CHÍNH ---
if menu == "Spare Part Quotation":
    # A_2: Hai nút bấm điều hướng
    col_n1, col_n2, _ = st.columns([2, 2, 5])
    if col_n1.button("New Spare Part Offer", use_container_width=True):
        st.session_state.page = "New"
    if col_nav2 = col_n2.button("Order Management", use_container_width=True):
        st.session_state.page = "Manage"

    st.divider()

    if st.session_state.page == "New":
        # --- B_1: OFFER HEADER (Layout hàng dọc) ---
        
        # 1. Customer Name (Col C -> index 2)
        # Lọc bỏ giá trị null và lấy danh sách duy nhất
        cust_list = df_mst.iloc[:, 2].dropna().unique().tolist()
        selected_cust = st.selectbox("Customer Name:", options=cust_list)
        
        # Tìm dòng khách hàng tương ứng
        cust_info = df_mst[df_mst.iloc[:, 2] == selected_cust].iloc[0]
        
        # 2. Customer No (Col B -> index 1)
        c_no = str(cust_info.iloc[1]).split('.')[0] # Xóa đuôi .0 nếu là số
        st.text_input("Customer No:", value=c_no, disabled=True)
        
        # 3. Tax Code (Col F -> index 5)
        tax_code = str(cust_info.iloc[5]) if not pd.isna(cust_info.iloc[5]) else ""
        st.text_input("Tax Code:", value=tax_code, disabled=True)
        
        # 4. Address (Col E -> index 4)
        address = str(cust_info.iloc[4])
        st.text_area("Address:", value=address, height=80, disabled=True)
        
        # 5. Contact Person (Tab Contact / Col H -> index 7)
        # Lọc danh sách liên hệ theo Customer No (Tab Contact / Col B -> index 1)
        f_contact = df_contact[df_contact.iloc[:, 1].astype(str).str.contains(c_no)]
        contact_names = f_contact.iloc[:, 7].dropna().tolist() if not f_contact.empty else ["N/A"]
        st.selectbox("Contact Person:", options=contact_names)
        
        # 6. Officer (Tab Staff / Col B -> index 1)
        officers = df_staff.iloc[:, 1].dropna().tolist()
        st.selectbox("Officer:", options=officers)
        
        # 7. Machine Number (Tab Machines / Col O -> index 14)
        # Lọc máy theo Customer No (Tab Machines / Col B -> index 1)
        f_machines = df_machines[df_machines.iloc[:, 1].astype(str).str.contains(c_no)]
        machine_list = f_machines.iloc[:, 14].dropna().tolist() if not f_machines.empty else ["N/A"]
        st.selectbox("Machine Number:", options=machine_list)
        
        # 8. Offer Date
        off_date = st.date_input("Offer Date:", value=datetime.now())
        
        # 9. Offer No (Input tay định dạng 2026-05-0001)
        st.text_input("Offer No:", value=f"{off_date.year}-{off_date.month:02d}-0001")

        # --- Dòng kẻ ngăn cách ---
        st.markdown("<hr style='border: 1.5px solid #FF4B4B'>", unsafe_allow_html=True)

        # --- B_2: OFFER DESCRIPTIONS ---
        st.subheader("🛒 Offer Descriptions")
        search_input = st.text_input("Search Part Number:", placeholder="Nhập mã hoặc dãy mã cách nhau bởi dấu ';' (vd: 2024956492;2031956280)")
        
        col_b1, col_b2, _ = st.columns([1.5, 1.5, 5])
        add_btn = col_b1.button("Add to Cart", type="primary", use_container_width=True)
        clear_btn = col_b2.button("Delete Cart", use_container_width=True)

        if clear_btn:
            st.session_state.cart = []
            st.rerun()

        if add_btn and search_input:
            p_codes = [x.strip() for x in search_input.split(";")]
            for code in p_codes:
                # Tìm trong SP_List / Col B -> index 1
                match = df_sp[df_sp.iloc[:, 1].astype(str).str.strip() == code]
                if not match.empty:
                    item = match.iloc[0]
                    # Thu thập thông tin theo yêu cầu
                    st.session_state.cart.append({
                        "Part Number": str(item.iloc[1]), # Col B
                        "Part Name": str(item.iloc[4]),   # Col E
                        "Qty": 1.0,                       # Mặc định 1
                        "Unit": str(item.iloc[7]),        # Col H
                        "VAT": float(item.iloc[12]) if not pd.isna(item.iloc[12]) else 0.0, # Col M
                        "Unit Price": float(item.iloc[18]) if not pd.isna(item.iloc[18]) else 0.0, # Col S
                        "% Discount": 0.0
                    })
                else:
                    st.error(f"Part Number {code} is not available")
            st.rerun()

        # HIỂN THỊ BẢNG GIỎ HÀNG
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            
            # Tính toán Column 9: Amount = (Unit Price * % Discount) / 100
            df_cart["Amount"] = (df_cart["Unit Price"] * df_cart["% Discount"]) / 100
            
            # Thêm cột No (số thứ tự) và Delete
            df_cart.insert(0, "No", range(1, len(df_cart) + 1))
            df_cart["Delete"] = False

            # Giao diện bảng có thể sửa đổi Qty và Discount
            edited_df = st.data_editor(
                df_cart,
                column_config={
                    "No": st.column_config.NumberColumn(disabled=True),
                    "Part Number": st.column_config.TextColumn(disabled=True),
                    "Part Name": st.column_config.TextColumn(disabled=True),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(format="%.2f", disabled=True),
                    "Unit Price": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Qty": st.column_config.NumberColumn(min_value=0.0, step=1.0),
                    "% Discount": st.column_config.NumberColumn(min_value=0.0, max_value=100.0),
                    "Amount": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Delete": st.column_config.CheckboxColumn("Xóa")
                },
                hide_index=True,
                use_container_width=True,
                key="editor_sp"
            )

            # Xử lý cập nhật dữ liệu khi người dùng sửa trên bảng
            if not edited_df.equals(df_cart):
                # Lọc bỏ các dòng được chọn "Delete"
                new_cart = edited_df[edited_df["Delete"] == False]
                # Lưu lại vào session (bỏ các cột phụ No, Amount, Delete)
                st.session_state.cart = new_cart.drop(columns=["No", "Amount", "Delete"]).to_dict('records')
                st.rerun()

    elif st.session_state.page == "Manage":
        st.info("Trang Order Management")
