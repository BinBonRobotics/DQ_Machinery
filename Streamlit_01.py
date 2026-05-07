import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import math

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=60)
def load_all_data(url_link):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_sp = conn.read(spreadsheet=url_link, worksheet="SP List", ttl=0)
        df_mst = conn.read(spreadsheet=url_link, worksheet="Customer_MST", ttl=0)
        df_contact = conn.read(spreadsheet=url_link, worksheet="Customer_Contact", ttl=0)
        df_machines = conn.read(spreadsheet=url_link, worksheet="List of machines", ttl=0)
        df_staff = conn.read(spreadsheet=url_link, worksheet="Staff", ttl=0)
        
        # Làm sạch tên cột
        for df in [df_sp, df_mst, df_contact, df_machines, df_staff]:
            df.columns = [c.replace('\n', ' ').strip() for c in df.columns]
        return df_sp, df_mst, df_contact, df_machines, df_staff
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None, None, None, None, None

def format_clean_str(val):
    """Biến mọi giá trị thành chuỗi sạch để so sánh chính xác"""
    if pd.isna(val): return ""
    # Loại bỏ .0 nếu là số, bỏ khoảng trắng đầu cuối
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    # SIDEBAR
    st.sidebar.title("⚙️ HỆ THỐNG D&Q")
    menu_selection = st.sidebar.radio("📂 Danh mục chính:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])
    st.sidebar.divider()
    ty_gia_input = st.sidebar.number_input("Tỷ giá Euro:", value=31000, step=100)
    
    if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'sub_action' not in st.session_state: st.session_state.sub_action = None

    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
    df_sp_raw, df_mst, df_contact, df_machines, df_staff = load_all_data(url)

    if df_sp_raw is not None:
        if menu_selection == "📄 Báo Giá Phụ Tùng":
            col_btn1, col_btn2, _, _, _ = st.columns(5)
            with col_btn1:
                if st.button("➕ Tạo Báo Giá", use_container_width=True): st.session_state.sub_action = "create"
            with col_btn2:
                if st.button("🔍 Tra Cứu", use_container_width=True): st.session_state.sub_action = "search"

            if st.session_state.sub_action == "create":
                st.divider()
                
                # --- KHỐI THÔNG TIN KHÁCH HÀNG ---
                # Hàng 1: Customer Name & Contact Person
                row1_col1, row1_col2 = st.columns(2)
                with row1_col1:
                    customer_list = sorted(df_mst['Customer name'].unique())
                    selected_customer = st.selectbox("🎯 Chọn khách hàng:", options=customer_list)
                    cust_info = df_mst[df_mst['Customer name'] == selected_customer].iloc[0]
                    c_no = format_clean_str(cust_info['Customer no'])
                    st.write(f"**Cust No:** {c_no} | **MST:** {format_clean_str(cust_info['Mã số thuế'])}")
                
                with row1_col2:
                    df_contact['C_NO_STR'] = df_contact['Customer no'].apply(format_clean_str)
                    f_contacts = df_contact[df_contact['C_NO_STR'] == c_no]
                    cont_options = f_contacts['Customer contact'].dropna().unique().tolist()
                    selected_contact = st.selectbox("👤 Contact Person:", options=cont_options if cont_options else ["N/A"])
                    
                    if cont_options and selected_contact != "N/A":
                        c_detail = f_contacts[f_contacts['Customer contact'] == selected_contact].iloc[0]
                        st.write(f"📞 {c_detail.get('Phone', '-')} | ✉️ {c_detail.get('Email', '-')}")
                    else:
                        st.write("📞 - | ✉️ -")

                # Hàng 2: Machine Number & Người lập (Đảm bảo thẳng hàng)
                row2_col1, row2_col2 = st.columns(2)
                with row2_col1:
                    m_list = df_machines[df_machines['Customer no'].apply(format_clean_str) == c_no]['Customer Machine'].tolist()
                    st.selectbox("🛠️ Machine number:", options=m_list if m_list else ["N/A"])
                
                with row2_col2:
                    staff_list = df_staff['Name'].tolist() if df_staff is not None else ["Admin"]
                    st.selectbox("✍️ Người lập báo giá:", options=staff_list)

                # Địa chỉ
                st.markdown(f'''
                    <div style="margin-top:10px; padding:12px; background-color:#f8f9fa; border-left:5px solid #ff4b4b; border-radius:4px;">
                        <b>📍 Địa chỉ:</b> {cust_info["Full Information customer"]}
                    </div>
                ''', unsafe_allow_html=True)
                st.divider()

                # --- TÌM KIẾM PHỤ TÙNG ---
                st.subheader("🔍 Tìm Part Number")
                col_search, col_add = st.columns([4, 1])
                with col_search:
                    part_search = st.text_input("Nhập mã phụ tùng:", placeholder="Ví dụ: 3608080970")
                
                if part_search:
                    # Làm sạch giá trị nhập vào
                    s_input = format_clean_str(part_search)
                    # Tạo cột so sánh đã được làm sạch từ SP List
                    df_sp_raw['PN_COMP'] = df_sp_raw['Part number'].apply(format_clean_str)
                    
                    match = df_sp_raw[df_sp_raw['PN_COMP'] == s_input]
                    
                    if not match.empty:
                        item = match.iloc[0]
                        with col_add:
                            st.write("##")
                            if st.button("➕ Thêm vào bảng", use_container_width=True, type="primary"):
                                st.session_state.cart.append({
                                    "Part Number": item['Part number'],
                                    "Part name": item['Part name'],
                                    "Qty": 1,
                                    "Unit": item['Unit'],
                                    "VAT": item['VAT'],
                                    "Unit Price": item['Giá bán']
                                })
                                st.toast(f"Đã thêm: {item['Part number']}")
                    else:
                        st.error(f"❌ Không tìm thấy mã '{part_search}'. Vui lòng kiểm tra lại tab SP List.")

                # --- BẢNG DANH SÁCH ---
                st.markdown("### 📋 Danh sách phụ tùng")
                if st.session_state.cart:
                    df_cart = pd.DataFrame(st.session_state.cart)
                    df_cart.insert(0, 'No', range(1, len(df_cart) + 1))
                    st.data_editor(df_cart, use_container_width=True, hide_index=True, key="editor_final")
                    if st.button("🗑️ Xoá toàn bộ bảng"):
                        st.session_state.cart = []
                        st.rerun()

                # Nút điều khiển dưới cùng
                st.markdown("<br>" * 10, unsafe_allow_html=True)
                cs1, cs2, _ = st.columns([1.5, 1.5, 5])
                cs1.button("💾 Lưu Báo Giá", use_container_width=True)
                cs2.button("🛒 Đặt Hàng", use_container_width=True)

        elif menu_selection == "🗂️ Master Data":
            st.header("🗂️ Master Data")
            st.dataframe(df_sp_raw, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
