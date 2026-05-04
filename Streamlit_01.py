import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import math

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=60)
def load_data(url_link, sheet_name):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=url_link, worksheet=sheet_name, ttl=0)
        
        # Làm sạch tên cột
        data.columns = [c.replace('\n', ' ').strip() for c in data.columns]
        
        # Lấy từ cột A (0) đến cột U (21)
        if data.shape[1] >= 21:
            data = data.iloc[:, 0:21]
            
        return data
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None

def roundup_to_10k(x):
    """Mô phỏng hàm ROUNDUP(x, -4) của Excel/Google Sheets"""
    if x == 0: return 0
    # Chia cho 10,000, dùng ceil để làm tròn lên, rồi nhân lại 10,000
    return math.ceil(x / 10000) * 10000

def format_number_with_comma(val):
    if pd.isna(val) or str(val).strip() in ['-', '']: 
        return "-"
    try:
        num_str = str(val).replace(',', '').strip()
        num = float(num_str)
        if num == int(num):
            return f"{int(num):,}"
        else:
            return f"{num:,.2f}".rstrip('0').rstrip('.')
    except:
        return str(val)

def tinh_toan_bao_gia(df, ty_gia_moi):
    calc_df = df.copy()

    def clean_num(x):
        if pd.isna(x) or str(x).strip() in ['-', '']: return 0
        return pd.to_numeric(str(x).replace(',', '').strip(), errors='coerce') or 0

    # 1. Thực hiện tính toán logic
    gia_net_euro = calc_df['Giá Net Euro'].apply(clean_num)
    he_so = calc_df['Hệ số'].apply(clean_num)

    # Tính Giá Net VND thô
    raw_net_vnd = gia_net_euro * ty_gia_moi
    # Áp dụng ROUNDUP(..., -4) cho Giá Net VND
    net_vnd = raw_net_vnd.apply(roundup_to_10k)
    
    # Tính Giá bán dựa trên Giá Net VND đã làm tròn
    raw_gia_ban = net_vnd * he_so
    # Áp dụng ROUNDUP(..., -4) cho Giá bán
    gia_ban = raw_gia_ban.apply(roundup_to_10k)
    
    profit = gia_ban - net_vnd
    margin = (profit / gia_ban).fillna(0)

    # 2. Cập nhật hiển thị
    df['Giá Net VND'] = net_vnd.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df['Giá bán'] = gia_ban.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df['Profit (Lợi nhuận)'] = profit.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df['Margin (Biên lợi nhuận)'] = margin.apply(lambda x: f"{x:.0%}")

    # 3. Định dạng các cột số khác
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
        df_final = tinh_toan_bao_gia(df_raw, ty_gia_input)
        
        st.header("🔍 Hệ thống Tra cứu Phụ tùng")
        
        search_query = st.text_input("Nhập Part number (Dùng dấu ; để tìm nhiều mã):")
        
        if search_query:
            list_ma = [s.strip() for s in search_query.split(';') if s.strip()]
            df_final['Part number'] = df_final['Part number'].astype(str)
            result = df_final[df_final['Part number'].isin(list_ma)]
            st.dataframe(result, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_final, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
