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
        # Tải thêm dữ liệu Staff
        df_staff = conn.read(spreadsheet=url_link, worksheet="Staff", ttl=0)
        
        for df in [df_sp, df_mst, df_contact, df_machines, df_staff]:
            df.columns = [c.replace('\n', ' ').strip() for c in df.columns]
        
        return df_sp, df_mst, df_contact, df_machines, df_staff
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None, None, None, None, None

def format_as_int_str(val):
    if pd.isna(val) or str(val).strip() in ['-', '']: return ""
    try:
        return str(int(float(str(val).replace(',', '').strip())))
    except:
        return str(val).strip()

def roundup_to_10k(x):
    if x == 0: return 0
    return math.ceil(x / 10000) * 10000

def tinh_toan_sp(df, ty_gia_moi):
    df_calc = df.copy()
    def clean_num(x):
        if pd.isna(x) or str(x).strip() in ['-', '']: return 0
        return pd.to_numeric(str(x).replace(',', '').strip(), errors='coerce') or 0
    
    gia_net_euro = df_calc['Giá Net Euro'].apply(clean_num)
    he_so = df_calc['Hệ số'].apply(clean_num)
    net_vnd = (gia_net_euro * ty_gia_moi).apply(roundup_to_10k)
    gia_ban = (net_vnd * he_so).apply(roundup_to_10k)
    
    df_calc['Giá Net VND'] = net_vnd.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df_calc['Giá bán'] = gia_ban.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df_calc['Profit (Lợi nhuận)'] = (gia_ban - net_vnd).apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df_calc['Margin (Biên lợi nhuận)'] = ((gia_ban - net_vnd) / gia_ban).fillna(0).apply(lambda x: f"{x:.0%}")
    return df_calc

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    st.markdown("""
        <style>
        .stVerticalBlock { gap: 0.5rem; }
        .stSelectbox { margin-bottom: 0px; }
        div[data-testid="stMarkdownContainer"] p { margin-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)

    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    st.sidebar.title("⚙️ Cấu hình")
    ty_gia_input = st.sidebar.number_input("Tỷ giá Euro:", value=31000, step=100)
    if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    menu_selection = st.sidebar.radio("📂 Danh mục:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])

    # Nhận thêm biến df_staff từ hàm tải dữ liệu
    df_sp_raw, df_mst, df_contact, df_machines, df_staff = load_all_data(url)

    if df_sp_raw is not None:
        if menu_selection == "📄 Báo Giá Phụ Tùng":
            st.header("📝 Lập Báo Giá")
            
            # --- KHỐI 1: KHÁCH HÀNG & LIÊN HỆ ---
            col1, col2 = st.columns(2)
            with col1:
                customer_list = sorted(df_mst['Customer name'].astype(str).unique().tolist())
                selected_customer = st.selectbox("🎯 Customer name:", options=customer_list)
                cust_info = df_mst[df_mst['Customer name'] == selected_customer].iloc[0]
                c_no = format_as_int_str(cust_info['Customer no'])
                mst_val = format_as_int_str(cust_info['Mã số thuế'])
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

            # --- KHỐI 2: MACHINE NUMBER & NGƯỜI LẬP BÁO GIÁ ---
            st.markdown("---")
            col_m1, col_m2 = st.columns(2) # Chia làm 2 cột ngang hàng
            
            with col_m1:
                df_machines['Customer no'] = df_machines['Customer no'].apply(format_as_int_str)
                f_machines = df_machines[df_machines['Customer no'] == c_no]
                m_options = f_machines['Customer Machine'].dropna().unique().tolist()
                if m_options:
                    st.selectbox("🛠️ Machine number:", options=m_options)
                else:
                    st.selectbox("🛠️ Machine number:", options=["Không có dữ liệu"], disabled=True)

            with col_m2:
                # Lấy danh sách từ cột 'Name' (Cột B) của tab Staff
                if df_staff is not None and 'Name' in df_staff.columns:
                    staff_list = df_staff['Name'].dropna().unique().tolist()
                    st.selectbox("✍️ Người lập báo giá:", options=staff_list)
                else:
                    st.selectbox("✍️ Người lập báo giá:", options=["Lỗi dữ liệu Staff"], disabled=True)
            
            # --- KHỐI 3: ĐỊA CHỈ ---
            st.markdown("**📍 Địa chỉ:**")
            st.info(cust_info['Full Information customer'])
            st.divider()
            st.caption("💡 Thông tin phụ tùng sẽ hiển thị bên dưới.")

        elif menu_selection == "🗂️ Master Data":
            st.header("🗂️ Master Data")
            df_final = tinh_toan_sp(df_sp_raw, ty_gia_input)
            st.dataframe(df_final, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
