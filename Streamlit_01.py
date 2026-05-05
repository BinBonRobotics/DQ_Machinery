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
        for df in [df_sp, df_mst, df_contact, df_machines]:
            df.columns = [c.replace('\n', ' ').strip() for c in df.columns]
        return df_sp, df_mst, df_contact, df_machines
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None, None, None, None

def format_as_int_str(val):
    if pd.isna(val) or str(val).strip() in ['-', '']: return ""
    try:
        return str(int(float(str(val).replace(',', '').strip())))
    except:
        return str(val).strip()

def roundup_to_10k(x):
    if x == 0: return 0
    return math.ceil(x / 10000) * 10000

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    # CSS tinh chỉnh: Chỉ giảm khoảng cách vừa đủ, không làm đè chữ
    st.markdown("""
        <style>
        .stVerticalBlock { gap: 0.5rem; }
        .stSelectbox { margin-bottom: 0px; }
        div[data-testid="stMarkdownContainer"] p { margin-bottom: 5px; }
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

    df_sp_raw, df_mst, df_contact, df_machines = load_all_data(url)

    if df_sp_raw is not None:
        if menu_selection == "📄 Báo Giá Phụ Tùng":
            st.header("📝 Lập Báo Giá")
            
            # --- KHỐI 1: CHỌN KHÁCH HÀNG ---
            col1, col2 = st.columns(2)
            with col1:
                customer_list = sorted(df_mst['Customer name'].astype(str).unique().tolist())
                selected_customer = st.selectbox("🎯 Customer name:", options=customer_list)
                cust_info = df_mst[df_mst['Customer name'] == selected_customer].iloc[0]
                c_no = format_as_int_str(cust_info['Customer no'])
                mst_val = format_as_int_str(cust_info['Mã số thuế'])
                
                # Hiển thị mã số ngay dưới tên khách hàng
                st.markdown(f"**Customer no:** {c_no} &nbsp;&nbsp; | &nbsp;&nbsp; **MST:** {mst_val}")

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

            # --- KHỐI 2: CHỌN MÁY ---
            st.markdown("---") # Đường kẻ mỏng phân cách
            df_machines['Customer no'] = df_machines['Customer no'].apply(format_as_int_str)
            f_machines = df_machines[df_machines['Customer no'] == c_no]
            m_options = f_machines['Customer Machine'].dropna().unique().tolist()

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                if m_options:
                    st.selectbox("🛠️ Machine number:", options=m_options)
                else:
                    st.selectbox("🛠️ Machine number:", options=["Không có dữ liệu"], disabled=True)
            
            # --- KHỐI 3: ĐỊA CHỈ (DÀN TRẢI ĐỂ DỄ ĐỌC) ---
            st.markdown("**📍 Địa chỉ:**")
            st.info(cust_info['Full Information customer'])

            st.divider()
            st.caption("💡 Thông tin phụ tùng sẽ hiển thị bên dưới.")

        elif menu_selection == "🗂️ Master Data":
            st.header("🗂️ Master Data")
            # (Phần tinh_toan_sp giữ nguyên như cũ)
            st.write("Dữ liệu Master Data hiển thị tại đây...")

if __name__ == "__main__":
    main()
