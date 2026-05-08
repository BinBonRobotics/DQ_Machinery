import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re

# 1. Hàm làm sạch mã Part Number để so sánh chính xác
def clean_code(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).split('.')[0].strip()
    return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

@st.cache_data(ttl=60)
def load_all_data(url):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_sp = conn.read(spreadsheet=url, worksheet="SP List", ttl=0)
        df_mst = conn.read(spreadsheet=url, worksheet="Customer_MST", ttl=0)
        df_con = conn.read(spreadsheet=url, worksheet="Customer_Contact", ttl=0)
        df_mac = conn.read(spreadsheet=url, worksheet="List of machines", ttl=0)
        df_staff = conn.read(spreadsheet=url, worksheet="Staff", ttl=0)
        return df_sp, df_mst, df_con, df_mac, df_staff
    except:
        return None, None, None, None, None

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
    df_sp, df_mst, df_con, df_mac, df_staff = load_all_data(url)

    if 'cart' not in st.session_state: st.session_state.cart = []

    st.header("📄 Báo Giá Phụ Tùng")

    # --- KHU VỰC THÔNG TIN KHÁCH HÀNG (CÂN BẰNG THẲNG HÀNG) ---
    if df_mst is not None:
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            cust_name = st.selectbox("🎯 Khách hàng:", options=sorted(df_mst['Customer name'].unique()))
            row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
            c_no = str(row_mst.get('Customer\nno', row_mst.get('Customer no', '')))
            st.info(f"**Cust No:** {c_no} | **MST:** {row_mst.get('Mã số thuế', '')}")
        
        with row1_col2:
            f_conts = df_con[df_con.iloc[:, 1].astype(str).str.contains(clean_code(c_no))]
            list_conts = f_conts.iloc[:, 7].dropna().unique().tolist()
            selected_c = st.selectbox("👤 Contact Person:", options=list_conts if list_conts else ["N/A"])
            st.write(f"📍 {row_mst.get('Địa chỉ', '')[:70]}...")

        # Dòng 2: Machine và Người lập (Thẳng hàng tuyệt đối)
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
    input_search = st.text_input("Dán mã vào đây (ví dụ: 4007010482; 2024956492...)", key="search_input")
    
    if st.button("🛒 Thêm vào giỏ hàng", type="primary"):
        if input_search:
            codes_to_find = [clean_code(c) for c in input_search.split(';') if c.strip()]
            df_sp['CLEAN_PN'] = df_sp.iloc[:, 1].apply(clean_code)
            
            for code in codes_to_find:
                match = df_sp[df_sp['CLEAN_PN'] == code]
                if not match.empty:
                    item = match.iloc[0]
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
                    st.error(f"❌ Không thấy mã: {code}")
            st.rerun()

    # --- BẢNG GIỎ HÀNG (CÓ CỘT SỐ THỨ TỰ "NO") ---
    if st.session_state.cart:
        st.markdown("### 📋 Danh sách Part đã chọn")
        df_cart = pd.DataFrame(st.session_state.cart)
        
        # Thêm cột No vào đầu bảng
        df_cart.insert(0, 'No', range(1, len(df_cart) + 1))
        
        st.data_editor(
            df_cart,
            column_config={
                "No": st.column_config.NumberColumn("No", width="small"),
                "Unit Price": st.column_config.NumberColumn("Giá bán", format="%,d"),
                "Qty": st.column_config.NumberColumn("Qty", min_value=1)
            },
            use_container_width=True,
            hide_index=True,
            key="main_table"
        )
        
        if st.button("🗑️ Xóa hết bảng"):
            st.session_state.cart = []
            st.rerun()

        # --- 2 NÚT BẤM DƯỚI CÙNG ---
        st.markdown("<br>", unsafe_allow_html=True)
        btn_col1, btn_col2, btn_spacer = st.columns([1.5, 1.5, 4])
        with btn_col1:
            if st.button("💾 Lưu báo giá", use_container_width=True):
                st.info("Chức năng Lưu đang chờ lệnh tiếp theo của bạn.")
        with btn_col2:
            if st.button("✅ Xác nhận đặt hàng", use_container_width=True):
                st.success("Chức năng Đặt hàng đang chờ lệnh tiếp theo của bạn.")

if __name__ == "__main__":
    main()
