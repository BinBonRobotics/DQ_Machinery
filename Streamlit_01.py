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
        
        # Làm sạch tên cột (xóa khoảng trắng ở đầu/cuối)
        data.columns = data.columns.str.strip()
        
        # Danh sách các từ khóa cần ép kiểu số
        numeric_keywords = ['Giá Net', 'Giá bán', 'Profit', 'VND', 'Euro', 'Tỷ giá', 'Margin']
        
        for col in data.columns:
            # Nếu tên cột chứa các từ khóa trên thì ép về số
            if any(key in col for key in numeric_keywords):
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
            elif col == 'Part number':
                data[col] = data[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                
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
        display_df = df_vattu[df_vattu['Part number'].isin(list_ma)].copy()
    else:
        display_df = df_vattu.copy()

    # Reset index để hàng đầu tiên là số 2 khớp với Sheet
    display_df.index = display_df.index + 2

    # TỰ ĐỘNG TẠO COLUMN CONFIG DỰA TRÊN TÊN CỘT THỰC TẾ
    config = {}
    for col in display_df.columns:
        if any(word in col for word in ['Giá', 'VND', 'Euro', 'Profit', 'Lợi nhuận']):
            config[col] = st.column_config.NumberColumn(col, format="#,##0")
        elif 'Margin' in col:
            # Định dạng phần trăm: hiển thị giá trị * 100 và thêm dấu %
            # Nếu giá trị trong sheet là 0.34 -> hiện 34%
            config[col] = st.column_config.NumberColumn(col, format="%.0f%%")
            # Lưu ý: Streamlit cần giá trị 34 để hiện 34%, nếu sheet là 0.34 ta cần xử lý ở dưới
            
    # Xử lý riêng cho cột Margin để hiển thị đúng %
    for col in display_df.columns:
        if 'Margin' in col:
            if display_df[col].max() <= 1.0: # Nếu dữ liệu dạng 0.34
                display_df[col] = display_df[col] * 100

    st.dataframe(
        display_df,
        use_container_width=True,
        column_config=config
    )

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery - SP List", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    st.sidebar.title("⚙️ D&Q Machinery")
    if st.sidebar.button("🔄 Làm mới dữ liệu"):
        st.cache_data.clear()
        st.rerun()

    df_vattu = load_data(url, "SP List")

    if df_vattu is not None:
        chuc_nang_tra_cuu_vat_tu(df_vattu)

if __name__ == "__main__":
    main()
