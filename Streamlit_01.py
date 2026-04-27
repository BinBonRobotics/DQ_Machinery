import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=3600)
def load_data(url_link, sheet_name):
    """Tải dữ liệu và chuẩn hóa tên cột"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=url_link, worksheet=sheet_name, ttl=0)
        # Chuẩn hóa: xóa khoảng trắng và viết thường tên cột
        data.columns = data.columns.str.strip().str.lower()
        return data
    except Exception as e:
        st.error(f"❌ Lỗi khi tải Sheet '{sheet_name}': {e}")
        return None

def chuc_nang_dang_nhap(df_user):
    """Giao diện đăng nhập"""
    st.markdown("---")
    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        with st.form("login_form"):
            user_email = st.text_input("Địa chỉ Email đăng nhập")
            pass_input = st.text_input("Mật khẩu", type="password")
            if st.form_submit_button("Xác nhận Đăng nhập"):
                user_data = df_user[(df_user['email'].astype(str).str.strip() == user_email.strip()) & 
                                    (df_user['password'].astype(str).str.strip() == pass_input.strip())]
                if not user_data.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['display_name'] = user_data.iloc[0]['name']
                    st.session_state['user_role'] = user_data.iloc[0]['role']
                    st.rerun()
                else:
                    st.error("Sai tài khoản hoặc mật khẩu!")

def chuc_nang_tra_cuu_vat_tu(df):
    """Tính năng: Quản lý Phụ tùng"""
    st.header("🔍 Quản lý Phụ tùng")
    col_search, _ = st.columns([2, 6])
    with col_search:
        search_query = st.text_input("Nhập Part numbers:", placeholder="Mã 1; Mã 2...")
    
    if search_query:
        list_ma = [s.strip() for s in search_query.replace(',', ';').split(';') if s.strip()]
        # Tìm cột chứa part number (thường là cột đầu tiên hoặc có tên tương ứng)
        col_name = 'part number' if 'part number' in df.columns else df.columns[0]
        result = df[df[col_name].astype(str).isin(list_ma)]
        if not result.empty:
            st.table(result)
        else:
            st.warning("❌ Không tìm thấy mã.")
    else:
        st.dataframe(df, use_container_width=True)

def chuc_nang_bao_gia(df_vattu, df_customer):
    """Tính năng: Báo giá Phụ tùng (MỚI)"""
    st.header("📄 Tạo Báo giá Phụ tùng")

    # --- PHẦN 1: THÔNG TIN KHÁCH HÀNG ---
    st.subheader("1. Thông tin khách hàng")
    
    # 1. Chọn Customer Name
    list_customers = df_customer['customer name'].unique().tolist()
    selected_customer = st.selectbox("Chọn khách hàng:", ["-- Chọn khách hàng --"] + list_customers)

    if selected_customer != "-- Chọn khách hàng --":
        # Lọc dữ liệu theo khách hàng đã chọn
        cus_info = df_customer[df_customer['customer name'] == selected_customer]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Customer No:", value=cus_info.iloc[0]['customer no'], disabled=True)
            # Lọc Machine Type tương ứng với khách hàng này
            list_m_type = cus_info['machine type'].unique().tolist()
            selected_m_type = st.selectbox("Machine Type:", list_m_type)
        
        with col2:
            st.text_input("Tax Code:", value=cus_info.iloc[0]['tax code'], disabled=True)
            # Lọc Machine No tương ứng với Machine Type đã chọn
            list_m_no = cus_info[cus_info['machine type'] == selected_m_type]['machine no'].unique().tolist()
            selected_m_no = st.selectbox("Machine No:", list_m_no)
            
        with col3:
            st.text_area("Address:", value=cus_info.iloc[0]['address'], disabled=True, height=100)

        # --- PHẦN 2: CHỌN PHỤ TÙNG ---
        st.divider()
        st.subheader("2. Danh mục phụ tùng")
        
        # Khởi tạo giỏ hàng trong session nếu chưa có
        if 'cart' not in st.session_state:
            st.session_state['cart'] = []

        col_part, col_qty, col_add = st.columns([3, 1, 1])
        with col_part:
            part_input = st.text_input("Nhập mã phụ tùng cần thêm:")
        with col_qty:
            qty_input = st.number_input("Số lượng:", min_value=1, value=1)
        with col_add:
            st.write("##") # Căn chỉnh nút bấm
            if st.button("➕ Thêm vào Offer"):
                # Tìm thông tin vật tư
                part_data = df_vattu[df_vattu['part number'].astype(str) == part_input.strip()]
                if not part_data.empty:
                    item = {
                        'Part No': part_input,
                        'Description': part_data.iloc[0]['description'] if 'description' in part_data.columns else "N/A",
                        'Qty': qty_input,
                        'Unit Price': part_data.iloc[0]['unit price'] if 'unit price' in part_data.columns else 0
                    }
                    st.session_state['cart'].append(item)
                    st.success(f"Đã thêm {part_input}")
                else:
                    st.error("Mã không tồn tại!")

        # Hiển thị bảng giỏ hàng hiện tại
        if st.session_state
