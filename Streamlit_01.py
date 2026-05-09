import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# 1. Hàm làm sạch mã Part Number để tìm kiếm chính xác
def clean_code(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).split('.')[0].strip()
    return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

# 2. Hàm đọc dữ liệu dùng Service Account (JSON trong Secrets)
@st.cache_data(ttl=60)
def load_all_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
        
        # Đọc các tab cũ
        df_sp = conn.read(spreadsheet=url, worksheet="SP List")
        df_mst = conn.read(spreadsheet=url, worksheet="Customer_MST")
        df_con = conn.read(spreadsheet=url, worksheet="Customer_Contact")
        df_mac = conn.read(spreadsheet=url, worksheet="List of machines")
        df_staff = conn.read(spreadsheet=url, worksheet="Staff")
        
        # Đọc các tab mới bạn vừa tạo (Nếu chưa có dữ liệu sẽ trả về DF trống)
        try:
            df_off_desc = conn.read(spreadsheet=url, worksheet="offer description")
            df_off_head = conn.read(spreadsheet=url, worksheet="offer header")
            df_off_track = conn.read(spreadsheet=url, worksheet="offer tracking")
        except:
            df_off_desc = df_off_head = df_off_track = pd.DataFrame()

        return df_sp, df_mst, df_con, df_mac, df_staff, df_off_desc, df_off_head, df_off_track
    except Exception as e:
        st.error(f"❌ Lỗi kết nối Google Sheets: {e}")
        return [None] * 8

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    # Load dữ liệu từ 8 tabs
    data = load_all_data()
    df_sp, df_mst, df_con, df_mac, df_staff, df_off_desc, df_off_head, df_off_track = data

    if df_mst is None:
        st.warning("⚠️ Đang chờ kết nối dữ liệu từ Google Sheets...")
        return

    # Khởi tạo session state
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'sub_action' not in st.session_state: st.session_state.sub_action = "create"

    # --- SIDEBAR ---
    st.sidebar.title("⚙️ Cấu hình")
    ty_gia = st.sidebar.number_input("Tỷ giá Euro (VND):", value=31000, step=100)
    if st.sidebar.button("🔄 Clear Cache & Reload", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    menu_selection = st.sidebar.radio("📂 Danh mục chính:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])

    if menu_selection == "📄 Báo Giá Phụ Tùng":
        col_btn1, col_btn2, _ = st.columns([1.5, 2, 3])
        if col_btn1.button("➕ Tạo Báo Giá", use_container_width=True, type="primary" if st.session_state.sub_action=="create" else "secondary"):
            st.session_state.sub_action = "create"
        if col_btn2.button("🔍 Order Management", use_container_width=True, type="primary" if st.session_state.sub_action=="search" else "secondary"):
            st.session_state.sub_action = "search"
        
        st.divider()

        if st.session_state.sub_action == "create":
            # --- PHẦN THÔNG TIN KHÁCH HÀNG (Sửa lỗi không thấy đâu) ---
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                # Tìm đúng tên cột 'Customer name' trong file bạn gửi
                cust_options = sorted(df_mst['Customer name'].dropna().unique())
                cust_name = st.selectbox("🎯 Khách hàng:", options=cust_options)
                
                # Lọc dữ liệu khách hàng
                row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
                
                # Xử lý tên cột có dấu xuống dòng 'Customer\nno'
                c_no_val = row_mst.get('Customer no', row_mst.get('Customer\nno', ''))
                c_no = str(c_no_val).split('.')[0] if pd.notna(c_no_val) else "N/A"
                mst = str(row_mst.get('Mã số thuế', '-'))
                st.info(f"**Cust No:** {c_no} | **MST:** {mst}")
            
            with r1c2:
                # Lọc Contact Person dựa trên Customer No
                f_conts = df_con[df_con.iloc[:, 1].astype(str).str.contains(clean_code(c_no))] if df_con is not None else pd.DataFrame()
                # Cột Customer contact là cột thứ 8 (index 7)
                list_conts = f_conts.iloc[:, 7].dropna().unique().tolist() if not f_conts.empty else []
                st.selectbox("👤 Contact Person:", options=list_conts if list_conts else ["N/A"])
                
                addr = row_mst.get('Địa chỉ', row_mst.get('Full Information customer', '-'))
                st.markdown(f"📍 **Địa chỉ:** {str(addr)}")

            r2c1, r2c2 = st.columns(2)
            with r2c1:
                # Lọc Machine Number dựa trên Customer No (Cột index 4 trong tab machines)
                f_macs = df_mac[df_mac.iloc[:, 1].astype(str).str.contains(clean_code(c_no))] if df_mac is not None else pd.DataFrame()
                list_macs = f_macs.iloc[:, 4].dropna().unique().tolist() if not f_macs.empty else []
                st.selectbox("🤖 Machine Number:", options=list_macs if list_macs else ["N/A"])
            
            with r2c2:
                list_staff = df_staff['Name'].dropna().unique().tolist() if 'Name' in df_staff.columns else ["Admin"]
                st.selectbox("✍️ Người lập báo giá:", options=list_staff)

            st.divider()
            # --- PHẦN TÌM PHỤ TÙNG ---
            st.subheader("🔍 Tìm Part Number")
            input_search = st.text_input("Nhập mã (ví dụ: 3608080970; 4007010482...):")
            
            if st.button("🛒 Thêm vào giỏ hàng", type="primary"):
                if input_search:
                    codes = [clean_code(c) for c in input_search.split(';') if c.strip()]
                    df_sp['CLEAN_PN'] = df_sp['Part number'].apply(clean_code)
                    for code in codes:
                        match = df_sp[df_sp['CLEAN_PN'] == code]
                        if not match.empty:
                            item = match.iloc[0]
                            # Lấy giá bán (Giá bán - Cột index 18)
                            price = item.get('Giá bán', 0)
                            st.session_state.cart.append({
                                "Part Number": item['Part number'], 
                                "Part name": item['Part name'],
                                "Qty": 1, "Unit": item['Unit'], "VAT": "8%",
                                "Unit Price": float(price) if pd.notna(price) else 0.0,
                                "%Dist": 0.0, "Xoá": False
                            })
                    st.rerun()

            if st.session_state.cart:
                df_cart = pd.DataFrame(st.session_state.cart)
                df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)
                st.data_editor(df_cart, use_container_width=True, hide_index=True)
                st.button("💾 Lưu báo giá (vào tab offer description)", use_container_width=True)

        elif st.session_state.sub_action == "search":
            st.subheader("📋 Order Management")
            t1, t2, t3 = st.tabs(["Offers", "Tracking", "Reports"])
            with t1: st.dataframe(df_off_head)
            with t2: st.dataframe(df_off_track)

    elif menu_selection == "🗂️ Master Data":
        st.dataframe(df_sp)

if __name__ == "__main__":
    main()
