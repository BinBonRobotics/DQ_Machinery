import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=60)
def load_data(url_link, sheet_name):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=url_link, worksheet=sheet_name, ttl=0)
        
        # Làm sạch tên cột
        data.columns = data.columns.str.strip()
        
        # XỬ LÝ CỘT SỐ CÓ CHỮ (TBA, ERROR, #N/A -> 0)
        # Bạn có thể thêm tên các cột cần ép về số vào danh sách bên dưới
        cols_to_fix = [
            'Unit2', 
            'Unit Price 2026', 
            'Unit Price (VND) 2026', 
            'Tax', 
            '30000', 
            'VAT'
        ]
        
        for col in cols_to_fix:
            if col in data.columns:
                # errors='coerce' sẽ biến chữ thành NaN, sau đó fillna(0) biến NaN thành 0
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        
        # Riêng Part number phải giữ dạng chuỗi sạch để tìm kiếm
        if 'Part number' in data.columns:
            data['Part number'] = data['Part number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
        return data
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
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
            st.dataframe(display_df, use_container_width=True)
        else:
            st.warning(f"❌ Không tìm thấy mã khớp.")
    else:
        st.info(f"💡 Đang hiển thị toàn bộ danh sách ({len(df_vattu)} dòng).")
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
    
    if st.sidebar.button("🔄 Làm mới dữ liệu (Clear Cache)"):
        st.cache_data.clear()
        st.rerun()

    df_vattu = load_data(url, "SP List")

    if df_vattu is not None:
        chuc_nang_tra_cuu_vat_tu(df_vattu)

if __name__ == "__main__":
    main()
