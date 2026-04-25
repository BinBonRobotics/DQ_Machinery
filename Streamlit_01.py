import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Cấu hình giao diện
st.set_page_config(page_title="Tra cứu vật tư DQ", layout="wide")
st.title("🛡️ D&Q Machinery - Homag Partner")

# 2. Link file
url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

# --- PHẦN TỐI ƯU TỐC ĐỘ (CACHE) ---
# ttl=3600 nghĩa là dữ liệu sẽ được "đóng băng" trong 1 tiếng (3600 giây)
# Sau 1 tiếng nó mới tự động tải mới từ Google Sheets 1 lần
@st.cache_data(ttl=3600)
def load_data_from_sheets(url_link):
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Đọc đúng sheet "SP-List"
    data = conn.read(spreadsheet=url_link, worksheet="SP-List", ttl=0)
    return data

try:
    # Gọi hàm đã có cache
    df = load_data_from_sheets(url)

    # 5. Giao diện tìm kiếm
    col1, col2 = st.columns([1, 3]) 
    with col1:
        search_query = st.text_input("Nhập Part numbers:", placeholder="Ví dụ: 4014020227; 2056186140")

    if search_query:
        # Tách chuỗi người dùng nhập
        list_ma = [s.strip() for s in search_query.replace(',', ';').split(';') if s.strip()]
        
        # Tìm các Part number trong danh sách
        result = df[df['Part number'].astype(str).isin(list_ma)]
        
        if not result.empty:
            st.success(f"🔍 Đã tìm thấy {len(result)} mã hàng.")
            st.table(result)
            
            # Kiểm tra mã nào bị thiếu
            ma_tim_thay = result['Part number'].astype(str).tolist()
            ma_khong_thay = [m for m in list_ma if m not in ma_tim_thay]
            if ma_khong_thay:
                st.warning(f"⚠️ Không tìm thấy mã: {', '.join(ma_khong_thay)}")
        else:
            st.warning("❌ Không tìm thấy mã nào trong danh sách trên.")
    else:
        st.info("💡 Nhập một hoặc nhiều mã (cách nhau bởi dấu ;) để kiểm tra.")
        # Dùng dataframe để hiển thị cho gọn, có thanh cuộn
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
