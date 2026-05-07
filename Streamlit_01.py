import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import math

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=60)
def load_all_data(url_link):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Tải các tab cần thiết
        df_sp = conn.read(spreadsheet=url_link, worksheet="SP List", ttl=0)
        df_mst = conn.read(spreadsheet=url_link, worksheet="Customer_MST", ttl=0)
        df_contact = conn.read(spreadsheet=url_link, worksheet="Customer_Contact", ttl=0)
        df_machines = conn.read(spreadsheet=url_link, worksheet="List of machines", ttl=0)
        df_staff = conn.read(spreadsheet=url_link, worksheet="Staff", ttl=0)
        
        # Làm sạch tên cột (bỏ xuống dòng)
        for df in [df_sp, df_mst, df_contact, df_machines, df_staff]:
            df.columns = [c.replace('\n', ' ').strip() for c in df.columns]
        return df_sp, df_mst, df_contact, df_machines, df_staff
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None, None, None, None, None

def format_as_int_str(val):
    if pd.isna(val) or str(val).strip() in ['-', '']: return ""
    try: return str(int(float(str(val).replace(',', '').strip())))
    except: return str(val).strip()

def roundup_to_10k(x):
    if x == 0: return 0
    return math.ceil(x / 10000) * 10000

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    # Khởi tạo giỏ hàng nếu chưa có
    if 'cart' not in st.session_state:
        st.session_state.cart = []
    if 'sub_action' not in st.session_state:
        st.session_state.sub_action = None

    # CSS tinh chỉnh khoảng cách
    st.markdown("""
        <style>
        .stVerticalBlock { gap: 0.8rem; }
        .address-box { margin-top: 15px; margin-bottom: 20px; padding: 12px; background-color: #f8f9fa; border-left: 5px solid #ff4b4b; border-radius: 4px; }
        .stButton button { border-radius: 5px; }
        </style>
    """, unsafe_allow_html=True)

    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
    df_sp_raw, df_mst, df_contact, df_machines, df_staff = load_all_data(url)

    if df_sp_raw is not None:
        # MENU CHÍNH
        col_m1, col_m2, _, _, _ = st.columns(5)
        with col_m1:
            if st.button("➕ Tạo Báo Giá", use_container_width=True): st.session_state.sub_action = "create"
        with col_m2:
            if st.button("🔍 Tra Cứu", use_container_width=True): st.session_state.sub_action = "search"

        if st.session_state.sub_action == "create":
            st.divider()
            
            # --- PHẦN 1: THÔNG TIN KHÁCH HÀNG ---
            c1, c2 = st.columns(2)
            with c1:
                selected_customer = st.selectbox("🎯 Chọn tên khách hàng:", options=sorted(df_mst['Customer name'].unique()))
                cust_info = df_mst[df_mst['Customer name'] == selected_customer].iloc[0]
                c_no = format_as_int_str(cust_info['Customer no'])
                st.write(f"**Customer no:** {c_no} | **MST:** {format_as_int_str(cust_info['Mã số thuế'])}")
                
                # Machine Number
                df_machines['Customer no'] = df_machines['Customer no'].apply(format_as_int_str)
                m_list = df_machines[df_machines['Customer no'] == c_no]['Customer Machine'].tolist()
                st.selectbox("⚙️ Machine number:", options=m_list if m_list else ["N/A"])

            with c2:
                df_contact['Customer no'] = df_contact['Customer no'].apply(format_as_int_str)
                cont_list = df_contact[df_contact['Customer no'] == c_no]['Customer contact'].tolist()
                st.selectbox("👤 Contact Person:", options=cont_list if cont_list else ["N/A"])
                
                staff_list = df_staff['Name'].tolist() if df_staff is not None else ["Admin"]
                st.selectbox("✍️ Người lập báo giá:", options=staff_list)

            st.markdown(f'<div class="address-box"><b>📍 Địa chỉ:</b><br>{cust_info["Full Information customer"]}</div>', unsafe_allow_html=True)
            st.divider()

            # --- PHẦN 2: TÌM KIẾM VÀ THÊM PHỤ TÙNG ---
            st.subheader("🔍 Tìm Part Number")
            col_search, col_add = st.columns([4, 1])
            
            with col_search:
                part_search = st.text_input("Nhập mã phụ tùng:", placeholder="Gõ Part Number vào đây và nhấn Enter...")
            
            if part_search:
                # Tìm kiếm trong cột B (Part number) của tab SP List
                match = df_sp_raw[df_sp_raw['Part number'].astype(str) == part_search.strip()]
                if not match.empty:
                    item = match.iloc[0]
                    with col_add:
                        st.write("##") # Căn lề nút nhấn
                        if st.button("➕ Thêm vào bảng", use_container_width=True, type="primary"):
                            # Tạo dictionary thông tin mới
                            new_item = {
                                "Part Number": item['Part number'],
                                "Part name": item['Part name'], # Cột E
                                "Qty": 1,
                                "Unit": item['Unit'], # Cột H
                                "VAT": item['VAT'],  # Cột M
                                "Unit Price": item['Giá bán'] # Cột J
                            }
                            st.session_state.cart.append(new_item)
                            st.toast(f"Đã thêm {item['Part number']}!")
                else:
                    st.error("Mã phụ tùng không tồn tại trong SP List!")

            # --- PHẦN 3: BẢNG DANH SÁCH PHỤ TÙNG (EDITABLE TABLE) ---
            st.markdown("### 📋 Danh sách phụ tùng")
            if st.session_state.cart:
                df_cart = pd.DataFrame(st.session_state.cart)
                # Đánh số thứ tự No.
                df_cart.insert(0, 'No', range(1, len(df_cart) + 1))
                
                # Sử dụng data_editor để khách hàng có thể sửa Qty
                edited_df = st.data_editor(
                    df_cart,
                    column_config={
                        "No": st.column_config.NumberColumn("No", width="small"),
                        "Part Number": st.column_config.TextColumn("Part Number", disabled=True),
                        "Part name": st.column_config.TextColumn("Part name", width="large", disabled=True),
                        "Qty": st.column_config.NumberColumn("Qty", min_value=1, step=1),
                        "Unit": st.column_config.TextColumn("Unit", width="small", disabled=True),
                        "VAT": st.column_config.TextColumn("VAT", width="small", disabled=True),
                        "Unit Price": st.column_config.TextColumn("Unit Price", disabled=True)
                    },
                    use_container_width=True,
                    hide_index=True,
                    key="cart_editor"
                )
                
                if st.button("🗑️ Xoá toàn bộ bảng"):
                    st.session_state.cart = []
                    st.rerun()
            else:
                st.info("Chưa có phụ tùng nào được chọn. Hãy nhập mã ở trên.")

            # --- PHẦN 4: NÚT ĐIỀU KHIỂN DƯỚI CÙNG ---
            st.markdown("<br>" * 15, unsafe_allow_html=True)
            col_save, col_order, _ = st.columns([1.5, 1.5, 5])
            with col_save:
                st.button("💾 Lưu Báo Giá", use_container_width=True)
            with col_order:
                st.button("🛒 Đặt Hàng", use_container_width=True)

if __name__ == "__main__":
    main()
