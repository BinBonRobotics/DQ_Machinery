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
        
        # Làm sạch tên cột trước khi xử lý
        data.columns = data.columns.str.strip()
        
        # Xử lý Part number sạch sẽ
        if 'Part number' in data.columns:
            data['Part number'] = data['Part number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            data['Part number'] = data['Part number'].replace('nan', '')
            
        return data
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None

def tinh_toan_bao_gia(df, ty_gia):
    """Hàm xử lý tính toán dựa trên các tiêu đề cột bạn yêu cầu"""
    # Chuyển đổi các cột số liệu về dạng numeric để tính toán (tránh lỗi định dạng text)
    df['Giá Net Euro'] = pd.to_numeric(df['Giá Net Euro'], errors='coerce').fillna(0)
    df['Hệ số'] = pd.to_numeric(df['Hệ số'], errors='coerce').fillna(1.0) # Mặc định hệ số 1 nếu trống

    # 1. Tính Giá Net VND
    df['Giá Net VND'] = df['Giá Net Euro'] * ty_gia
    
    # 2. Tính Giá bán
    df['Giá bán'] = df['Giá Net VND'] * df['Hệ số']
    
    # 3. Tính Profit (Lợi nhuận)
    df['Profit (Lợi nhuận)'] = df['Giá bán'] - df['Giá Net VND']
    
    # 4. Tính Margin (Biên lợi nhuận)
    # Tránh chia cho 0 bằng .where
    df['Margin (Biên lợi nhuận)'] = (df['Profit (Lợi nhuận)'] / df['Giá bán']).fillna(0)
    
    return df

def chuc_nang_tra_cuu_vat_tu(df_vattu, ty_gia):
    st.header("🔍 Hệ thống Quản lý Phụ tùng (SP List)")
    
    # Thực hiện tính toán báo giá trước khi hiển thị
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

def hien_thi_dataframe(df):
    """Hàm format hiển thị tiền tệ và phần trăm"""
    display_df = df.copy()
    display_df.index = display_df.index + 2
    
    # Format hiển thị (không làm thay đổi giá trị thực tế của df gốc)
    st.dataframe(
        display_df.style.format({
            "Giá Net Euro": "{:,.2f} €",
            "Giá Net VND": "{:,.0f} ₫",
            "Giá bán": "{:,.0f} ₫",
            "Profit (Lợi nhuận)": "{:,.0f} ₫",
            "Margin (Biên lợi nhuận)": "{:.2%}"
        }),
        use_container_width=True
    )

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery - SP List", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    # --- SIDEBAR ---
    st.sidebar.title("⚙️ D&Q Machinery")
    
    # Thêm cấu hình tỷ giá
    ty_gia = st.sidebar.number_input("Tỷ giá Euro (VND):", value=27500, step=100)
    
    if st.sidebar.button("🔄 Làm mới dữ liệu (Clear Cache)"):
        st.cache_data.clear()
        st.rerun()

    # --- TẢI VÀ XỬ LÝ DỮ LIỆU ---
    df_raw = load_data(url, "SP List")

    if df_raw is not None:
        chuc_nang_tra_cuu_vat_tu(df_raw, ty_gia)

if __name__ == "__main__":
    main()
