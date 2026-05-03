import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=300)
def load_data(url_link, sheet_name):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=url_link, worksheet=sheet_name, ttl=0)
        
        # Làm sạch tên cột
        data.columns = data.columns.str.strip()
        
        # FIX LỖI PYARROW: Ép toàn bộ dataframe thành kiểu chuỗi (string)
        # Việc này giúp tránh lỗi khi một cột vừa có số vừa có chữ (như HOMAG, TBA)
        data = data.fillna("").astype(str)
        
        # Riêng Part number vẫn xử lý để mất đuôi .0 cho đẹp
        if 'Part number' in data.columns:
            data['Part number'] = data['Part number'].str.replace(r'\.0$', '', regex=True)
            
        return data
    except Exception as e:
        st.error(f"❌ Lỗi khi tải Sheet: {e}")
        return None

def chuc_nang_tra_cuu_vat_tu(df_vattu):
    st.header("🔍 Hệ thống Quản lý Phụ tùng (SP List)")
    
    col_search, _ = st.columns([4, 4])
    with col_search:
        search_query = st.text_input("Nhập Part number (Dùng dấu ; để tìm nhiều mã):")
    
    if search_query:
        list_ma = [s.strip() for s in search_query.split(';') if s.strip()]
        result = df_vattu[df_vattu['Part number'].isin(list_ma)]
        
        if not result.empty:
            st.success(f"✅ Tìm thấy {len(result)} kết quả.")
            display_df = result.copy()
            display_df.index = display_df.index + 2
            # SỬA LỖI width='stretch' THEO PHIÊN BẢN MỚI
            st.dataframe(display_df, width=None, use_container_width=True) 
        else:
            st.warning(f"❌ Không tìm thấy mã khớp.")
    else:
        st.info(f"💡 Đang hiển thị toàn bộ danh sách ({len(df_vattu)} dòng).")
        full_display_df = df_vattu.copy()
        full_display_df.index = full_display_df.index + 2
        st.dataframe(full_display_df, width=None, use_container_width=True)

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery - SP List", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    st.sidebar.title("⚙️ D&Q Machinery")
    df_vattu = load_data(url, "SP List")

    if df_vattu is not None:
        chuc_nang_tra_cuu_vat_tu(df_vattu)

if __name__ == "__main__":
    main()
