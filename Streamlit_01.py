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
        
        # Làm sạch tên cột: Xóa khoảng trắng thừa ở đầu/cuối
        data.columns = [str(c).strip() for c in data.columns]
        
        # Xử lý Part number sạch sẽ
        if 'Part number' in data.columns:
            data['Part number'] = data['Part number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            data['Part number'] = data['Part number'].replace('nan', '')
            
        return data
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None

def tinh_toan_bao_gia(df, ty_gia):
    """Tính toán an toàn, không gây lỗi nếu thiếu cột"""
    # Danh sách các cột cần tính toán
    col_euro = 'Giá Net Euro'
    col_he_so = 'Hệ số'
    
    # Kiểm tra xem cột có tồn tại trong File không
    if col_euro in df.columns:
        # Chuyển đổi sang số an toàn
        df[col_euro] = pd.to_numeric(df[col_euro], errors='coerce').fillna(0)
        
        # Lấy Hệ số (nếu không có thì mặc định là 1.0)
        if col_he_so in df.columns:
            df[col_he_so] = pd.to_numeric(df[col_he_so], errors='coerce').fillna(1.0)
        else:
            df[col_he_so] = 1.0
            
        # Thực hiện các phép tính
        df['Giá Net VND'] = df[col_euro] * ty_gia
        df['Giá bán'] = df['Giá Net VND'] * df[col_he_so]
        df['Profit (Lợi nhuận)'] = df['Giá bán'] - df['Giá Net VND']
        
        # Tránh chia cho 0 khi tính Margin
        df['Margin (Biên lợi nhuận)'] = df.apply(
            lambda row: (row['Profit (Lợi nhuận)'] / row['Giá bán']) if row['Giá bán'] != 0 else 0, axis=1
        )
    return df

def hien_thi_dataframe(df):
    """Hàm hiển thị bảng với định dạng số đẹp"""
    display_df = df.copy()
    display_df.index = display_df.index + 2
    
    # Tạo từ điển format cho các cột nếu chúng tồn tại
    format_dict = {}
    if 'Giá Net Euro' in display_df.columns: format_dict['Giá Net Euro'] = "{:,.2f} €"
    if 'Giá Net VND' in display_df.columns: format_dict['Giá Net VND'] = "{:,.0f} ₫"
    if 'Giá bán' in display_df.columns: format_dict['Giá bán'] = "{:,.0f} ₫"
    if 'Profit (Lợi nhuận)' in display_df.columns: format_dict['Profit (Lợi nhuận)'] = "{:,.0f} ₫"
    if 'Margin (Biên lợi nhuận)' in display_df.columns: format_dict['Margin (Biên lợi nhuận)'] = "{:.2%}"

    st.dataframe(display_df.style.format(format_dict), use_container_width=True)

def chuc_nang_tra_cuu_vat_tu(df_vattu, ty_gia):
    st.header("🔍 Hệ thống Quản lý Phụ tùng (SP List)")
    
    # Tính toán trước khi lọc
    df_vattu = tinh_toan_bao_gia(df_vattu, ty_gia)
    
    col_search, _ = st.columns([4, 4])
    with col_search:
        search_query = st.text_input("Nhập Part number (Dùng dấu ; để tìm nhiều mã):", key="search_box")
    
    if search_query:
        list_ma = [s.strip() for s in search_query.split(';') if s.strip()]
        result = df_vattu[df_vattu['Part number'].isin(list_ma)]
        if not result.empty:
            st.success(f"✅ Tìm thấy {len(result)} kết quả.")
            hien_thi_dataframe(result)
        else:
            st.warning(f"❌ Không tìm thấy mã khớp.")
    else:
        st.info(f"💡 Đang hiển thị toàn bộ danh sách ({len(df_vattu)} dòng).")
        hien_thi_dataframe(df_vattu)

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery - SP List", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    st.sidebar.title("⚙️ D&Q Machinery")
    ty_gia = st.sidebar.number_input("Tỷ giá Euro (VND):", value=27500, step=100)
    
    if st.sidebar.button("🔄 Làm mới dữ liệu (Clear Cache)"):
        st.cache_data.clear()
        st.rerun()

    df_raw = load_data(url, "SP List")

    if df_raw is not None:
        # Kiểm tra xem có cột 'Giá Net Euro' không để cảnh báo người dùng
        if 'Giá Net Euro' not in df_raw.columns:
            st.error("⚠️ Cảnh báo: Không tìm thấy cột 'Giá Net Euro' trong file Google Sheets. Vui lòng kiểm tra lại tên cột!")
            st.write("Các cột hiện có trong file của bạn là:", list(df_raw.columns))
        
        chuc_nang_tra_cuu_vat_tu(df_raw, ty_gia)

if __name__ == "__main__":
    main()
