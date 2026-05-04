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
        
        # CHỈNH SỬA: Làm sạch tên cột
        data.columns = [c.replace('\n', ' ').strip() for c in data.columns]
        
        # CHỈNH SỬA TẠI ĐÂY: Lấy từ cột A (chỉ số 0) đến cột U (chỉ số 21)
        if data.shape[1] >= 21:
            data = data.iloc[:, 0:21] # Thay 1:21 thành 0:21 để lấy thêm cột A
            
        return data
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None

def tinh_toan_bao_gia(df, ty_gia_moi):
    """Tính toán lại các cột dựa trên tỷ giá thực tế"""
    calc_df = df.copy()

    def clean_num(x):
        if pd.isna(x) or str(x).strip() == '-' or str(x).strip() == '': return 0
        return pd.to_numeric(str(x).replace(',', '').strip(), errors='coerce') or 0

    # Lấy giá trị số để tính toán
    gia_net_euro = calc_df['Giá Net Euro'].apply(clean_num)
    he_so = calc_df['Hệ số'].apply(clean_num)

    # Logic tính toán
    net_vnd = gia_net_euro * ty_gia_moi
    gia_ban = net_vnd * he_so
    profit = gia_ban - net_vnd
    margin = (profit / gia_ban).fillna(0)

    # Cập nhật hiển thị có dấu phẩy phân cách ngàn
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
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    st.sidebar.title("⚙️ Cấu hình")
    ty_gia = st.sidebar.number_input("Nhập Tỷ giá Euro mới (VND):", value=31000, step=100)
    
    if st.sidebar.button("🔄 Làm mới dữ liệu"):
        st.cache_data.clear()
        st.rerun()

    df_raw = load_data(url, "SP List")

    if df_raw is not None:
        # Tính toán lại dữ liệu
        df_final = tinh_toan_bao_gia(df_raw, ty_gia)
        
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
            # Hiển thị đầy đủ từ cột A đến U
            st.info("Hiển thị danh sách đầy đủ (Cột A -> U)")
            st.dataframe(df_final, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
