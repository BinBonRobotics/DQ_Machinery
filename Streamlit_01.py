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
        return data
    except Exception as e:
        st.error(f"❌ Không tìm thấy Sheet: '{sheet_name}'")
        return None

def chuc_nang_dang_nhap(df_user):
    """Xử lý logic đăng nhập bằng Email và Password"""
    if df_user is None: return
    
    st.markdown("---")
    col_l, col_c, col_r = st.columns([1, 2, 1])
    
    with col_c:
        with st.form("login_form"):
            # Đổi nhãn hiển thị thành Email theo yêu cầu của bạn
            user_email = st.text_input("Địa chỉ Email đăng nhập")
            pass_input = st.text_input("Mật khẩu", type="password")
            submit_button = st.form_submit_button("Xác nhận Đăng nhập")
            
            if submit_button:
                # CHỈNH SỬA: Kiểm tra dựa trên cột 'email' và 'password' trong sheet 'members'
                user_data = df_user[
                    (df_user['email'].astype(str).str.strip() == user_email.strip()) & 
                    (df_user['password'].astype(str).str.strip() == pass_input.strip())
                ]
                
                if not user_data.empty:
                    st.session_state['logged_in'] = True
                    # CHỈNH SỬA: Lưu tên từ cột 'name' để hiển thị lời chào
                    st.session_state['display_name'] = user_data.iloc[0]['name']
                    st.session_state['user_role'] = user_data.iloc[0]['role']
                    st.success(f"Chào mừng {st.session_state['display_name']} đã đăng nhập thành công!")
                    st.rerun()
                else:
                    st.error("Sai địa chỉ Email hoặc mật khẩu. Vui lòng thử lại!")

def chuc_nang_tra_cuu_vat_tu(df):
    """Giao diện tra cứu vật tư"""
    if df is None: return
    st.header("🔍 Hệ thống Tra cứu Phụ tùng")
    
    col1, col2 = st.columns([1, 3]) 
    with col1:
        search_query = st.text_input("Nhập Part numbers:", placeholder="Ví dụ: 4014020227")

    if search_query:
        list_ma = [s.strip() for s in search_query.replace(',', ';').split(';') if s.strip()]
        result = df[df['Part number'].astype(str).isin(list_ma)]
        
        if not result.empty:
            st.success(f"Tìm thấy {len(result)} kết quả.")
            st.table(result)
        else:
            st.warning("❌ Không tìm thấy mã nào.")
    else:
        st.dataframe(df, use_container_width=True)

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        st.title("🛡️ D&Q Machinery - Portal")
        # Sử dụng sheet "members" như bạn đã đổi tên
        df_user = load_data(url, "members") 
        if df_user is not None:
            chuc_nang_dang_nhap(df_user)
    else:
        # CHỈNH SỬA: Hiển thị Tên người dùng thay vì Email ở Sidebar
        st.sidebar.title(f"👤 {st.session_state['display_name']}")
        st.sidebar.info(f"Quyền hạn: {st.session_state['user_role']}")
        
        if st.sidebar.button("🚪 Đăng xuất"):
            st.session_state['logged_in'] = False
            st.rerun()

        # Load dữ liệu từ sheet SP-List
        df_vattu = load_data(url, "SP-List")
        
        menu = ["Tra cứu vật tư", "Thông tin khách hàng"]
        choice = st.sidebar.selectbox("Tính năng:", menu)

        if choice == "Tra cứu vật tư":
            chuc_nang_tra_cuu_vat_tu(df_vattu)
        else:
            st.info("Tính năng đang phát triển...")

if __name__ == "__main__":
    main()
