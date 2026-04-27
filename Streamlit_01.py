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
        
        # CHỈNH SỬA QUAN TRỌNG: Loại bỏ khoảng trắng thừa trong tên cột
        data.columns = data.columns.str.strip().str.lower()
        
        return data
    except Exception as e:
        st.error(f"❌ Lỗi khi tải Sheet '{sheet_name}': {e}")
        return None

def chuc_nang_dang_nhap(df_user):
    """Xử lý logic đăng nhập"""
    if df_user is None: return
    
    st.markdown("---")
    col_l, col_c, col_r = st.columns([1, 2, 1])
    
    with col_c:
        with st.form("login_form"):
            user_email = st.text_input("Địa chỉ Email đăng nhập")
            pass_input = st.text_input("Mật khẩu", type="password")
            submit_button = st.form_submit_button("Xác nhận Đăng nhập")
            
            if submit_button:
                # Kiểm tra sự tồn tại của cột trước khi truy vấn để tránh KeyError
                if 'email' not in df_user.columns or 'password' not in df_user.columns:
                    st.error("❌ Cấu trúc bảng tính không đúng. Cần có cột 'email' và 'password'.")
                    st.write("Cột hiện có:", list(df_user.columns))
                    return

                # Thực hiện lọc dữ liệu
                user_data = df_user[
                    (df_user['email'].astype(str).str.strip() == user_email.strip()) & 
                    (df_user['password'].astype(str).str.strip() == pass_input.strip())
                ]
                
                if not user_data.empty:
                    st.session_state['logged_in'] = True
                    # Lấy tên hiển thị từ cột 'name'
                    st.session_state['display_name'] = user_data.iloc[0]['name'] if 'name' in df_user.columns else user_email
                    st.session_state['user_role'] = user_data.iloc[0]['role'] if 'role' in df_user.columns else "N/A"
                    st.success(f"Chào mừng {st.session_state['display_name']}!")
                    st.rerun()
                else:
                    st.error("Sai địa chỉ Email hoặc mật khẩu!")

def chuc_nang_tra_cuu_vat_tu(df):
    """Giao diện tra cứu vật tư"""
    if df is None: return
    st.header("🔍 Hệ thống Tra cứu Phụ tùng")
    
    # Chuẩn hóa tên cột cho dữ liệu vật tư
    df.columns = df.columns.str.strip()
    
    search_query = st.text_input("Nhập Part numbers (cách nhau bởi dấu ;):")

    if search_query:
        list_ma = [s.strip() for s in search_query.replace(',', ';').split(';') if s.strip()]
        # Đảm bảo dùng đúng tên cột 'Part number'
        col_name = 'Part number' if 'Part number' in df.columns else df.columns[0]
        result = df[df[col_name].astype(str).isin(list_ma)]
        
        if not result.empty:
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
        # Gọi đúng sheet 'members' đã đổi tên
        df_user = load_data(url, "members") 
        chuc_nang_dang_nhap(df_user)
    else:
        st.sidebar.title(f"👤 {st.session_state.get('display_name', 'User')}")
        if st.sidebar.button("🚪 Đăng xuất"):
            st.session_state['logged_in'] = False
            st.rerun()

        df_vattu = load_data(url, "SP-List")
        chuc_nang_tra_cuu_vat_tu(df_vattu)

if __name__ == "__main__":
    main()
