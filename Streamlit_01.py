import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re

# 1. Hàm làm sạch mã để so sánh (Xóa mọi ký tự không phải chữ và số)
def clean_code(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).split('.')[0] # Bỏ phần .0 nếu có
    return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

@st.cache_data(ttl=60)
def load_data(url):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_sp = conn.read(spreadsheet=url, worksheet="SP List", ttl=0)
    df_mst = conn.read(spreadsheet=url, worksheet="Customer_MST", ttl=0)
    df_con = conn.read(spreadsheet=url, worksheet="Customer_Contact", ttl=0)
    df_mac = conn.read(spreadsheet=url, worksheet="List of machines", ttl=0)
    df_staff = conn.read(spreadsheet=url, worksheet="Staff", ttl=0)
    return df_sp, df_mst, df_con, df_mac, df_staff

def main():
    st.set_page_config(layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
    df_sp, df_mst, df_con, df_mac, df_staff = load_data(url)

    if 'cart' not in st.session_state: st.session_state.cart = []

    st.title("📄 Báo Giá Phụ Tùng")

    # --- KHU VỰC THÔNG TIN (FIX THẲNG HÀNG 100%) ---
    col1, col2 = st.columns(2)
    with col1:
        cust = st.selectbox("🎯 Khách hàng:", options=sorted(df_mst['Customer name'].unique()))
        c_no = str(df_mst[df_mst['Customer name'] == cust].iloc[0]['Customer no'])
        st.info(f"Cust No: {c_no}")
        # Ô vàng 1
        st.selectbox("🛠️ Machine number:", options=df_mac[df_mac['Customer no'].astype(str).str.contains(c_no)]['Customer Machine'].tolist() or ["N/A"])

    with col2:
        contact_list = df_con[df_con['Customer no'].astype(str).str.contains(c_no)]['Customer contact'].unique().tolist()
        st.selectbox("👤 Contact Person:", options=contact_list or ["N/A"])
        st.write("") # Tạo khoảng đệm
        st.write("") # Tạo khoảng đệm
        # Ô vàng 2 (Nằm cùng hàng với Machine number do cùng cấu trúc cột)
        st.selectbox("✍️ Người lập báo giá:", options=df_staff['Name'].tolist() if df_staff is not None else ["Admin"])

    st.divider()

    # --- KHU VỰC TÌM KIẾM (SO SÁNH TRỰC TIẾP CỘT B) ---
    st.subheader("🔍 Nhập mã Part Number")
    search_input = st.text_input("Dán danh sách mã cách nhau bởi dấu ;", placeholder="Ví dụ: 4007010482;2024956492")
    
    if st.button("🛒 Thêm vào bảng", type="primary"):
        if search_input:
            input_codes = [clean_code(c) for c in search_input.split(';') if c.strip()]
            
            # Chuẩn bị cột B để so sánh
            # Giả sử cột B là cột thứ 2 (index 1), hoặc bạn dùng đúng tên 'Part number'
            df_sp['MATCH_KEY'] = df_sp['Part number'].apply(clean_code)
            
            found_any = False
            for code in input_codes:
                result = df_sp[df_sp['MATCH_KEY'] == code]
                if not result.empty:
                    item = result.iloc[0]
                    # Lấy đúng tên cột trong file của bạn
                    st.session_state.cart.append({
                        "Part Number": item['Part number'],
                        "Part name": item['Part name'],
                        "Qty": 1,
                        "Unit": item['Unit'],
                        "VAT": "8%", # Hoặc lấy từ cột VAT nếu có
                        "Unit Price": float(item['Giá bán']) if 'Giá bán' in item else 0
                    })
                    found_any = True
                else:
                    st.warning(f"Không tìm thấy mã: {code}")
            
            if found_any: st.rerun()

    # --- BẢNG HIỂN THỊ ---
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
        if st.button("🗑️ Xóa bảng"):
            st.session_state.cart = []
            st.rerun()

if __name__ == "__main__":
    main()
