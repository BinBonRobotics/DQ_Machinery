import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- A_General layout ---
st.set_page_config(page_title="HOMAG Spare Part", layout="wide")

# Hàm load data an toàn
@st.cache_data(ttl=60)
def get_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Đọc tất cả các tab cần thiết
    mst = conn.read(worksheet="Customer_MST")
    contact = conn.read(worksheet="Customer_Contact")
    staff = conn.read(worksheet="Staff")
    machines = conn.read(worksheet="List_of_ machines")
    sp = conn.read(worksheet="SP_List")
    
    # Làm sạch tên cột (xóa khoảng trắng thừa hoặc ký tự xuống dòng)
    for df in [mst, contact, staff, machines, sp]:
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        
    return mst, contact, staff, machines, sp

try:
    df_mst, df_contact, df_staff, df_machines, df_sp = get_data()
except Exception as e:
    st.error(f"Lỗi kết nối Sheet: {e}")
    st.stop()

# Khởi tạo session lưu trữ giỏ hàng
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'offer_page' not in st.session_state:
    st.session_state.offer_page = "Main"

# --- A_1: Side menu ---
with st.sidebar:
    st.header("MENU")
    menu = st.radio("Options:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh"):
        st.cache_data.clear()
        st.rerun()

# --- A_2: Spare Part Quotation Logic ---
if menu == "Spare Part Quotation":
    col_btn1, col_btn2, _ = st.columns([2, 2, 5])
    if col_btn1.button("New Spare Part Offer", use_container_width=True):
        st.session_state.offer_page = "NewOffer"
    if col_btn2.button("Order Management", use_container_width=True):
        st.session_state.offer_page = "Management"

    st.divider()

    if st.session_state.offer_page == "NewOffer":
        # --- B_1: Offer Header (Top to Bottom) ---
        
        # Customer Name (Ref: Customer_MST / Col: Customer name)
        cust_name_list = df_mst["Customer name"].dropna().unique().tolist()
        customer_name = st.selectbox("Customer Name:", options=cust_name_list)
        
        # Lấy row dữ liệu khách hàng
        cust_row = df_mst[df_mst["Customer name"] == customer_name].iloc[0]
        
        # Customer No (Ref: Customer_MST / Col: Customer no)
        cust_no = str(cust_row["Customer no"]).split('.')[0]
        st.text_input("Customer No:", value=cust_no, disabled=True)
        
        # Tax Code (Ref: Customer_MST / Col: Tax_Code)
        tax_code = str(cust_row["Tax_Code"])
        st.text_input("Tax Code:", value=tax_code, disabled=True)
        
        # Address (Ref: Customer_MST / Col: Địa chỉ)
        address = str(cust_row["Địa chỉ"])
        st.text_area("Address:", value=address, height=100, disabled=True)
        
        # Contact Person (Ref: Customer_Contact / Col: Customer contact, filter by Cust No)
        # Lưu ý: Tên cột trong file của bạn là 'Customer no'
        f_contact = df_contact[df_contact["Customer no"].astype(str).str.contains(cust_no)]
        contact_list = f_contact["Customer contact"].dropna().tolist() if not f_contact.empty else ["N/A"]
        st.selectbox("Contact Person:", options=contact_list)
        
        # Officer (Ref: Staff / Col: Name)
        officer_list = df_staff["Name"].dropna().tolist()
        st.selectbox("Officer:", options=officer_list)
        
        # Machine Number (Ref: List_of_ machines / Col: Machine No.)
        f_machines = df_machines[df_machines["Customer no"].astype(str).str.contains(cust_no)]
        machine_list = f_machines["Machine No."].dropna().tolist() if not f_machines.empty else ["N/A"]
        st.selectbox("Machine Number:", options=machine_list)
        
        # Offer Date
        offer_date = st.date_input("Offer Date:", value=datetime.now())
        
        # Offer No (Format: Year-Month-0001)
        default_no = f"{offer_date.year}-{offer_date.month:02d}-0001"
        st.text_input("Offer No:", value=default_no)

        # --- Separate Line ---
        st.markdown("---")
        st.subheader("Offer Descriptions")

        # --- B_2: Offer Descriptions ---
        search_input = st.text_input("Search Part Number (Ex: 2024956492;2031956280):")
        
        col_act1, col_act2, _ = st.columns([1.5, 1.5, 4])
        
        if col_act1.button("Add to Cart", type="primary"):
            if search_input:
                codes = [c.strip() for c in search_input.split(';')]
                for code in codes:
                    # Tìm trong SP_List / Col: Part number
                    match = df_sp[df_sp["Part number"].astype(str) == code]
                    if not match.empty:
                        item = match.iloc[0]
                        # Check trùng trong giỏ
                        if not any(d['Part Number'] == code for d in st.session_state.cart):
                            st.session_state.cart.append({
                                "Part Number": str(item["Part number"]),
                                "Part Name": item["Part name"],
                                "Qty": 1,
                                "Unit": item["Unit"],
                                "VAT": item["VAT"],
                                "Unit Price": float(item["Giá bán"]) if not pd.isna(item["Giá bán"]) else 0.0,
                                "% Discount": 0.0
                            })
                    else:
                        st.warning(f"Part Number {code} is not available")
                st.rerun()

        if col_act2.button("Delete Cart"):
            st.session_state.cart = []
            st.rerun()

        # Bảng hiển thị Cart
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            
            # Tính toán cột Amount: (Unit Price * % Discount) / 100 theo yêu cầu
            # Lưu ý: Đây là số tiền ĐƯỢC GIẢM theo công thức của bạn
            df_cart["Amount"] = (df_cart["Unit Price"] * df_cart["% Discount"]) / 100
            
            # Thêm cột số thứ tự
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
                    "Unit Price": st.column_config.NumberColumn(format="%.0f", disabled=True),
                    "Qty": st.column_config.NumberColumn(min_value=1),
                    "% Discount": st.column_config.NumberColumn(min_value=0, max_value=100),
                    "Amount": st.column_config.NumberColumn(format="%.0f", disabled=True),
                    "Delete": st.column_config.CheckboxColumn("Xóa dòng")
                },
                hide_index=True,
                use_container_width=True
            )

            # Cập nhật lại giỏ hàng nếu có thay đổi (Qty, Discount hoặc Delete)
            if not edited_df.equals(df_cart):
                new_cart = edited_df[edited_df["Delete"] == False].drop(columns=["No", "Amount", "Delete"]).to_dict('records')
                st.session_state.cart = new_cart
                st.rerun()

    elif st.session_state.offer_page == "Management":
        st.info("Chức năng quản lý đơn hàng (Order Management) đang chờ thiết kế.")
