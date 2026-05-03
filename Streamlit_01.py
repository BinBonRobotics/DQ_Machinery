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
        
        # DANH SÁCH CÁC CỘT CẦN ĐỊNH DẠNG SỐ
        cols_numeric = [
            'Giá Net VND', 'Giá bán', 'Profit (Lợi nhuận)', 
            'Margin (Biên lợi nhuận)', 'Unit Price (VND)', 'Tỷ giá'
        ]
        
        for col in data.columns:
            if col in cols_numeric:
                # Chuyển về số, lỗi (TBA, #N/A) thành NaN sau đó thành 0
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
            elif col == 'Part number':
                # Part number giữ nguyên string sạch
                data[col] = data[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            else:
                # Các cột khác để mặc định
                pass
                
        return data
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None

def chuc_nang_tra_cuu_vat_tu(df_vattu):
    st.header("🔍 Hệ thống Quản lý Phụ tùng (SP List)")
    
    col_search, _ = st.columns([4, 4])
    with col_search:
        search_query = st.text_input("Nhập Part number (Dùng dấu ; để tìm nhiều mã):")
    
    # Chuẩn bị dữ liệu hiển thị
    if search_query:
        list_ma = [s.strip() for s in search_query.split(';') if s.strip()]
        display_df = df_vattu[df_vattu['Part number'].isin(list_ma)].copy()
    else:
        display_df = df_vattu.copy()

    display_df.index = display_df.index + 2

    # ĐỊNH DẠNG HIỂN THỊ CỘT (GIỐNG GOOGLE SHEETS)
    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "Giá Net VND": st.column_config.NumberColumn("Giá Net VND", format="#,##0"),
            "Giá bán": st.column_config.NumberColumn("Giá bán", format="#,##0"),
            "Profit (Lợi nhuận)": st.column_config.NumberColumn("Profit (Lợi nhuận)", format="#,##0"),
            "Margin (Biên lợi nhuận)": st.column_config.NumberColumn("Margin (%)", format="%.0f%%") if display_df['Margin (Biên lợi nhuận)'].max() > 1 else st.column_config.ProgressColumn("Margin (%)", format="%.2f", min_value=0, max_value=1),
            # Nếu Margin trong sheet là 0.34 thì dùng format bên dưới để hiện 34%
            "Margin (Biên lợi nhuận)": st.column_config.NumberColumn("Margin (%)", format="%.2f") 
        }
    )

    # Lưu ý về Margin: 
    # Nếu trong Google Sheets bạn để 0.33 và chọn định dạng %, Streamlit sẽ hiểu là 0.33.
    # Để hiển thị dạng %, tôi sẽ dùng cấu hình ColumnConfig bên dưới cho chính xác hơn.

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
        # Cập nhật Margin hiển thị dạng % nếu nó đang ở dạng số thập phân (ví dụ 0.33 -> 33%)
        # df_vattu['Margin (Biên lợi nhuận)'] = df_vattu['Margin (Biên lợi nhuận)'] * 100 # Mở dòng này nếu muốn nhân 100
        
        chuc_nang_tra_cuu_vat_tu(df_vattu)

if __name__ == "__main__":
    main()
