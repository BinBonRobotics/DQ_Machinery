import streamlit as st
from streamlit_gsheets import GSheetsConnection

# 1. Cấu hình giao diện
st.set_page_config(page_title="Tra cứu vật tư DQ", layout="wide")
st.title("🛡️ Hệ thống tra cứu bảo mật")

# 2. Link file - dùng link sạch (đã bỏ phần /edit phía sau)
url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

try:
    # 3. Kết nối (Streamlit sẽ tự tìm trong mục Secrets)
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 4. Đọc dữ liệu (Sử dụng tham số spreadsheet)
    df = conn.read(spreadsheet=url, ttl=0)

    # 5. Giao diện tìm kiếm
    search_query = st.text_input("Nhập Part number cần tìm:", placeholder="Ví dụ: 4014020621...")

    if search_query:
        result = df[df['Part number'].astype(str).str.contains(search_query, case=False)]
        if not result.empty:
            st.success(f"Tìm thấy {len(result)} mã hàng!")
            st.table(result)
        else:
            st.warning("⚠️ Không tìm thấy mã này.")
    else:
        st.info("💡 Nhập mã vào ô trên để kiểm tra giá.")
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
