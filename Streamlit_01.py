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

def tinh_toan_sp(df, ty_gia_moi):
    df_calc = df.copy()
    def clean_num(x):
        if pd.isna(x) or str(x).strip() in ['-', '']: return 0
        return pd.to_numeric(str(x).replace(',', '').strip(), errors='coerce') or 0
    df_calc = df_calc.iloc[:, 0:21]
    gia_net_euro = df_calc['Giá Net Euro'].apply(clean_num)
    he_so = df_calc['Hệ số'].apply(clean_num)
    net_vnd = (gia_net_euro * ty_gia_moi).apply(roundup_to_10k)
    gia_ban = (net_vnd * he_so).apply(roundup_to_10k)
    df_calc['Giá Net VND'] = net_vnd.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df_calc['Giá bán'] = gia_ban.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df_calc['Profit (Lợi nhuận)'] = (gia_ban - net_vnd).apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df_calc['Margin (Biên lợi nhuận)'] = ((gia_ban - net_vnd) / gia_ban).fillna(0).apply(lambda x: f"{x:.0%}")
    return df_calc

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    st.sidebar.title("⚙️ Cấu hình chung")
    ty_gia_input = st.sidebar.number_input("Nhập Tỷ giá Euro mới (VND):", value=31000, step=100)
    if st.sidebar.button("🔄 Làm mới toàn bộ dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    menu_selection = st.sidebar.radio("📂 Danh mục quản lý:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])

    df_sp_raw, df_mst, df_contact, df_machines = load_all_data(url)

    if df_sp_raw is not None:
        if menu_selection == "📄 Báo Giá Phụ Tùng":
            st.header("📝 Lập Báo Giá")
            
            # --- HÀNG 1: LỰA CHỌN KHÁCH HÀNG & LIÊN HỆ ---
            col_sel_cust, col_sel_cont = st.columns(2)
            
            with col_sel_cust:
                customer_list = sorted(df_mst['Customer name'].astype(str).unique().tolist())
                selected_customer = st.selectbox("🎯 Customer name:", options=customer_list)
                cust_info = df_mst[df_mst['Customer name'] == selected_customer].iloc[0]
                customer_no_key = format_as_int_str(cust_info['Customer no'])
                mst_val = format_as_int_str(cust_info['Mã số thuế'])

            with col_sel_cont:
                df_contact['Customer no'] = df_contact['Customer no'].apply(format_as_int_str)
                filtered_contacts = df_contact[df_contact['Customer no'] == customer_no_key]
                contact_options = filtered_contacts['Customer contact'].dropna().unique().tolist()
                
                if contact_options:
                    selected_contact = st.selectbox("👤 Contact Person:", options=contact_options)
                    c_detail = filtered_contacts[filtered_contacts['Customer contact'] == selected_contact].iloc[0]
                    # Dùng markdown để hiển thị phone/email nhỏ gọn, không dùng st.success để tránh chiếm diện tích lớn
                    phone_val = c_detail.get('Phone', '-')
                    email_val = c_detail.get('Email', '-')
                    st.markdown(f"📞 `{phone_val}` | ✉️ `{email_val}`")
                else:
                    st.selectbox("👤 Contact Person:", options=["Không có dữ liệu"], disabled=True)
                    st.write("") # Giữ khoảng trống đồng nhất

            # --- HÀNG 2: THÔNG TIN MÃ SỐ (ÉP SÁT LÊN TRÊN) ---
            # Dùng 4 cột để các tiêu đề Customer no và MST nằm sát nhau và sát bên dưới ô chọn
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            with c1:
                st.markdown(f"**Customer no:** {customer_no_key}")
            with c2:
                st.markdown(f"**Mã số thuế:** {mst_val}")

            # --- HÀNG 3: MACHINE NUMBER ---
            df_machines['Customer no'] = df_machines['Customer no'].apply(format_as_int_str)
            f_machines = df_machines[df_machines['Customer no'] == customer_no_key]
            machine_options = f_machines['Customer Machine'].dropna().unique().tolist()

            col_mach, col_empty = st.columns([1, 1])
            with col_mach:
                if machine_options:
                    selected_machine = st.selectbox("🛠️ Machine number:", options=machine_options)
                else:
                    st.selectbox("🛠️ Machine number:", options=["Không có dữ liệu"], disabled=True)

            # --- HÀNG 4: ĐỊA CHỈ ---
            st.markdown("**Địa chỉ:**")
            st.caption(cust_info['Full Information customer'])

            st.divider()
            st.info("💡 Thông tin phụ tùng sẽ hiển thị bên dưới đường gạch này.")

        elif menu_selection == "🗂️ Master Data":
            st.header("🗂️ Master Data")
            df_final_sp = tinh_toan_sp(df_sp_raw, ty_gia_input)
            st.dataframe(df_final_sp, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
