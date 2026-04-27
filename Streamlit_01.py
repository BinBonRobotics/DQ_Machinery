import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=3600)
def load_data(url_link, sheet_name):
    """Tải dữ liệu từ Google Sheets"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(spreadsheet=url_link, worksheet=sheet_name, ttl=0)
    return data

def chuc_nang_dang_nhap(df_user):
    """Xử lý logic đăng nhập"""
    st.markdown("---")
    col_l, col_c, col_r = st.columns([1, 2, 1]) # Đưa form vào giữa cho đẹp
    
    with col_c:
        with st.form("login_form"):
            user_input = st.text_input("Tên đăng nhập")
            pass_input = st.text_input("Mật khẩu", type="password")
            submit_button = st.form_submit_button("Xác nhận Đăng nhập")
            
            if submit_button:
                # Kiểm tra khớp username và password, cột bây giờ là 'role'
                user_data = df_user[(df_user['username'].astype(str) == user_input) & 
                                    (df_user['password'].astype(str) == pass_input)]
                
                if not user_data.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user_name'] = user_input
                    st.session_state['user_role'] = user_data.iloc[0]['role'] # Đã sửa thành role
                    st.success("Đăng nhập thành công!")
                    st.rerun()
                else:
                    st.error("Sai tài khoản hoặc mật khẩu, vui lòng thử lại!")

def chuc_nang_tra_cuu_vat_tu(df):
    """Giao diện và logic tra cứu vật tư"""
    st.header("🔍 Hệ thống Tra cứu Phụ tùng")
    
    col1, col2 = st.columns([1, 3]) 
    with col1:
        search_query = st.text_input("Nhập Part numbers:", placeholder="Mã 1; Mã 2...")

    if search_query:
        # Logic tìm nhiều mã cùng lúc
        list_ma = [s.strip() for s in search_query.replace(',', ';').split(';') if s.strip()]
        result = df[df['Part number'].astype(str).isin(list_ma)]
        
        if not result.empty:
            st.success(f"Tìm thấy {len(result)} kết quả.")
            st.table(result)
            
            # Báo mã không tồn tại
            ma_tim_thay = result['Part number'].astype(str).tolist()
            ma_khong_thay = [m for m in list_ma if m not in ma_tim_thay]
            if ma_khong_thay:
                st.warning(f"⚠️ Không tìm thấy mã: {', '.join(ma_khong_thay)}")
        else:
            st.warning("❌ Không có dữ liệu cho các mã trên.")
    else:
        st.info("💡 Mẹo: Bạn có thể nhập nhiều mã cách nhau bằng dấu chấm phẩy (;)")
        st.dataframe(df, use_container_width=True)

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    # Cấu hình layout
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    # Quản lý trạng thái đăng nhập
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    try:
        if not st.session_state['logged_in']:
            # GIAO DIỆN KHI CHƯA ĐĂNG NHẬP
            st.title("🛡️ D&Q Machinery - Portal")
            df_user = load_data(url, "user")
            chuc_nang_dang_nhap(df_user)
        else:
            # GIAO DIỆN KHI ĐÃ ĐĂNG NHẬP
            st.sidebar.title(f"👤 {st.session_state['user_name']}")
            st.sidebar.info(f"Quyền hạn: {st.session_state['user_role']}")
            
            if st.sidebar.button("🚪 Đăng xuất"):
                st.session_state['logged_in'] = False
                st.rerun()

            # Tải dữ liệu chính
            df_vattu = load_data(url, "SP-List")

            # Menu điều hướng
            menu = ["Tra cứu vật tư", "Thông tin khách hàng"]
            choice = st.sidebar.selectbox("Lựa chọn tính năng:", menu)

            if choice == "Tra cứu vật tư":
                chuc_nang_tra_cuu_vat_tu(df_vattu)
            elif choice == "Thông tin khách hàng":
                st.title("👥 Danh sách Khách hàng")
                st.write("Dữ liệu khách hàng đang được đồng bộ...")

    except Exception as e:
        st.error(f"⚠️ Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    main()
