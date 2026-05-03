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
        # Đọc toàn bộ sheet
        data = conn.read(spreadsheet=url_link, worksheet=sheet_name, ttl=0)
        
        # --- ĐIỀU CHỈNH: Chỉ lấy các cột từ B đến U ---
        # Trong pandas, .iloc[:, 1:21] sẽ lấy từ cột thứ 2 (chỉ số 1 - cột B) 
        # đến cột thứ 21 (chỉ số 20 - cột U)
        if data.shape[1] >= 21:
            data = data.iloc[:, 1:21]
        
        # Làm sạch tên cột
        data.columns = [str(c).strip() for c in data.columns]
        
        # Xử lý Part number nếu có
        if 'Part number' in data.columns:
            data['Part number'] = data['Part number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            data['Part number'] = data['Part number'].replace('nan', '')
            
        return data
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ và cắt cột: {e}")
        return None

def tinh_toan_bao_gia(df, ty_gia):
    """Tính toán an toàn dựa trên tên cột thực tế"""
    # Ép kiểu số cho các cột tính toán để tránh lỗi
    for col in ['Giá Net Euro', 'Hệ số']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    if 'Giá Net Euro' in df.columns:
        # Nếu không có cột Hệ số, mặc định là 1.0
        he_so = df['Hệ số'] if 'Hệ số' in df.columns else 1.0
        
        df['Giá Net VND'] = df['Giá Net Euro'] * ty_gia
        df['Giá bán'] = df['Giá Net VND'] * he_so
        df['Profit (Lợi nhuận)'] = df['Giá bán'] - df['Giá Net VND']
        
        # Tính Margin an toàn
        df['Margin (Biên lợi nhuận)'] = df.apply(
            lambda row: (row['Profit (Lợi nhuận)'] / row['Giá bán']) if row['Giá bán'] != 0 else 0, axis=1
        )
    return df

def hien_thi_dataframe(df):
    """Hiển thị bảng với format tiền tệ"""
    display_df = df.copy()
    display_df.index = display_df.index + 2
    
    format_dict = {}
    if 'Giá Net Euro' in display_df.columns: format_dict['Giá Net Euro'] = "{:,.2f} €"
    if 'Giá Net VND' in display_df.columns: format_dict['Giá Net VND'] = "{:,.0f} ₫"
    if 'Giá bán' in display_df.columns: format_dict['Giá bán'] = "{:,.0f} ₫"
    if 'Profit (Lợi nhuận)' in display_df.columns: format_dict['Profit (Lợi nhuận)'] = "{:,.0f} ₫"
    if 'Margin (Biên lợi nhuận)' in display_df.columns: format_dict['Margin (Biên lợi nhuận)'] = "{:.2%}"

    st.dataframe(display_df.style.format(format_dict), use_container_width=True)

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery - SP List", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    st.sidebar.title("⚙️ Cấu hình")
    ty_gia = st.sidebar.number_input("Tỷ giá Euro (VND):", value=27500, step=100)
    
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    df_raw = load_data(url, "SP List")

    if df_raw is not None:
        st.header("🔍 Hệ thống Quản lý Phụ tùng (Cột B -> U)")
        
        # 1. Tính toán giá
        df_final = tinh_toan_bao_gia(df_raw, ty_gia)
        
        # 2. Tìm kiếm
        search_query = st.text_input("Nhập Part number để tìm kiếm:")
        
        if search_query:
            list_ma = [s.strip() for s in search_query.split(';') if s.strip()]
            result = df_final[df_final['Part number'].isin(list_ma)]
            hien_thi_dataframe(result)
        else:
            hien_thi_dataframe(df_final)

if __name__ == "__main__":
    main()
