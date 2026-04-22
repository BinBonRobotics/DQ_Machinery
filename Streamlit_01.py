import streamlit as st
from streamlit_gsheets import GSheetsConnection

# 1. Cấu hình trang
st.set_page_config(page_title="Tra cứu vật tư bảo mật", layout="centered")

st.title("🛡️ Hệ thống tra cứu mã hàng (Bảo mật)")

# 2. Link file Google Sheet của bạn (Dù link này bị lộ, người khác cũng không thể vào xem)
url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHx..." 

try:
    # 3. Kết nối dữ liệu sử dụng Service Account
    # Streamlit sẽ tự động tìm thông tin trong mục 'Secrets' mà bạn đã dán
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # QUAN TRỌNG: Thêm tham số spreadsheet vào hàm read để chỉ định file cần đọc
    df = conn.read(spreadsheet=url, ttl="10m")

    # 4. GIAO DIỆN TRA CỨU
    st.divider() 
    
    search_query = st.text_input("Nhập Part number cần tìm:", placeholder="Ví dụ: 123456...")

    if search_query:
        # Lọc dữ liệu: Tìm trong cột 'Part number'
        result = df[df['Part number'].astype(str).str.contains(search_query, case=False)]

        if not result.empty:
            st.success(f"Tìm thấy {len(result)} mã hàng tương ứng!")
            st.table(result)
        else:
            st.warning("⚠️ Không tìm thấy Part number này trong hệ thống.")
    else:
        st.info("💡 Mẹo: Nhập mã vào ô trên để lọc nhanh.")
        # Lưu ý bảo mật: Bạn có thể ẩn dòng st.dataframe(df) này nếu không muốn hiện toàn bộ giá khi chưa tìm kiếm
        st.write("Danh sách tổng quát:")
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Có lỗi xảy ra: {e}")
    st.info("Mẹo: Đảm bảo bạn đã dán thông tin Service Account vào mục 'Secrets' trên Streamlit Cloud.")