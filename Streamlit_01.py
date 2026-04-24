import streamlit as st
from streamlit_gsheets import GSheetsConnection

# 1. Cấu hình giao diện
st.set_page_config(page_title="Tra cứu vật tư DQ", layout="wide")
st.title("🛡️ D&Q Machinery - Homag Partner")

# 2. Link file - dùng link sạch (đã bỏ phần /edit phía sau)
url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

try:
    # 3. Kết nối (Streamlit sẽ tự tìm trong mục Secrets)
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 4. Đọc dữ liệu (Sử dụng tham số spreadsheet)
    df = conn.read(spreadsheet=url, ttl=0)

    # 5. Giao diện tìm kiếm
# 5. Giao diện tìm kiếm - Làm ngắn lại bằng cách chia cột
    col1, col2 = st.columns([1, 6]) 
    with col1:
        # Nhắc người dùng dùng dấu chấm phẩy hoặc dấu phẩy để ngăn cách
        search_query = st.text_input("Nhập Part numbers:", placeholder="Ví dụ: 4014020227; 2056186140")

    if search_query:
        # BƯỚC QUAN TRỌNG: Tách chuỗi người dùng nhập thành danh sách các mã
        # Thay thế dấu phẩy bằng dấu chấm phẩy, sau đó tách theo dấu chấm phẩy
        list_ma = [s.strip() for s in search_query.replace(',', ';').split(';') if s.strip()]
        
        # Lọc dữ liệu: Tìm các Part number nằm trong danh sách list_ma
        # .isin() là hàm cực mạnh để tìm nhiều giá trị cùng lúc
        result = df[df['Part number'].astype(str).isin(list_ma)]
        
        if not result.empty:
            st.success(f"🔍 Đã tìm thấy {len(result)} mã trong danh sách bạn nhập.")
            st.table(result)
            
            # Nếu có mã nào không tìm thấy, báo cho người dùng biết
            ma_tim_thay = result['Part number'].astype(str).tolist()
            ma_khong_thay = [m for m in list_ma if m not in ma_tim_thay]
            if ma_khong_thay:
                st.warning(f"⚠️ Không tìm thấy: {', '.join(ma_khong_thay)}")
        else:
            st.warning("❌ Không tìm thấy mã nào trong danh sách trên.")
    else:
        st.info("💡 Nhập một hoặc nhiều mã (cách nhau bởi dấu ;) để kiểm tra.")
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
