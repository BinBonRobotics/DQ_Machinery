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

def tinh_toan_sp(df, ty_gia_moi):
    df_calc = df.copy()
    def clean_num(x):
        if pd.isna(x) or str(x).strip() in ['-', '']: return 0
        return pd.to_numeric(str(x).replace(',', '').strip(), errors='coerce') or 0
    gia_net_euro = df_calc['Giá Net Euro'].apply(clean_num)
    he_so = df_calc['Hệ số'].apply(clean_num)
    net_vnd = (gia_net_euro * ty_gia_moi).apply(roundup_to_10k)
    gia_ban = (net_vnd * he_so).apply(roundup_to_10k)
    df_calc['Giá Net VND'] = net_vnd.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df_calc['Giá bán'] = gia_ban.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    return df_calc

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    if 'sub_action' not in st.session_state:
        st.session_state.sub_action = None

    # CSS tinh chỉnh để các dòng sát nhau nhất có thể
    st.markdown("""
        <style>
        .stVerticalBlock { gap: 0.2rem; }
        .stSelectbox { margin-bottom: -10px; }
        div[data-testid="stMarkdownContainer"] p { margin-bottom: 2px; }
        .stAlert { padding: 10px; margin-top: 5px; }
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
            # --- SUB MENU BUTTONS ---
            col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)
            with col_btn1:
                if st.button("➕ Tạo Báo Giá", use_container_width=True): st.session_state.sub_action = "create"
            with col_btn2:
                if st.button("🔍 Tra Cứu Đơn Hàng", use_container_width=True): st.session_state.sub_action = "search"
            
            st.divider()

            if st.session_state.sub_action == "create":
                # --- KHỐI THÔNG TIN KHÁCH HÀNG (SẮP XẾP LẠI THEO YÊU CẦU) ---
                col1, col2 = st.columns(2)
                
                with col1:
                    customer_list = sorted(df_mst['Customer name'].astype(str).unique().tolist())
                    selected_customer = st.selectbox("🎯 Customer name:", options=customer_list)
                    cust_info = df_mst[df_mst['Customer name'] == selected_customer].iloc[0]
                    c_no = format_as_int_str(cust_info['Customer no'])
                    mst_val = format_as_int_str(cust_info['Mã số thuế'])
                    st.markdown(f"**Customer no:** {c_no} &nbsp;&nbsp; | &nbsp;&nbsp; **MST:** {mst_val}")
                    
                    # --- ĐƯA MACHINE NUMBER LÊN SÁT CUSTOMER NO ---
                    df_machines['Customer no'] = df_machines['Customer no'].apply(format_as_int_str)
                    f_machines = df_machines[df_machines['Customer no'] == c_no]
                    m_options = f_machines['Customer Machine'].dropna().unique().tolist()
                    if m_options:
                        st.selectbox("🛠️ Machine number:", options=m_options)
                    else:
                        st.selectbox("🛠️ Machine number:", options=["Không có dữ liệu"], disabled=True)

                with col2:
                    df_contact['Customer no'] = df_contact['Customer no'].apply(format_as_int_str)
                    f_contacts = df_contact[df_contact['Customer no'] == c_no]
                    cont_options = f_contacts['Customer contact'].dropna().unique().tolist()
                    if cont_options:
                        selected_contact = st.selectbox("👤 Contact Person:", options=cont_options)
                        c_detail = f_contacts[f_contacts['Customer contact'] == selected_contact].iloc[0]
                        st.write(f"📞 {c_detail.get('Phone', '-')} | ✉️ {c_detail.get('Email', '-')}")
                    else:
                        st.selectbox("👤 Contact Person:", options=["Không có dữ liệu"], disabled=True)
                    
                    # --- ĐƯA NGƯỜI LẬP BÁO GIÁ LÊN NGANG HÀNG VỚI MACHINE NUMBER ---
                    if df_staff is not None and 'Name' in df_staff.columns:
                        staff_list = df_staff['Name'].dropna().unique().tolist()
                        st.selectbox("✍️ Người lập báo giá:", options=staff_list)

                # --- ĐỊA CHỈ NẰM DƯỚI VÀ SÁT LÊN TRÊN ---
                st.markdown("**📍 Địa chỉ:**")
                st.write(cust_info['Full Information customer'])
                
                # --- ĐƯỜNG GẠCH NGANG DƯỚI ĐỊA CHỈ ---
                st.markdown("---")

                # --- KHOẢNG TRỐNG ĐỂ ĐIỀN PART NUMBER (Sẽ thêm widget nhập liệu ở đây) ---
                st.write("") # Tạo khoảng hở nhẹ
                st.info("📌 Khu vực nhập Part Number sẽ nằm ở đây.")
                
                # Tạo thêm nhiều khoảng trống bằng markdown nếu cần
                st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)

                # --- ĐƯA NÚT NHẤT XUỐNG DƯỚI CÙNG ---
                col_save, col_order, _ = st.columns([1, 1, 3])
                with col_save:
                    st.button("💾 Lưu Báo Giá", use_container_width=True, type="primary")
                with col_order:
                    st.button("🛒 Đặt Hàng", use_container_width=True)

            elif st.session_state.sub_action == "search":
                st.subheader("🔍 Tra Cứu Đơn Hàng")

        elif menu_selection == "🗂️ Master Data":
            st.session_state.sub_action = None
            st.header("🗂️ Master Data")
            df_final = tinh_toan_sp(df_sp_raw, ty_gia_input)
            st.dataframe(df_final, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
