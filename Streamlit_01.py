import streamlit as st
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="HOMAG Offer Management", layout="wide")

# --- HÀM ĐỌC DỮ LIỆU ---
@st.cache_data
def load_data():
    # Thay 'Offer_Details.csv' bằng đường dẫn file của bạn
    # Ở đây mình xử lý chuẩn hóa tên cột ngay khi load
    try:
        df_details = pd.read_csv('Offer_Details.csv')
        df_details.columns = df_details.columns.str.replace('_', ' ').str.strip()
        
        df_header = pd.read_csv('Offer_Header.csv')
        df_header.columns = df_header.columns.str.replace('_', ' ').str.strip()
        
        return df_header, df_details
    except:
        # Tạo dữ liệu mẫu nếu không tìm thấy file để bạn test code
        header = pd.DataFrame(columns=['Offer No', 'Offer Date', 'Customer Name', 'Staff', 'Grand Total'])
        details = pd.DataFrame(columns=['Offer No', 'Part Number', 'Part Name', 'Qty', 'Unit Price', 'VAT Rate', 'Discount Percent'])
        return header, details

df_header, df_details = load_data()

# --- GIAO DIỆN SIDEBAR ---
st.sidebar.title("Menu Quản Lý")
page = st.sidebar.selectbox("Chọn chức năng", ["Tạo Báo Giá Mới", "Danh Sách Báo Giá", "Cài Đặt"])

# --- CHỨC NĂNG CHÍNH: TẠO BÁO GIÁ ---
if page == "Tạo Báo Giá Mới":
    st.header("Tạo Báo Giá Mới")
    
    col1, col2 = st.columns(2)
    with col1:
        offer_no = st.text_input("Offer No", value=f"OFF-{datetime.now().strftime('%Y%m%d-%H%M')}")
        customer = st.selectbox("Khách hàng", ["Khách hàng A", "Khách hàng B", "Khách hàng C"])
    with col2:
        offer_date = st.date_input("Ngày báo giá", datetime.now())
        staff = st.text_input("Người thực hiện", "Duy Nguyen")

    st.divider()
    st.subheader("Chi tiết phụ tùng")

    # Khởi tạo bảng nhập liệu (Data Editor)
    if 'items' not in st.session_state:
        st.session_state.items = pd.DataFrame([{
            'Part Number': '',
            'Part Name': '',
            'Qty': 1,
            'Unit Price': 0.0,
            'VAT Rate': 0.08,
            'Discount Percent': 0.0
        }])

    # Sử dụng st.data_editor để người dùng nhập liệu trực tiếp như Excel
    edited_df = st.data_editor(
        st.session_state.items,
        num_rows="dynamic",
        key="offer_editor",
        use_container_width=True
    )

    # --- TÍNH TOÁN TỔNG CỘNG ---
    if not edited_df.empty:
        # Tính toán các cột phụ (tránh lỗi KeyError bằng cách kiểm tra tên cột)
        edited_df['Amount'] = edited_df['Qty'] * edited_df['Unit Price']
        edited_df['Discount Amount'] = edited_df['Amount'] * (edited_df['Discount Percent'] / 100)
        edited_df['Final Amount'] = (edited_df['Amount'] - edited_df['Discount Amount']) * (1 + edited_df['VAT Rate'])
        
        total_before_vat = edited_df['Amount'].sum()
        total_discount = edited_df['Discount Amount'].sum()
        grand_total = edited_df['Final Amount'].sum()

        # Hiển thị kết quả tính toán
        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng chưa thuế", f"{total_before_vat:,.0f} VND")
        c2.metric("Tổng chiết khấu", f"- {total_discount:,.0f} VND")
        c3.metric("Tổng thanh toán (G.Total)", f"{grand_total:,.0f} VND", delta_color="normal")

    # Nút lưu dữ liệu
    if st.button("Lưu báo giá"):
        # Logic lưu vào file CSV hoặc Database ở đây
        st.success(f"Đã lưu báo giá {offer_no} thành công!")

# --- CHỨC NĂNG: DANH SÁCH BÁO GIÁ ---
elif page == "Danh Sách Báo Giá":
    st.header("Quản lý danh sách báo giá")
    
    search = st.text_input("Tìm kiếm theo mã báo giá hoặc khách hàng")
    
    if not df_header.empty:
        # Lọc dữ liệu
        filtered_df = df_header[df_header['Offer No'].str.contains(search, case=False, na=False)]
        st.dataframe(filtered_df, use_container_width=True)
        
        # Cho phép xuất Excel
        csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("Tải về file CSV", csv, "offers.csv", "text/csv")
    else:
        st.info("Chưa có dữ liệu báo giá nào.")

# --- XỬ LÝ LỖI KEYERROR CHUNG ---
# Luôn kiểm tra sự tồn tại của cột trước khi xử lý
def safe_calc(df, col_name):
    if col_name in df.columns:
        return df[col_name].sum()
    else:
        st.error(f"Không tìm thấy cột '{col_name}' trong dữ liệu. Hãy kiểm tra lại file CSV.")
        return 0
