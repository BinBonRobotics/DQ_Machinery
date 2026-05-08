import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re

# 1. Hàm làm sạch mã Part Number để so sánh chính xác
def clean_code(val):
    if pd.isna(val) or val == "": return ""
    # Lấy phần số, bỏ .0, bỏ mọi ký tự lạ
    s = str(val).split('.')[0].strip()
    return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

@st.cache_data(ttl=60)
def load_all_data(url):
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Đọc raw data, không ép kiểu để tránh mất số 0 đầu
    df_sp = conn.read(spreadsheet=url, worksheet="SP List", ttl=0)
    df_mst = conn.read(spreadsheet=url, worksheet="Customer_MST", ttl=0)
    df_con = conn.read(spreadsheet=url, worksheet="Customer_Contact", ttl=0)
    df_mac = conn.read(spreadsheet=url, worksheet="List of machines", ttl=0)
    df_staff = conn.read(spreadsheet=url, worksheet="Staff", ttl=0)
    return df_sp, df_mst, df_con, df_mac, df_staff

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
    df_sp, df_mst, df_con, df_mac, df_staff = load_all_data(url)

    if 'cart' not in st.session_state: st.session_state.cart = []

    st.sidebar.title("⚙️ HỆ THỐNG D&Q")
    if st.sidebar.button("🔄 Làm mới dữ liệu"):
        st.cache_data.clear()
        st.rerun()

    st.header("📄 Báo Giá Phụ Tùng")

    # --- KHU VỰC THÔNG TIN KHÁCH HÀNG (CÂN BẰNG THẲNG HÀNG) ---
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        cust_name = st.selectbox("🎯 Khách hàng:", options=sorted(df_mst['Customer name'].unique()))
        row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
        c_no = str(row_mst.get('Customer\nno', row_mst.get('Customer no', '')))
        st.info(f"**Cust No:** {c_no} | **MST:** {row_mst.get('Mã số thuế', '')}")
    
    with row1_col2:
        f_conts = df_con[df_con.iloc[:, 1].astype(str).str.contains(clean_code(c_no))]
        list_conts = f_conts.iloc[:, 7].dropna().unique().tolist() # Cột Customer contact
        selected_c = st.selectbox("👤 Contact Person:", options=list_conts if list_conts else ["N/A"])
        st.write(f"📍 {row_mst.get('Địa chỉ', '')[:50]}...")

    # Dòng 2: Machine và Người lập (Ép thẳng hàng)
    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        m_list = df_mac[df_mac.iloc[:, 1].astype(str).str.contains(clean_code(c_no))].iloc[:, -1].tolist()
        st.selectbox("🛠️ Machine number:", options=m_list if m_list else ["N/A"])
    with row2_col2:
        staff_names = df_staff.iloc[:, 1].tolist() if df_staff is not None else ["Admin"]
        st.selectbox("✍️ Người lập báo giá:", options=staff_names)

    st.divider()

    # --- KHU VỰC TÌM KIẾM ---
    st.subheader("🔍 Tìm Part Number")
    input_search = st.text_input("Dán mã vào đây (cách nhau bởi dấu ;)", placeholder="4007010482; 2024956492...")
    
    if st.button("🛒 Thêm vào giỏ hàng", type="primary"):
        if input_search:
            codes_to_find = [clean_code(c) for c in input_search.split(';') if c.strip()]
            
            # Tạo cột sạch để so sánh (Cột B - Part number)
            df_sp['CLEAN_PN'] = df_sp.iloc[:, 1].apply(clean_code)
            
            for code in codes_to_find:
                match = df_sp[df_sp['CLEAN_PN'] == code]
                if not match.empty:
                    item = match.iloc[0]
                    # Lấy giá bán (Cột S - index 18) hoặc cột có tên tương ứng
                    price = item.iloc[18] if len(item) > 18 else 0
                    
                    st.session_state.cart.append({
                        "Part Number": item.iloc[1],
                        "Part name": item.iloc[4],
                        "Qty": 1,
                        "Unit": item.iloc[7],
                        "VAT": "8%",
                        "Unit Price": float(price) if pd.notna(price) else 0.0
                    })
                else:
                    st.error(f"Không thấy mã: {code}")
            st.rerun()

    # --- BẢNG GIỎ HÀNG ---
    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        st.data_editor(
            df_cart,
            column_config={
                "Unit Price": st.column_config.NumberColumn("Giá bán", format="%,d"),
            },
            use_container_width=True,
            hide_index=True
        )
        if st.button("🗑️ Xóa hết"):
            st.session_state.cart = []
            st.rerun()

if __name__ == "__main__":
    main()
