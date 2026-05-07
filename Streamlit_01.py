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
        df_sp = conn.read(spreadsheet=url_link, worksheet="SP List", ttl=0)
        df_mst = conn.read(spreadsheet=url_link, worksheet="Customer_MST", ttl=0)
        df_contact = conn.read(spreadsheet=url_link, worksheet="Customer_Contact", ttl=0)
        df_machines = conn.read(spreadsheet=url_link, worksheet="List of machines", ttl=0)
        df_staff = conn.read(spreadsheet=url_link, worksheet="Staff", ttl=0)
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
    
    if 'sub_action' not in st.session_state:
        st.session_state.sub_action = None

    # CSS tinh chỉnh khoảng cách
    st.markdown("""
        <style>
        .stVerticalBlock { gap: 0.8rem; } /* Tăng khoảng cách chung giữa các block */
        .stSelectbox { margin-bottom: 5px; }
        div[data-testid="stMarkdownContainer"] p { margin-bottom: 5px; }
        /* Tạo khoảng cách riêng cho phần địa chỉ */
        .address-box { margin-top: 15px; margin-bottom: 15px; padding: 10px; background-color: #f0f2f6; border-radius: 5px; }
        </style>
    """, unsafe_allow_html=True)

    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    # SIDEBAR
    st.sidebar.title("⚙️ Cấu hình")
    ty_gia_input = st.sidebar.number_input("Tỷ giá Euro:", value=31000, step=100)
    if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    menu_selection = st.sidebar.radio("📂 Danh mục:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])

    df_sp_raw, df_mst, df_contact, df_machines, df_staff = load_all_data(url)

    if df_sp_raw is not None:
        if menu_selection == "📄 Báo Giá Phụ Tùng":
            col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)
            with col_btn1:
                if st.button("➕ Tạo Báo Giá", use_container_width=True): st.session_state.sub_action = "create"
            with col_btn2:
                if st.button("🔍 Tra Cứu Đơn Hàng", use_container_width=True): st.session_state.sub_action = "search"
            
            st.divider()

            if st.session_state.sub_action == "create":
                # --- KHỐI THÔNG TIN KHÁCH HÀNG ---
                col1, col2 = st.columns(2)
                with col1:
                    customer_list = sorted(df_mst['Customer name'].astype(str).unique().tolist())
                    selected_customer = st.selectbox("🎯 Customer name:", options=customer_list)
                    cust_info = df_mst[df_mst['Customer name'] == selected_customer].iloc[0]
                    c_no = format_as_int_str(cust_info['Customer no'])
                    st.markdown(f"**Customer no:** {c_no} &nbsp;&nbsp; | &nbsp;&nbsp; **MST:** {format_as_int_str(cust_info['Mã số thuế'])}")
                    
                    df_machines['Customer no'] = df_machines['Customer no'].apply(format_as_int_str)
                    f_machines = df_machines[df_machines['Customer no'] == c_no]
                    m_options = f_machines['Customer Machine'].dropna().unique().tolist()
                    st.selectbox("🛠️ Machine number:", options=m_options if m_options else ["Không có dữ liệu"])

                with col2:
                    df_contact['Customer no'] = df_contact['Customer no'].apply(format_as_int_str)
                    f_contacts = df_contact[df_contact['Customer no'] == c_no]
                    cont_options = f_contacts['Customer contact'].dropna().unique().tolist()
                    st.selectbox("👤 Contact Person:", options=cont_options if cont_options else ["Không có dữ liệu"])
                    
                    if df_staff is not None:
                        staff_list = df_staff['Name'].dropna().unique().tolist()
                        st.selectbox("✍️ Người lập báo giá:", options=staff_list)

                # --- ĐỊA CHỈ (Dùng CSS Class để tạo khoảng cách) ---
                st.markdown('<div class="address-box"><b>📍 Địa chỉ:</b><br>' + cust_info['Full Information customer'] + '</div>', unsafe_allow_html=True)
                
                st.markdown("---")

                # --- KHU VỰC TÌM PART NUMBER ---
                st.subheader("🔍 Tìm Part Number")
                part_input = st.text_input("Nhập Part Number để kiểm tra giá:", placeholder="Ví dụ: 3608080970...")

                if part_input:
                    # Tìm kiếm chính xác Part Number
                    result = df_sp_raw[df_sp_raw['Part number'].astype(str) == part_input.strip()]
                    
                    if not result.empty:
                        item = result.iloc[0]
                        # Tính toán giá tại chỗ dựa trên tỷ giá sidebar
                        net_euro = pd.to_numeric(str(item.get('Giá Net Euro', 0)).replace(',', ''), errors='coerce') or 0
                        hs = pd.to_numeric(str(item.get('Hệ số', 1.5)).replace(',', ''), errors='coerce') or 0
                        
                        net_vnd = roundup_to_10k(net_euro * ty_gia_input)
                        selling_price = roundup_to_10k(net_vnd * hs)

                        # Hiển thị thông tin tô vàng (Trình bày dạng thẻ thông tin)
                        st.success(f"✅ Đã tìm thấy phụ tùng: **{item.get('Part name', 'N/A')}**")
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.metric("Tên phụ tùng (VN)", item.get('Vietnamese', 'N/A'))
                            st.metric("Đơn vị", item.get('Unit', 'pc'))
                        with c2:
                            st.metric("Giá Net (Euro)", f"€ {net_euro:,.2f}")
                            st.metric("Giá Net (VND)", f"{net_vnd:,.0f} đ")
                        with c3:
                            st.metric("Hệ số bán", f"x {hs}")
                            st.markdown(f"### Giá bán: <span style='color:red'>{selling_price:,.0f} đ</span>", unsafe_allow_html=True)
                    else:
                        st.warning("⚠️ Không tìm thấy Part Number này trong hệ thống.")

                # --- KÉO NÚT XUỐNG SÂU ---
                st.markdown("<br>" * 10, unsafe_allow_html=True)
                col_save, col_order, _ = st.columns([1, 1, 3])
                with col_save:
                    st.button("💾 Lưu Báo Giá", use_container_width=True, type="primary")
                with col_order:
                    st.button("🛒 Đặt Hàng", use_container_width=True)

        elif menu_selection == "🗂️ Master Data":
            st.header("🗂️ Master Data")
            # Logic Master Data giữ nguyên...
            st.info("Dữ liệu gốc từ SP List")

if __name__ == "__main__":
    main()
