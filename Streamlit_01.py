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
        # Chuẩn hóa tên cột: xóa khoảng trắng và chuyển về chữ thường
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
                if 'email' not in df_user.columns or 'password' not in df_user.columns:
                    st.error("❌ Bảng tính thiếu cột 'email' hoặc 'password'.")
                    return

                user_data = df_user[
                    (df_user['email'].astype(str).str.strip() == user_email.strip()) & 
                    (df_user['password'].astype(str).str.strip() == pass_input.strip())
                ]
                
                if not user_data.empty:
                    st.session_state['logged_in'] = True
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
    
    # ĐIỀU CHỈNH: Thu ngắn thanh search bằng cách chia cột theo tỷ lệ 2:6
    col_search, col_empty = st.columns([2, 6])
    with col_search:
        search_query = st.text_input("Nhập Part numbers:", placeholder="Mã 1; Mã 2...")

    if search_query:
        list_ma = [s.strip() for s in search_query.replace(',', ';').split(';') if s.strip()]
        # Xác định cột chứa mã phụ tùng (mặc định là cột đầu tiên nếu không tìm thấy 'part number')
        col_name = 'part number' if 'part number' in df.columns.str.lower() else df.columns[0]
        
        result = df[df[col_name].astype(str).isin(list_ma)]
        
        if not result.empty:
            st.success(f"Tìm thấy {len(result)} kết quả.")
            st.table(result)
        else:
            st.warning("❌ Không tìm thấy mã nào.")
    else:
        st.info("💡 Nhập mã phụ tùng để tra cứu nhanh.")
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
        df_user = load_data(url, "members") 
        chuc_nang_dang_nhap(df_user)
    else:
        # HIỂN THỊ: Tên người dùng và Role ngay bên dưới ở Sidebar
        st.sidebar.markdown(f"### 👤 {st.session_state['display_name']}")
        st.sidebar.markdown(f"**Quyền hạn:** `{st.session_state['user_role']}`")
        
        if st.sidebar.button("🚪 Đăng xuất"):
            st.session_state['logged_in'] = False
            st.rerun()

        st.sidebar.divider()
        
        df_vattu = load_data(url, "SP-List")
        chuc_nang_tra_cuu_vat_tu(df_vattu)

if __name__ == "__main__":
    main()
