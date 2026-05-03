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
        # Đọc dữ liệu và ép tất cả về String để giữ nguyên định dạng của GSheet
        data = conn.read(spreadsheet=url_link, worksheet=sheet_name, ttl=0)
        
        # Chỉ lấy cột B -> U (Cột 1 đến 20)
        if data.shape[1] >= 21:
            data = data.iloc[:, 1:21]
            
        # Làm sạch tên cột
        data.columns = [str(c).strip() for c in data.columns]
        
        return data
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None

def format_number(val):
    """Hàm bổ trợ để format số thủ công cho đẹp"""
    if pd.isna(val) or val == "": return ""
    try:
        # Nếu là số nguyên hoặc số thập phân
        num = float(val)
        if num == int(num):
            return f"{int(num):,}" # 11,197,000
        else:
            # Giữ tối đa 2 chữ số thập phân và xóa số 0 thừa ở cuối (9.300000 -> 9.3)
            return f"{num:,.2f}".rstrip('0').rstrip('.')
    except:
        return str(val)

def xu_ly_va_tinh_toan(df, ty_gia):
    """Chuyển đổi số để tính toán nhưng giữ hiển thị theo ý người dùng"""
    
    # Danh sách các cột cần tính toán
    cols_to_calc = ['Giá Net Euro', 'Hệ số', 'Giá bán', 'Giá Net VND', 'Profit (Lợi nhuận)']
    
    # Tạo bản sao để tính toán số học
    calc_df = df.copy()
    for col in calc_df.columns:
        # Chuyển đổi về dạng số để tính toán, loại bỏ dấu phẩy nếu có trong chuỗi
        calc_df[col] = pd.to_numeric(calc_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    # Thực hiện tính toán (Dựa trên logic bạn cung cấp)
    calc_df['Giá Net VND'] = calc_df['Giá Net Euro'] * ty_gia
    calc_df['Giá bán'] = calc_df['Giá Net VND'] * calc_df['Hệ số']
    calc_df['Profit (Lợi nhuận)'] = calc_df['Giá bán'] - calc_df['Giá Net VND']
    calc_df['Margin (Biên lợi nhuận)'] = (calc_df['Profit (Lợi nhuận)'] / calc_df['Giá bán']).fillna(0)

    # Cập nhật kết quả tính toán ngược lại vào df hiển thị và ép format
    df['Giá Net VND'] = calc_df['Giá Net VND'].apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df['Giá bán'] = calc_df['Giá bán'].apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df['Profit (Lợi nhuận)'] = calc_df['Profit (Lợi nhuận)'].apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df['Margin (Biên lợi nhuận)'] = calc_df['Margin (Biên lợi nhuận)'].apply(lambda x: f"{x:.0%}" if x != 0 else "0%")
    
    # Format lại các cột số có sẵn từ GSheet (như Unit Price, Net Weight...)
    for col in df.columns:
        if col not in ['Giá Net VND', 'Giá bán', 'Profit (Lợi nhuận)', 'Margin (Biên lợi nhuận)', 'Part number']:
            df[col] = df[col].apply(format_number)

    return df

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    st.sidebar.title("⚙️ Cấu hình")
    ty_gia_input = st.sidebar.number_input("Tỷ giá Euro (VND):", value=31000, step=100)
    
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    df_raw = load_data(url, "SP List")

    if df_raw is not None:
        st.header("🔍 Tra cứu Phụ tùng (Cột B -> U)")
        
        # Xử lý tính toán và định dạng
        df_display = xu_ly_va_tinh_toan(df_raw, ty_gia_input)
        
        # Tìm kiếm
        search_query = st.text_input("Nhập Part number:")
        
        if search_query:
            list_ma = [s.strip() for s in search_query.split(';') if s.strip()]
            df_display = df_display[df_display['Part number'].astype(str).isin(list_ma)]

        # Hiển thị
        st.dataframe(df_display, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
