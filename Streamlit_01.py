import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=60)
def load_data(url_link, sheet_name):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=url_link, worksheet=sheet_name, ttl=0)
        
        # Làm sạch tên cột (bỏ khoảng trắng và ký tự xuống dòng)
        data.columns = [c.replace('\n', ' ').strip() for c in data.columns]
        
        # Lấy từ cột A (chỉ số 0) đến cột U (chỉ số 21)
        if data.shape[1] >= 21:
            data = data.iloc[:, 0:21]
            
        return data
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None

def format_number_with_comma(val):
    """Hàm chuyển đổi mọi giá trị số thành chuỗi có dấu phân cách ngàn"""
    if pd.isna(val) or str(val).strip() in ['-', '']: 
        return "-"
    try:
        # Loại bỏ dấu phẩy cũ nếu có để ép kiểu số
        num_str = str(val).replace(',', '').strip()
        num = float(num_str)
        
        # Nếu là số nguyên (ví dụ tỷ giá 31000) -> 31,000
        if num == int(num):
            return f"{int(num):,}"
        # Nếu là số thập phân (ví dụ 9.3) -> 9.3
        else:
            return f"{num:,.2f}".rstrip('0').rstrip('.')
    except:
        return str(val)

def tinh_toan_bao_gia(df, ty_gia_moi):
    """Tính toán logic và áp dụng format cho tất cả các cột số"""
    calc_df = df.copy()

    def clean_num(x):
        if pd.isna(x) or str(x).strip() in ['-', '']: return 0
        return pd.to_numeric(str(x).replace(',', '').strip(), errors='coerce') or 0

    # 1. Thực hiện tính toán logic
    gia_net_euro = calc_df['Giá Net Euro'].apply(clean_num)
    he_so = calc_df['Hệ số'].apply(clean_num)

    net_vnd = gia_net_euro * ty_gia_moi
    gia_ban = net_vnd * he_so
    profit = gia_ban - net_vnd
    margin = (profit / gia_ban).fillna(0)

    # 2. Áp dụng định dạng dấu "," cho CÁC CỘT TÍNH TOÁN MỚI
    df['Giá Net VND'] = net_vnd.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df['Giá bán'] = gia_ban.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df['Profit (Lợi nhuận)'] = profit.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df['Margin (Biên lợi nhuận)'] = margin.apply(lambda x: f"{x:.0%}")

    # 3. Áp dụng định dạng dấu "," cho CÁC CỘT CÓ SẴN từ GSheet (Unit Price, Tỷ giá,...)
    cols_to_format = ['Unit Price (VND)', 'Tỷ giá', 'Unit Price (Euro)', 'Thuế Nhập Khẩu VND']
    for col in cols_to_format:
        if col in df.columns:
            df[col] = df[col].apply(format_number_with_comma)

    return df

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery - Tra cứu", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    st.sidebar.title("⚙️ Cấu hình")
    ty_gia_input = st.sidebar.number_input("Nhập Tỷ giá Euro mới (VND):", value=31000, step=100)
    
    if st.sidebar.button("🔄 Làm mới dữ liệu"):
        st.cache_data.clear()
        st.rerun()

    df_raw = load_data(url, "SP List")

    if df_raw is not None:
        # Xử lý tính toán và định dạng lại toàn bộ bảng
        df_final = tinh_toan_bao_gia(df_raw, ty_gia_input)
        
        st.header("🔍 Hệ thống Tra cứu Phụ tùng")
        
        search_query = st.text_input("Nhập Part number (Dùng dấu ; để tìm nhiều mã):")
        
        if search_query:
            list_ma = [s.strip() for s in search_query.split(';') if s.strip()]
            df_final['Part number'] = df_final['Part number'].astype(str)
            result = df_final[df_final['Part number'].isin(list_ma)]
            
            if not result.empty:
                st.success(f"Tìm thấy {len(result)} kết quả")
                st.dataframe(result, use_container_width=True, hide_index=True)
            else:
                st.warning("Không tìm thấy mã.")
        else:
            st.dataframe(df_final, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
