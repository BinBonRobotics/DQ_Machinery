import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=3600)
def load_data(url_link, sheet_name):
    """Chương trình con: Kết nối và tải dữ liệu từ Google Sheets"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(spreadsheet=url_link, worksheet=sheet_name, ttl=0)
    return data

def chuc_nang_tra_cuu_vat_tu(df):
    """Chương trình con: Giao diện và logic tra cứu vật tư"""
    st.header("🔍 Tra cứu Phụ tùng Homag")
    
    col1, col2 = st.columns([1, 3]) 
    with col1:
        search_query = st.text_input("Nhập Part numbers:", placeholder="Ví dụ: 4014020227; 2056186140")

    if search_query:
        # Logic tách mã và lọc dữ liệu
        list_ma = [s.strip() for s in search_query.replace(',', ';').split(';') if s.strip()]
        result = df[df['Part number'].astype(str).isin(list_ma)]
        
        if not result.empty:
            st.success(f"🔍 Đã tìm thấy {len(result)} mã hàng.")
            st.table(result)
            
            # Kiểm tra mã thiếu
            ma_tim_thay = result['Part number'].astype(str).tolist()
            ma_khong_thay = [m for m in list_ma if m not in ma_tim_thay]
            if ma_khong_thay:
                st.warning(f"⚠️ Không tìm thấy mã: {', '.join(ma_khong_thay)}")
        else:
            st.warning("❌ Không tìm thấy mã nào trong danh sách trên.")
    else:
        st.info("💡 Nhập mã để kiểm tra giá.")
        st.dataframe(df, use_container_width=True)

def chuc_nang_khach_hang():
    """Chương trình con: (Tính năng mới sắp viết)"""
    st.header("👥 Quản lý Khách hàng")
    st.write("Tính năng này đang được phát triển...")

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    # Cấu hình chung
    st.set_page_config(page_title="Hệ thống D&Q", layout="wide")
    st.title("🛡️ D&Q Machinery - Homag Partner")

    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    try:
        # Tải dữ liệu dùng chung
        df_vattu = load_data(url, "SP-List")

        # MENU ĐIỀU KHIỂN (Bật/Tắt tính năng)
        # Bạn có thể dùng Sidebar để tạo menu chọn tính năng
        menu = ["Tra cứu vật tư", "Thông tin khách hàng"]
        choice = st.sidebar.selectbox("Chọn tính năng muốn sử dụng:", menu)

        if choice == "Tra cứu vật tư":
            chuc_nang_tra_cuu_vat_tu(df_vattu)
        
        elif choice == "Thông tin khách hàng":
            chuc_nang_khach_hang()

    except Exception as e:
        st.error(f"Hệ thống gặp lỗi: {e}")

# Chạy chương trình chính
if __name__ == "__main__":
    main()
