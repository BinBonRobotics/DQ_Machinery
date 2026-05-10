import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- A_General layout ---
st.set_page_config(page_title="HOMAG Quotation System", layout="wide")

# Hàm load dữ liệu và dọn dẹp dòng trống
@st.cache_data(ttl=60)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Load và bỏ các dòng hoàn toàn trống để tránh lỗi Index
    df_mst = conn.read(worksheet="Customer_MST").dropna(how='all')
    df_contact = conn.read(worksheet="Customer_Contact").dropna(how='all')
    df_staff = conn.read(worksheet="Staff").dropna(how='all')
    df_machines = conn.read(worksheet="List_of_ machines").dropna(how='all')
    df_sp = conn.read(worksheet="SP_List").dropna(how='all')
    return df_mst, df_contact, df_staff, df_machines, df_sp

try:
    df_mst, df_contact, df_staff, df_machines, df_sp = load_data()
except Exception as e:
    st.error(f"Lỗi kết nối Sheet: {e}")
    st.stop()

# Khởi tạo session state để lưu trữ trạng thái trang và giỏ hàng
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'page_view' not in st.session_state:
    st.session_state.page_view = "Main"

# --- A_1: Side menu (Left side) ---
with st.sidebar:
    st.title("📋 MENU")
    option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- A_2: Main Content (Right hand page) ---
if option == "Spare Part Quotation":
    # Tạo 2 nút bấm ở phía trên cùng của trang bên phải
    col_btn1, col_btn2, _ = st.columns([2, 2, 5])
    
    if col_btn1.button("New Spare Part Offer", use_container_width=True):
        st.session_state.page_view = "NewOffer"
    
    if col_btn2.button("Order Management", use_container_width=True):
        st.session_state.page_view = "Management"

    st.divider()

    # --- B_Functions: 1_Click New Spare Part Offer ---
    if st.session_state.page_view == "NewOffer":
        
        # --- B_1: Offer Header (Từ trên xuống dưới) ---
        
        # 1. Customer Name (Col C -> index 2)
        cust_list = df_mst.iloc[:, 2].dropna().unique().tolist()
        selected_cust = st.selectbox("Customer Name:", options=cust_list)
        
        # Lấy row dữ liệu khách hàng được chọn
        cust_row = df_mst[df_mst.iloc[:, 2] == selected_cust].iloc[0]
        
        # 2. Customer No (Col B -> index 1) - Convert sang String
        cust_no = str(cust_row.iloc[1]).split('.')[0] # Bỏ đuôi .0 nếu là số
        st.text_input("Customer No:", value=cust_no, disabled=True)
        
        # 3. Tax Code (Col F -> index 5)
        tax_code = str(cust_row.iloc[5]) if not pd.isna(cust_row.iloc[5]) else ""
        st.text_input("Tax Code:", value=tax_code, disabled=True)
        
        # 4. Address (Col E -> index 4)
        address = str(cust_row.iloc[4])
        st.text_area("Address:", value=address, height=80, disabled=True)
        
        # 5. Contact Person (Tab Contact / Col H -> index 7)
        # Tìm dựa trên Customer No (Col B của tab Contact -> index 1)
        f_contact = df_contact[df_contact.iloc[:, 1].astype(str).str.contains(cust_no)]
        contact_list = f_contact.iloc[:, 7].dropna().tolist() if not f_contact.empty else ["N/A"]
        st.selectbox("Contact Person:", options=contact_list)
        
        # 6. Officer (Tab Staff / Col B -> index 1)
        officer_list = df_staff.iloc[:, 1].dropna().tolist()
        st.selectbox("Officer:", options=officer_list)
        
        # 7. Machine Number (Tab Machines / Col O -> index 14)
        # Tìm dựa trên Customer No (Col B của tab Machines -> index 1)
        f_machines = df_machines[df_machines.iloc[:, 1].astype(str).str.contains(cust_no)]
        machine_list = f_machines.iloc[:, 14].dropna().tolist() if not f_machines.empty else ["N/A"]
        st.selectbox("Machine Number:", options=machine_list)
        
        # 8. Offer Date
        offer_date = st.date_input("Offer Date:", value=datetime.now())
        
        # 9. Offer No (Year-Month-0001)
        st.text_input("Offer No:", value=f"{offer_date.year}-{offer_date.month:02d}-0001")

        # --- Đường kẻ ngăn cách Header và Description ---
        st.markdown("---")
        st.subheader("Offer Descriptions")

        # --- B_2: Search Part Number ---
        search_val = st.text_input("Search Part Number (vd: 2024956492;2031956280):")
        
        col_act1, col_act2, _ = st.columns([1.5, 1.5, 6])
        add_btn = col_act1.button("Add to Cart", type="primary", use_container_width=True)
        del_btn = col_act2.button("Delete Cart", use_container_width=True)

        if del_btn:
            st.session_state.cart = []
            st.rerun()

        if add_btn and search_val:
            codes = [c.strip() for c in search_val.split(';')]
            for code in codes:
                # Tìm trong SP_List / Col B -> index 1
                match = df_sp[df_sp.iloc[:, 1].astype(str) == code]
                if not match.empty:
                    item = match.iloc[0]
                    # Thêm vào giỏ hàng nếu chưa có (hoặc cộng dồn tùy bạn, ở đây là thêm mới)
                    st.session_state.cart.append({
                        "Part Number": str(item.iloc[1]), # Col B
                        "Part Name": str(item.iloc[4]),   # Col E
                        "Qty": 1.0,
                        "Unit": str(item.iloc[7]),        # Col H
                        "VAT": float(item.iloc[12]) if not pd.isna(item.iloc[12]) else 0.0, # Col M
                        "Unit Price": float(item.iloc[18]) if not pd.isna(item.iloc[18]) else 0.0, # Col S
                        "% Discount": 0.0
                    })
                else:
                    st.warning(f"Part Number {code} is not available")
            st.rerun()

        # Hiển thị bảng kết quả (Cart)
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            
            # Tính Column 9: Amount = (Unit Price * % Discount) / 100
            # Lưu ý: Theo công thức bạn đưa, đây là số tiền được giảm.
            df_cart["Amount"] = (df_cart["Unit Price"] * df_cart["% Discount"]) / 100
            
            # Thêm cột No và cột Delete
            df_cart.insert(0, "No", range(1, len(df_cart) + 1))
            df_cart["Delete"] = False

            edited_df = st.data_editor(
                df_cart,
                column_config={
                    "No": st.column_config.NumberColumn(disabled=True),
                    "Part Number": st.column_config.TextColumn(disabled=True),
                    "Part Name": st.column_config.TextColumn(disabled=True),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(format="%.2f", disabled=True),
                    "Unit Price": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Qty": st.column_config.NumberColumn(min_value=1.0, step=1.0),
                    "% Discount": st.column_config.NumberColumn(min_value=0.0, max_value=100.0),
                    "Amount": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Delete": st.column_config.CheckboxColumn("Xóa dòng")
                },
                hide_index=True,
                use_container_width=True,
                key="editor"
            )

            # Cập nhật lại giỏ hàng nếu có thay đổi hoặc xóa
            if not edited_df.equals(df_cart):
                new_cart = edited_df[edited_df["Delete"] == False].drop(columns=["No", "Amount", "Delete"]).to_dict('records')
                st.session_state.cart = new_cart
                st.rerun()

    elif st.session_state.page_view == "Management":
        st.write("### Order Management Page")
        st.info("Chức năng quản lý đơn hàng đang chờ thiết kế thêm.")

elif option == "Service Quotation":
    st.write("### Service Quotation Page")
