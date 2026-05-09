import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re

# 1. Hàm làm sạch mã Part Number
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
    if 'sub_action' not in st.session_state: st.session_state.sub_action = "create"

    # --- SIDEBAR (KHÔI PHỤC ĐẦY ĐỦ) ---
    st.sidebar.title("⚙️ Cấu hình")
    ty_gia = st.sidebar.number_input("Tỷ giá Euro (VND):", value=31000, step=100)
    if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.divider()
    menu_selection = st.sidebar.radio("📂 Danh mục chính:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])

    if menu_selection == "📄 Báo Giá Phụ Tùng":
        # --- 2 NÚT TRÊN CÙNG (KHÔI PHỤC) ---
        col_btn1, col_btn2, _ = st.columns([1, 1, 4])
        if col_btn1.button("➕ Tạo Báo Giá", use_container_width=True, type="primary" if st.session_state.sub_action=="create" else "secondary"):
            st.session_state.sub_action = "create"
        if col_btn2.button("🔍 Tra Cứu", use_container_width=True, type="primary" if st.session_state.sub_action=="search" else "secondary"):
            st.session_state.sub_action = "search"
        
        st.divider()

        if st.session_state.sub_action == "create":
            # --- THÔNG TIN KHÁCH HÀNG (CHỐNG LỖI DATA TRỐNG) ---
            if df_mst is not None:
                r1c1, r1c2 = st.columns(2)
                with r1c1:
                    cust_name = st.selectbox("🎯 Khách hàng:", options=sorted(df_mst['Customer name'].unique()))
                    row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
                    
                    # Fix lỗi Customer No hoặc MST bị trống
                    c_no_raw = row_mst.get('Customer no', row_mst.get('Customer\nno', ''))
                    c_no = str(c_no_raw).split('.')[0] if pd.notna(c_no_raw) else "N/A"
                    mst = str(row_mst.get('Mã số thuế', 'nan'))
                    mst_display = mst if mst != 'nan' else '-'
                    
                    st.info(f"**Cust No:** {c_no} | **MST:** {mst_display}")
                
                with r1c2:
                    f_conts = df_con[df_con.iloc[:, 1].astype(str).str.contains(clean_code(c_no))]
                    list_conts = f_conts.iloc[:, 7].dropna().unique().tolist()
                    st.selectbox("👤 Contact Person:", options=list_conts if list_conts else ["N/A"])
                    
                    # Fix lỗi Địa chỉ bị trống (Tránh crash app)
                    addr = row_mst.get('Địa chỉ', row_mst.get('Full Information customer', ''))
                    addr_str = str(addr) if pd.notna(addr) else "-"
                    st.write(f"📍 {addr_str[:80]}...")

                # Dòng 2: Machine & Người lập (Thẳng hàng)
                r2c1, r2c2 = st.columns(2)
                with r2c1:
                    m_list = df_mac[df_mac.iloc[:, 1].astype(str).str.contains(clean_code(c_no))].iloc[:, -1].tolist()
                    st.selectbox("🛠️ Machine number:", options=m_list if m_list else ["N/A"])
                with r2c2:
                    staff_names = df_staff.iloc[:, 1].tolist() if df_staff is not None else ["Admin"]
                    st.selectbox("✍️ Người lập báo giá:", options=staff_names)

            st.divider()

            # --- TÌM KIẾM ---
            st.subheader("🔍 Tìm Part Number")
            input_search = st.text_input("Dán mã vào đây:", placeholder="Ví dụ: 4007010482; 2024956492...")
            
            if st.button("🛒 Thêm vào giỏ hàng", type="primary"):
                if input_search:
                    codes = [clean_code(c) for c in input_search.split(';') if c.strip()]
                    df_sp['CLEAN_PN'] = df_sp.iloc[:, 1].apply(clean_code)
                    for code in codes:
                        match = df_sp[df_sp['CLEAN_PN'] == code]
                        if not match.empty:
                            item = match.iloc[0]
                            # Lấy giá và VAT an toàn
                            price = item.iloc[18] if len(item) > 18 else 0
                            vat_raw = item.iloc[13] if len(item) > 13 else 0.08
                            vat_display = f"{int(float(vat_raw)*100)}%" if pd.notna(vat_raw) else "8%"
                            
                            st.session_state.cart.append({
                                "Part Number": item.iloc[1],
                                "Part name": item.iloc[4],
                                "Qty": 1,
                                "Unit": item.iloc[7],
                                "VAT": vat_display,
                                "Unit Price": float(price) if pd.notna(price) else 0.0
                            })
                    st.rerun()

            # --- BẢNG GIỎ HÀNG ---
            if st.session_state.cart:
                df_cart = pd.DataFrame(st.session_state.cart)
                df_cart.insert(0, 'No', range(1, len(df_cart) + 1))
                st.data_editor(
                    df_cart,
                    column_config={"Unit Price": st.column_config.NumberColumn("Giá bán", format="%,d")},
                    use_container_width=True, hide_index=True
                )
                if st.button("🗑️ Xóa hết bảng"):
                    st.session_state.cart = []
                    st.rerun()

                # --- 2 NÚT BẤM DƯỚI CÙNG ---
                st.write("")
                b1, b2, _ = st.columns([1.5, 1.5, 4])
                b1.button("💾 Lưu báo giá", use_container_width=True)
                b2.button("✅ Xác nhận đặt hàng", use_container_width=True)

    elif menu_selection == "🗂️ Master Data":
        st.header("🗂️ Master Data - SP List")
        st.dataframe(df_sp, use_container_width=True)

if __name__ == "__main__":
    main()
