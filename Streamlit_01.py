import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=600) # Lưu cache 10 phút để app mượt hơn
def load_data(url_link, sheet_name):
    """Tải dữ liệu từ Google Sheets và xử lý định dạng"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=url_link, worksheet=sheet_name, ttl=0)
        
        # Làm sạch tên cột
        data.columns = data.columns.str.strip()
        
        # Xử lý Part number để không bị hiện đuôi .0
        if 'Part number' in data.columns:
            data['Part number'] = pd.to_numeric(data['Part number'], errors='coerce').fillna(0).astype(int).astype(str)
            data['Part number'] = data['Part number'].replace('0', '')
            
        return data
    except Exception as e:
        # Hiển thị lỗi cụ thể để dễ debug
        st.error(f"❌ Lỗi khi tải Sheet '{sheet_name}': {e}")
        return None

def chuc_nang_tra_cuu_vat_tu(df_vattu):
    """Hiển thị toàn bộ danh sách phụ tùng và hỗ trợ tìm kiếm"""
    st.header("🔍 Hệ thống Quản lý Phụ tùng (SP List)")
    
    # Khu vực bộ lọc tìm kiếm
    col_search, _ = st.columns([3, 5])
    with col_search:
        search_query = st.text_input("Tìm kiếm nhanh (Nhập Part number):")
    
    if search_query:
        # Hỗ trợ tìm kiếm nhiều mã cách nhau bằng dấu ; hoặc ,
        list_ma = [s.strip() for s in search_query.replace(',', ';').split(';') if s.strip()]
        result = df_vattu[df_vattu['Part number'].astype(str).isin(list_ma)]
        
        if not result.empty:
            st.success(f"Tìm thấy {len(result)} kết quả.")
            st.dataframe(result, use_container_width=True)
        else:
            st.warning("❌ Không tìm thấy mã trong danh sách.")
    else:
        # Mặc định hiển thị toàn bộ tất cả dòng và cột
        st.info(f"Đang hiển thị toàn bộ danh sách ({len(df_vattu)} dòng).")
        st.dataframe(df_vattu, use_container_width=True)

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    # Cấu hình trang
    st.set_page_config(page_title="D&Q Machinery - SP-List", layout="wide")
    
    # Link Google Sheets của bạn
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    # Sidebar tối giản
    st.sidebar.title("⚙️ D&Q Machinery")
    st.sidebar.markdown("---")
    st.sidebar.write("✅ **Tính năng:** Quản lý Phụ tùng")
    st.sidebar.info("Dữ liệu được lấy trực tiếp từ tab 'SP-List'")

    # Chỉ load duy nhất tab SP List
    df_vattu = load_data(url, "SP-List")

    if df_vattu is not None:
        chuc_nang_tra_cuu_vat_tu(df_vattu)
    else:
        st.error("Không thể kết nối với dữ liệu. Vui lòng kiểm tra lại tên tab trên Google Sheets hoặc quyền chia sẻ link.")

if __name__ == "__main__":
    main()
