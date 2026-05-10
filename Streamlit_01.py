import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(layout="wide", page_title="Quotation System")

# URL Google Sheet của bạn
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8/edit#gid=903775380"

# --- 2. HÀM KẾT NỐI VÀ LOAD DỮ LIỆU ---
@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Load tất cả các Tab cần thiết
        mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST").dropna(how='all')
        contact = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact").dropna(how='all')
        staff = conn.read(spreadsheet=SHEET_URL, worksheet="Staff").dropna(how='all')
        machines = conn.read(spreadsheet=SHEET_URL, worksheet="List_of_ machines").dropna(how='all')
        sp = conn.read(spreadsheet=SHEET_URL, worksheet="SP_List").dropna(how='all')
        return mst, contact, staff, machines, sp
    except Exception as e:
        st.error(f"Lỗi kết nối dữ liệu: {e}")
        return None, None, None, None, None

df_mst, df_contact, df_staff, df_machines, df_sp = load_data()

# Khởi tạo Session State cho giỏ hàng và trạng thái hiển thị
if 'cart' not in st.session_state: st.session_state.cart = []
if 'page_view' not in st.session_state: st.session_state.page_view = "New"

# --- 3. LAYOUT A_1: SIDE MENU ---
with st.sidebar:
    st.header("MENU")
    option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 4. CHỨC NĂNG CHÍNH ---
if df_mst is not None and option == "Spare Part Quotation":
    # A_2: Hai nút bấm bên phải
    col_b1, col_b2, _ = st.columns([2, 2, 5])
    if col_b1.button("New Spare Part Offer", use_container_width=True): st.session_state.page_view = "New"
    if col_b2.button("Order Management", use_container_width=True): st.session_state.page_view = "Manage"

    if st.session_state.page_view == "New":
        st.markdown("### New Spare Part Offer")
        
        # --- B_1: OFFER HEADER (TOP DOWN) ---
        # 1. Customer Name (Col C - index 2)
        names = df_mst.iloc[:, 2].dropna().unique().tolist()
        selected_name = st.selectbox("Customer Name:", options=names)
        cust_row = df_mst[df_mst.iloc[:, 2] == selected_name].iloc[0]
        
        # 2. Customer No (Col B - index 1)
        c_no = str(cust_row.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=c_no, disabled=True)
        
        # 3. Tax Code (Col F - index 5) -> Xử lý xóa đuôi .0
        t_code = str(cust_row.iloc[5]).split('.')[0] if not pd.isna(cust_row.iloc[5]) else ""
        st.text_input("Tax Code:", value=t_code, disabled=True)
        
        # 4. Address (Col E - index 4)
        addr = str(cust_row.iloc[4]) if not pd.isna(cust_row.iloc[4]) else ""
        st.text_area("Address:", value=addr, height=70, disabled=True)
        
        # 5. Contact Person (Tab Contact / Col H - index 7 / Lọc theo Customer No)
        f_contact = df_contact[df_contact.iloc[:, 1].astype(str).str.contains(c_no)]
        contact_list = f_contact.iloc[:, 7].dropna().tolist() if not f_contact.empty else ["N/A"]
        st.selectbox("Contact Person:", options=contact_list)
        
        # 6. Officer (Tab Staff / Col B - index 1)
        officer_list = df_staff.iloc[:, 1].dropna().tolist()
        st.selectbox("Officer:", options=officer_list)
        
        # 7. Machine Number (Tab Machines / Col O - index 14 / Lọc theo Customer No)
        f_machines = df_machines[df_machines.iloc[:, 1].astype(str).str.contains(c_no)]
        machine_list = f_machines.iloc[:, 14].dropna().tolist() if not f_machines.empty else ["N/A"]
        st.selectbox("Machine Number:", options=machine_list)
        
        # 8. Offer Date
        off_date = st.date_input("Offer Date:", value=datetime.now())
        
        # 9. Offer No
        st.text_input("Offer No:", value=f"{off_date.year}-{off_date.month:02d}-0001")

        # --- DÒNG KẺ PHÂN CÁCH ---
        st.markdown("---")
        st.subheader("Offer Descriptions")

        # --- B_2: OFFER DESCRIPTIONS ---
        search_input = st.text_input("Search Part Number:", placeholder="Ví dụ: 2024956492;2031956280")
        
        col_act1, col_act2, _ = st.columns([1.5, 1.5, 6])
        
        # Nút Add to Cart
        if col_act1.button("Add to Cart", type="primary", use_container_width=True):
            if search_input:
                codes = [c.strip() for c in search_input.split(';')]
                for code in codes:
                    # Tìm mã trong SP_List (Col B - index 1)
                    match = df_sp[df_sp.iloc[:, 1].astype(str) == code]
                    if not match.empty:
                        item = match.iloc[0]
                        st.session_state.cart.append({
                            "Part Number": str(item.iloc[1]), # Col B
                            "Part Nname": str(item.iloc[4]),  # Col E
                            "Qty": 1,
                            "Unit": str(item.iloc[7]),        # Col H
                            "VAT": item.iloc[12],             # Col M
                            "Unit Price": float(item.iloc[18]) if not pd.isna(item.iloc[18]) else 0.0, # Col S
                            "% Distcount": 0.0
                        })
                    else:
                        st.error(f"Part Number {code} is not available")
                st.rerun()

        # Nút Delete Cart
        if col_act2.button("Delete Cart", use_container_width=True):
            st.session_state.cart = []
            st.rerun()

        # Bảng hiển thị kết quả
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            
            # Tính toán Column 9: Amount = Qty * (UnitPrice * %Discount) / 100
            df_cart["Amount"] = df_cart["Qty"] * (df_cart["Unit Price"] * df_cart["% Distcount"]) / 100
            
            # Thêm cột số thứ tự và cột xóa
            df_cart.insert(0, "No", range(1, len(df_cart) + 1))
            df_cart["Delete"] = False

            # Hiển thị bảng có thể chỉnh sửa
            edited_df = st.data_editor(
                df_cart,
                column_config={
                    "No": st.column_config.NumberColumn(disabled=True),
                    "Part Number": st.column_config.TextColumn(disabled=True),
                    "Part Nname": st.column_config.TextColumn(disabled=True),
                    "Qty": st.column_config.NumberColumn(min_value=1, step=1),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(format="%.2f", disabled=True),
                    "Unit Price": st.column_config.NumberColumn(format="%d", disabled=True),
                    "% Distcount": st.column_config.NumberColumn(min_value=0, max_value=100),
                    "Amount": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Delete": st.column_config.CheckboxColumn("Xóa dòng")
                },
                hide_index=True,
                use_container_width=True,
                key="editor"
            )

            # Xử lý cập nhật dữ liệu khi người dùng sửa trên bảng
            if not edited_df.equals(df_cart):
                # Lọc bỏ các dòng được chọn Delete
                new_cart = edited_df[edited_df["Delete"] == False].drop(columns=["No", "Amount", "Delete"]).to_dict('records')
                st.session_state.cart = new_cart
                st.rerun()

    elif st.session_state.page_view == "Manage":
        st.info("Trang Order Management đang được cập nhật...")

elif option == "Service Quotation":
    st.write("### Service Quotation Section")
