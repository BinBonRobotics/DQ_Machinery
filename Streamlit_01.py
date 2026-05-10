import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Spare Part Management", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

# Hàm format dữ liệu thành chuỗi chuẩn (giữ số 0 đầu)
def clean_str(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).strip()
    return s.split('.')[0] if '.' in s and s.split('.')[1] == '0' else s

# --- 2. TẢI DỮ LIỆU ---
@st.cache_data(ttl=600)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Ép kiểu string ngay từ khi đọc để bảo vệ số 0 ở Tax Code và Customer No
    mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST", dtype=str)
    contact = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact", dtype=str)
    staff = conn.read(spreadsheet=SHEET_URL, worksheet="Staff", dtype=str)
    machines = conn.read(spreadsheet=SHEET_URL, worksheet="List_of_ machines", dtype=str)
    sp_list = conn.read(spreadsheet=SHEET_URL, worksheet="SP List", dtype=str)
    return mst, contact, staff, machines, sp_list

df_mst, df_contact, df_staff, df_mac, df_sp = load_data()

# --- 3. SIDE MENU (A_1) ---
with st.sidebar:
    st.header("📋 MENU")
    menu_option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# --- 4. KHỞI TẠO SESSION STATE ---
if "cart" not in st.session_state: st.session_state.cart = []
if "offer_mode" not in st.session_state: st.session_state.offer_mode = "new"

# --- 5. CHƯƠNG TRÌNH CHÍNH (A_2) ---
if menu_option == "Spare Part Quotation":
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("➕ New Spare Part Offer", use_container_width=True):
            st.session_state.offer_mode = "new"
    with col_btn2:
        if st.button("📋 Order Management", use_container_width=True):
            st.session_state.offer_mode = "manage"

    if st.session_state.offer_mode == "new":
        st.divider()
        # --- B_1: OFFER HEADER ---
        # Customer Name (Col C)
        cust_names = df_mst.iloc[:, 2].dropna().unique()
        selected_cust = st.selectbox("👤 Customer Name:", options=cust_names)
        
        cust_row = df_mst[df_mst.iloc[:, 2] == selected_cust].iloc[0]
        
        # Customer No (Col B) & Tax Code (Col F) - Chuyển sang String sạch
        c_no = clean_str(cust_row.iloc[1])
        tax_code = clean_str(cust_row.iloc[5])
        
        st.text_input("🆔 Customer No:", value=c_no, disabled=True)
        st.text_input("📑 Tax Code:", value=tax_code, disabled=True)
        st.text_area("📍 Address:", value=str(cust_row.iloc[4]), disabled=True, height=70)

        col_l, col_r = st.columns(2)
        with col_l:
            # Contact Person (Tab Contact / Col H - Index 7 / Match Col B - Index 1)
            contacts = df_contact[df_contact.iloc[:, 1].apply(clean_str) == c_no].iloc[:, 7].dropna().unique()
            st.selectbox("📞 Contact Person:", options=contacts if len(contacts)>0 else ["N/A"])
            
            # Officer (Tab Staff / Col B - Index 1)
            officers = df_staff.iloc[:, 1].dropna().unique()
            st.selectbox("👨‍💼 Officer:", options=officers)

        with col_r:
            # Machine Number (Tab Machines / Col O - Index 14 / Match Col B - Index 1)
            try:
                macs = df_mac[df_mac.iloc[:, 1].apply(clean_str) == c_no].iloc[:, 14].dropna().unique()
            except: macs = []
            st.selectbox("🤖 Machine Number:", options=macs if len(macs)>0 else ["N/A"])
            
            st.date_input("📅 Offer Date:", value=datetime.now())

        # Offer No
        default_off_no = f"{datetime.now().year}-{datetime.now().month:02d}-0001"
        st.text_input("🆔 Offer No:", value=default_off_no)

        # --- B_2: OFFER DESCRIPTIONS ---
        st.markdown("---")
        st.subheader("🛒 Offer Descriptions")
        
        search_input = st.text_input("🔍 Search Part Number (seperated by ';'):", placeholder="2024956492;2031956280...")
        
        c_act1, c_act2, _ = st.columns([1, 1, 4])
        with c_act1:
            if st.button("➕ Add to Cart", use_container_width=True):
                if search_input:
                    parts = [p.strip() for p in search_input.split(";")]
                    for p in parts:
                        match = df_sp[df_sp.iloc[:, 1].apply(clean_str) == p]
                        if not match.empty:
                            row = match.iloc[0]
                            # Kiểm tra xem đã có trong giỏ hàng chưa
                            if not any(item['Part Number'] == p for item in st.session_state.cart):
                                st.session_state.cart.append({
                                    "Part Number": clean_str(row.iloc[1]),
                                    "Part Name": row.iloc[4], # Col E
                                    "Qty": 1,
                                    "Unit": row.iloc[7], # Col H
                                    "VAT": row.iloc[12], # Col M
                                    "Unit Price": float(row.iloc[18]) if row.iloc[18] else 0, # Col S
                                    "Discount": 0.0
                                })
                        else:
                            st.warning(f"Part Number {p} is not available")
        
        with c_act2:
            if st.button("🗑️ Delete Cart", use_container_width=True):
                st.session_state.cart = []
                st.rerun()

        # Hiển thị bảng giỏ hàng
        if st.session_state.cart:
            final_data = []
            for idx, item in enumerate(st.session_state.cart):
                # Tính toán Amount
                amount = (item["Unit Price"] * (100 - item["Discount"])) / 100
                
                final_data.append({
                    "No": idx + 1,
                    "Part Number": item["Part Number"],
                    "Part Name": item["Part Name"],
                    "Qty": item["Qty"],
                    "Unit": item["Unit"],
                    "VAT": item["VAT"],
                    "Unit Price": f"{item['Unit Price']:,.0f}",
                    "% Discount": f"{item['Discount']}%",
                    "Amount": f"{amount:,.0f}"
                })
            
            st.table(pd.DataFrame(final_data))
            st.info("💡 Lưu ý: Chức năng chỉnh sửa trực tiếp trên bảng Qty và Discount sẽ được tích hợp ở bước tiếp theo.")

    elif st.session_state.offer_mode == "manage":
        st.subheader("📋 Order Management")
        st.write("Dữ liệu quản lý đơn hàng sẽ hiển thị tại đây.")

else:
    st.title("🛠️ Service Quotation")
    st.write("Chức năng đang được cập nhật...")
