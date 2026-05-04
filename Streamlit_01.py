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
        
        # CHỈNH SỬA QUAN TRỌNG: Làm sạch tên cột (bỏ khoảng trắng và ký tự xuống dòng \n)
        data.columns = [c.replace('\n', ' ').strip() for c in data.columns]
        
        # Chỉ lấy phạm vi từ cột B đến U (tương ứng chỉ số 1 đến 21 trong Pandas)
        if data.shape[1] >= 21:
            data = data.iloc[:, 1:21]
            
        return data
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None

def format_hien_thi(val):
    """Giữ nguyên định dạng của GSheet: 11,197,000 hoặc 9.3"""
    if pd.isna(val) or val == "": return "-"
    # Nếu dữ liệu đã có dấu phẩy (dạng string từ GSheet), giữ nguyên
    return str(val)

def tinh_toan_bao_gia(df, ty_gia_moi):
    """
    Tính toán dựa trên các tên cột thực tế trong file CSV mới của bạn
    """
    # Tạo bản sao để tính toán số học
    calc_df = df.copy()

    def clean_num(x):
        if pd.isna(x) or str(x).strip() == '-': return 0
        # Xóa dấu phẩy và khoảng trắng để chuyển về số
        return pd.to_numeric(str(x).replace(',', '').strip(), errors='coerce') or 0

    # Lấy giá trị số từ các cột (Tên cột đã được strip ở bước load_data)
    gia_net_euro = calc_df['Giá Net Euro'].apply(clean_num)
    he_so = calc_df['Hệ số'].apply(clean_num)

    # Tính toán các giá trị mới dựa trên Tỷ giá người dùng nhập vào
    net_vnd = gia_net_euro * ty_gia_moi
    gia_ban = net_vnd * he_so
    profit = gia_ban - net_vnd
    # Tránh chia cho 0
    margin = (profit / gia_ban).fillna(0)

    # Cập nhật lại định dạng hiển thị (Có dấu phẩy phân cách ngàn)
    df['Giá Net VND'] = net_vnd.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df['Giá bán'] = gia_ban.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df['Profit (Lợi nhuận)'] = profit.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df['Margin (Biên lợi nhuận)'] = margin.apply(lambda x: f"{x:.0%}")

    return df

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery - Tra cứu", layout="wide")
    
    # Link Google Sheet của bạn
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    st.sidebar.title("⚙️ Cấu hình")
    ty_gia = st.sidebar.number_input("Nhập Tỷ giá Euro mới (VND):", value=31000, step=100)
    
    if st.sidebar.button("🔄 Làm mới dữ liệu"):
        st.cache_data.clear()
        st.rerun()

    df_raw = load_data(url, "SP List")

    if df_raw is not None:
        # Tính toán lại các cột dựa trên tỷ giá mới
        df_final = tinh_toan_bao_gia(df_raw, ty_gia)
        
        st.header("🔍 Hệ thống Tra cứu Phụ tùng")
        
        # Thanh tìm kiếm
        search_query = st.text_input("Nhập Part number (Ví dụ: 3608080970; 4010030087):")
        
        if search_query:
            list_ma = [s.strip() for s in search_query.split(';') if s.strip()]
            # Ép kiểu string để so sánh chính xác Part number
            df_final['Part number'] = df_final['Part number'].astype(str)
            result = df_final[df_final['Part number'].isin(list_ma)]
            
            if not result.empty:
                st.success(f"Tìm thấy {len(result)} kết quả")
                st.dataframe(result, use_container_width=True, hide_index=True)
            else:
                st.warning("Không tìm thấy mã này.")
        else:
            st.info("Hiển thị danh sách đầy đủ (Cột B -> U)")
            st.dataframe(df_final, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
