import streamlit as st
from streamlit_gsheets import GSheetsConnection

# 1. Cấu hình trang web
st.set_page_config(page_title="Hệ thống tra cứu sản phẩm", layout="wide")

st.title("🚀 Kết nối thành công Google Sheets!")

# 2. Link file Google Sheet của bạn
# Dán link bạn vừa copy vào giữa hai dấu ngoặc kép dưới đây
url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8/edit?usp=sharing"

# 3. Tạo kết nối và đọc dữ liệu
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=url, ttl=0) # ttl=0 để luôn lấy dữ liệu mới nhất khi load lại

    # 4. Hiển thị dữ liệu lên giao diện
    st.success("Đã kết nối với file: Test_Streamlit")
    
    st.subheader("Bảng dữ liệu sản phẩm:")
    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Có lỗi xảy ra: {e}")
    st.info("Mẹo: Đảm bảo bạn đã cài đặt thư viện 'st-gsheets-connection'")