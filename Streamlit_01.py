import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=300) # Cập nhật cache mỗi 5 phút
def load_data(url_link, sheet_name):
    """Tải dữ liệu và chuẩn hóa để khớp với hàng lối trong Sheets"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Đọc dữ liệu
        data = conn.read(spreadsheet=url_link, worksheet=sheet_name, ttl=0)
        
        # Làm sạch tên cột
        data.columns = data.columns.str.strip()
        
        # Chuyển đổi toàn bộ cột 'Part number' sang chuỗi (string) để tìm kiếm chính xác
        # và loại bỏ .0 nếu có
        if 'Part number' in data.columns:
            data['Part number'] = data['Part number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
        return data
    except Exception as e:
        st.error(f"❌ Lỗi khi tải Sheet '{sheet_name}': {e}")
        return None

def chuc_nang_tra_cuu_vat_tu(df_vattu):
    """Tính năng tìm kiếm nâng cao và hiển thị đúng số hàng"""
    st.header("🔍 Hệ thống Quản lý Phụ tùng (SP List)")
    
    # Khu vực bộ lọc tìm kiếm
    col_search, _ = st.columns([4, 4])
    with col_search:
        # Hướng dẫn người dùng nhập liệu
        search_query = st.text_input("Nhập Part number (Dùng dấu ; để tìm nhiều mã):", placeholder="Ví dụ: 30 charge; 40 charge")
    
    # Xử lý tìm kiếm
    if search_query:
        # 1. Tách chuỗi bằng dấu ;
        # 2. Loại bỏ khoảng trắng thừa của từng mã
        # 3. Loại bỏ các phần tử rỗng
        list_ma = [s.strip() for s in search_query.split(';') if s.strip()]
        
        # Lọc dữ liệu: Kiểm tra xem Part number có nằm trong danh sách list_ma không
        result = df_vattu[df_vattu['Part number'].isin(list_ma)]
        
        if not result.empty:
            st.success(f"✅ Tìm thấy {len(result)} kết quả tương ứng.")
            # Điều chỉnh index hiển thị bắt đầu từ 2 để khớp với hàng trong Google Sheets
            display_df = result.copy()
            display_df.index = display_df.index + 2
            st.dataframe(display_df, use_container_width=True)
        else:
            st.warning(f"❌ Không tìm thấy mã nào khớp với: {', '.join(list_ma)}")
    else:
        # Mặc định hiển thị toàn bộ
        st.info(f"💡 Đang hiển thị toàn bộ danh sách ({len(df_vattu)} dòng).")
        
        # Điều chỉnh index hiển thị để hàng đầu tiên là số 2
        full_display_df = df_vattu.copy()
        full_display_df.index = full_display_df.index + 2
        st.dataframe(full_display_df, use_container_width=True)

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery - SP List", layout="wide")
    
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    st.sidebar.title("⚙️ D&Q Machinery")
    st.sidebar.write("---")
    st.sidebar.info("Chế độ: Truy xuất dữ liệu thời gian thực từ Google Sheets")

    # Tải dữ liệu từ tab 'SP List'
    df_vattu = load_data(url, "SP List")

    if df_vattu is not None:
        chuc_nang_tra_cuu_vat_tu(df_vattu)

if __name__ == "__main__":
    main()
