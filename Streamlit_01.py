import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=3600)
def load_data(url_link, sheet_name):
    """Tải dữ liệu từ Google Sheets"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=url_link, worksheet=sheet_name, ttl=0)
        # Xóa khoảng trắng thừa ở tên cột
        data.columns = data.columns.str.strip()
        return data
    except Exception as e:
        st.error(f"❌ Lỗi khi tải Sheet '{sheet_name}': {e}")
        return None

def chuc_nang_dang_nhap(df_user):
    """Xử lý giao diện và logic đăng nhập"""
    st.markdown("---")
    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        with st.form("login_form"):
            user_email = st.text_input("Địa chỉ Email đăng nhập")
            pass_input = st.text_input("Mật khẩu", type="password")
            if st.form_submit_button("Xác nhận Đăng nhập"):
                if user_email and pass_input:
                    # Kiểm tra cột 'email' và 'password' trong sheet members
                    user_data = df_user[(df_user['email'] == user_email.strip()) & 
                                        (df_user['password'] == pass_input.strip())]
                    if not user_data.empty:
                        st.session_state['logged_in'] = True
                        st.session_state['display_name'] = user_data.iloc[0]['name']
                        st.session_state['user_role'] = user_data.iloc[0]['role']
                        st.rerun()
                    else:
                        st.error("Sai tài khoản hoặc mật khẩu!")

def chuc_nang_tra_cuu_vat_tu(df_vattu):
    """Giao diện tra cứu phụ tùng"""
    st.header("🔍 Quản lý Phụ tùng")
    col_search, _ = st.columns([2, 6])
    with col_search:
        search_query = st.text_input("Nhập Part numbers:", placeholder="Mã 1; Mã 2...")
    
    if search_query:
        list_ma = [s.strip() for s in search_query.replace(',', ';').split(';') if s.strip()]
        # Lọc theo cột 'part number' từ sheet SP-List
        result = df_vattu[df_vattu['part number'].astype(str).isin(list_ma)]
        if not result.empty:
            st.table(result)
        else:
            st.warning("❌ Không tìm thấy mã.")
    else:
        st.dataframe(df_vattu, use_container_width=True)

def chuc_nang_bao_gia(df_vattu, df_customer):
    """Giao diện tạo báo giá với layout tối ưu"""
    st.header("📄 Tạo Báo giá Phụ tùng")
    
    if df_customer is None:
        st.error("Không thể tải dữ liệu khách hàng.")
        return

    st.subheader("1. Thông tin khách hàng")
    
    # BƯỚC 1: Làm nhỏ thanh chọn khách hàng [2:6] và dùng cột 'Customer-name'
    col_select, col_empty = st.columns([2, 6])
    with col_select:
        list_customers = sorted(df_customer['Customer-name'].dropna().unique().tolist())
        selected_customer = st.selectbox("Chọn khách hàng:", ["-- Chọn khách hàng --"] + list_customers)

    if selected_customer != "-- Chọn khách hàng --":
        # Lấy dữ liệu của khách hàng đã chọn
        cus_info = df_customer[df_customer['Customer-name'] == selected_customer]
        
        # Hiển thị chi tiết (Customer no, Tax Code, Address...)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Customer no:", value=str(cus_info.iloc[0]['Customer no']), disabled=True)
            list_m_type = sorted(cus_info['Machine-Type'].dropna().unique().tolist())
            selected_m_type = st.selectbox("Machine Type:", list_m_type)
        
        with col2:
            st.text_input("Tax Code:", value=str(cus_info.iloc[0]['Tax Code']), disabled=True)
            list_m_no = sorted(cus_info[cus_info['Machine-Type'] == selected_m_type]['Machine No'].dropna().unique().tolist())
            selected_m_no = st.selectbox("Machine No:", list_m_no)
            
        with col3:
            st.text_area("Address:", value=str(cus_info.iloc[0]['Address']), disabled=True, height=100)

        st.divider()
        st.subheader("2. Chọn phụ tùng vào Offer")
        
        if 'cart' not in st.session_state:
            st.session_state['cart'] = []

        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            part_input = st.text_input("Nhập mã phụ tùng:")
        with c2:
            qty_input = st.number_input("Số lượng:", min_value=1, value=1)
        with c3:
            st.write("##")
            if st.button("➕ Thêm"):
                part_data = df_vattu[df_vattu['part number'].astype(str) == part_input.strip()]
                if not part_data.empty:
                    st.session_state['cart'].append({
                        'Part No': part_input,
                        'Description': part_data.iloc[0]['part name'],
                        'Qty': qty_input,
                        'Price': part_data.iloc[0]['price']
                    })
                    st.success("Đã thêm!")
                else:
                    st.error("Mã không tồn tại trong hệ thống!")

        if st.session_state['cart']:
            st.table(pd.DataFrame(st.session_state['cart']))
            if st.button("🗑️ Xóa danh sách"):
                st.session_state['cart'] = []
