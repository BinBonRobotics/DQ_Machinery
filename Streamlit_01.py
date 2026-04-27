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
        # Giữ nguyên tên cột gốc để khớp với file của bạn (không chuyển về chữ thường toàn bộ)
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
                # Kiểm tra cột 'email' và 'password' trong sheet members
                if user_email and pass_input:
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
    """Giao diện tra cứu phụ tùng nhanh"""
    st.header("🔍 Quản lý Phụ tùng")
    col_search, _ = st.columns([2, 6])
    with col_search:
        search_query = st.text_input("Nhập Part numbers:", placeholder="Mã 1; Mã 2...")
    
    if search_query:
        list_ma = [s.strip() for s in search_query.replace(',', ';').split(';') if s.strip()]
        # Lọc theo cột 'part number'
        result = df_vattu[df_vattu['part number'].astype(str).isin(list_ma)]
        if not result.empty:
            st.table(result)
        else:
            st.warning("❌ Không tìm thấy mã.")
    else:
        st.dataframe(df_vattu, use_container_width=True)

def chuc_nang_bao_gia(df_vattu, df_customer):
    """Giao diện tạo báo giá chuyên nghiệp"""
    st.header("📄 Tạo Báo giá Phụ tùng")
    
    if df_customer is None:
        st.error("Không thể tải dữ liệu khách hàng.")
        return

    st.subheader("1. Thông tin khách hàng")
    
    # Lấy danh sách từ cột 'Customer-name' (Đúng theo hình bạn gửi)
    list_customers = sorted(df_customer['Customer-name'].unique().tolist())
    selected_customer = st.selectbox("Chọn khách hàng:", ["-- Chọn khách hàng --"] + list_customers)

    if selected_customer != "-- Chọn khách hàng --":
        # Lọc thông tin của khách hàng được chọn
        cus_info = df_customer[df_customer['Customer-name'] == selected_customer]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Customer no:", value=str(cus_info.iloc[0]['Customer no']), disabled=True)
            # Lọc Machine-Type
            list_m_type = sorted(cus_info['Machine-Type'].unique().tolist())
            selected_m_type = st.selectbox("Machine Type:", list_m_type)
        
        with col2:
            st.text_input("Tax Code:", value=str(cus_info.iloc[0]['Tax Code']), disabled=True)
            # Lọc Machine No theo Machine-Type đã chọn
            list_m_no = sorted(cus_info[cus_info['Machine-Type'] == selected_m_type]['Machine No'].unique().tolist())
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
                    st.error("Mã không khớp!")

        if st.session_state['cart']:
            st.table(pd.DataFrame(st.session_state['cart']))
            if st.button("🗑️ Xóa danh sách"):
                st.session_state['cart'] = []
                st.rerun()

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        df_user = load_data(url, "members") 
        st.title("🛡️ D&Q Machinery - Portal")
        chuc_nang_dang_nhap(df_user)
    else:
        # SIDEBAR
        st.sidebar.markdown(f"### 👤 {st.session_state['display_name']}")
        st.sidebar.markdown(f"**Quyền hạn:** `{st.session_state['user_role']}`")
        if st.sidebar.button("🚪 Đăng xuất"):
            st.session_state['logged_in'] = False
            st.rerun()

        st.sidebar.divider()
        menu = st.sidebar.radio("CHỨC NĂNG", ["🔍 Quản lý Phụ tùng", "📄 Báo giá Phụ tùng"])

        # Tải dữ liệu các sheet (Lưu ý viết hoa đúng tên sheet)
        df_vattu = load_data(url, "SP-List")
        df_customer = load_data(url, "Customer-machine")

        if menu == "🔍 Quản lý Phụ tùng":
            chuc_nang_tra_cuu_vat_tu(df_vattu)
        else:
            chuc_nang_bao_gia(df_vattu, df_customer)

if __name__ == "__main__":
    main()
