def chuc_nang_bao_gia(df_vattu, df_customer):
    """Giao diện tạo báo giá chuyên nghiệp với layout tối ưu"""
    st.header("📄 Tạo Báo giá Phụ tùng")
    
    if df_customer is None:
        st.error("Không thể tải dữ liệu khách hàng.")
        return

    st.subheader("1. Thông tin khách hàng")
    
    # ĐIỀU CHỈNH: Thu ngắn thanh chọn khách hàng bằng tỷ lệ cột [2, 6]
    col_select, col_empty = st.columns([2, 6])
    with col_select:
        # Tham chiếu chính xác vào cột 'Customer-name'
        list_customers = sorted(df_customer['Customer-name'].dropna().unique().tolist())
        selected_customer = st.selectbox("Chọn khách hàng:", ["-- Chọn khách hàng --"] + list_customers)

    if selected_customer != "-- Chọn khách hàng --":
        # Lọc thông tin của khách hàng được chọn
        cus_info = df_customer[df_customer['Customer-name'] == selected_customer]
        
        # Layout hiển thị thông tin chi tiết
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Customer no:", value=str(cus_info.iloc[0]['Customer no']), disabled=True)
            # Lọc Machine-Type dựa trên khách hàng đã chọn
            list_m_type = sorted(cus_info['Machine-Type'].dropna().unique().tolist())
            selected_m_type = st.selectbox("Machine Type:", list_m_type)
        
        with col2:
            st.text_input("Tax Code:", value=str(cus_info.iloc[0]['Tax Code']), disabled=True)
            # Lọc Machine No theo Machine-Type đã chọn
            list_m_no = sorted(cus_info[cus_info['Machine-Type'] == selected_m_type]['Machine No'].dropna().unique().tolist())
            selected_m_no = st.selectbox("Machine No:", list_m_no)
            
        with col3:
            st.text_area("Address:", value=str(cus_info.iloc[0]['Address']), disabled=True, height=100)

        st.divider()
        # ... (Các phần code tiếp theo giữ nguyên)
