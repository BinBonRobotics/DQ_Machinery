import streamlit as st
from streamlit_gsheets import GSheetsConnection

# 1. Cấu hình giao diện
st.set_page_config(page_title="Tra cứu vật tư DQ", layout="wide")
st.title("🛡️ D&Q Machinery - Homag Partner")
st.title("🛡️Deutsch & Qualität Machinery - Homag Partner")
# 2. Link file - dùng link sạch
url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

try:
    # 3. Kết nối
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 4. Đọc dữ liệu từ sheet cụ thể: "SP-List"
    # Thêm tham số worksheet ở đây để chỉ định đúng tên sheet mới của bạn
    df = conn.read(spreadsheet=url, worksheet="SP-List", ttl=0)

    # 5. Giao diện tìm kiếm
    col1, col2 = st.columns([1, 3]) 
    with col1:
        search_query = st.text_input("Nhập Part numbers:", placeholder="Ví dụ: 4014020227; 2056186140")

    if search_query:
        # Tách chuỗi người dùng nhập thành danh sách các mã
        list_ma = [s.strip() for s in search_query.replace(',', ';').split(';') if s.strip()]
        
        # Lọc dữ liệu: Tìm các Part number trong danh sách list_ma
        result = df[df['Part number'].astype(str).isin(list_ma)]
        
        if not result.empty:
            st.success(f"🔍 Đã tìm thấy {len(result)} mã trong danh sách bạn nhập.")
            st.table(result)
            
            # Báo lỗi nếu có mã nhập vào nhưng không tìm thấy trong dữ liệu
            ma_tim_thay = result['Part number'].astype(str).tolist()
            ma_khong_thay = [m for m in list_ma if m not in ma_tim_thay]
            if ma_khong_thay:
                st.warning(f"⚠️ Không tìm thấy mã: {', '.join(ma_khong_thay)}")
        else:
            st.warning("❌ Không tìm thấy mã nào trong danh sách trên.")
    else:
        st.info("💡 Nhập một hoặc nhiều mã (cách nhau bởi dấu ;) để kiểm tra.")
        # Hiển thị toàn bộ dữ liệu mẫu ban đầu
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
