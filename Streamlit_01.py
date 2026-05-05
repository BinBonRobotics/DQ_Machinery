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
        
        for df in [df_sp, df_mst, df_contact]:
            df.columns = [c.replace('\n', ' ').strip() for c in df.columns]
        
        return df_sp, df_mst, df_contact
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None, None, None

def roundup_to_10k(x):
    if x == 0: return 0
    return math.ceil(x / 10000) * 10000

def format_as_int_str(val):
    """Chuyển đổi số sang số nguyên chuỗi sạch sẽ"""
    if pd.isna(val) or str(val).strip() in ['-', '']: return ""
    try:
        # Xử lý trường hợp số bị lưu dạng float (123.0) hoặc string có dấu phẩy
        num_clean = str(val).replace(',', '').strip()
        return str(int(float(num_clean)))
    except:
        return str(val)

def format_number_with_comma(val):
    if pd.isna(val) or str(val).strip() in ['-', '']: return "-"
    try:
        num = float(str(val).replace(',', '').strip())
        return f"{int(num):,}" if num == int(num) else f"{num:,.2f}".rstrip('0').rstrip('.')
    except: return str(val)

def tinh_toan_sp(df, ty_gia_moi):
    df_calc = df.copy()
    def clean_num(x):
        if pd.isna(x) or str(x).strip() in ['-', '']: return 0
        return pd.to_numeric(str(x).replace(',', '').strip(), errors='coerce') or 0

    df_calc = df_calc.iloc[:, 0:21]
    gia_net_euro = df_calc['Giá Net Euro'].apply(clean_num)
    he_so = df_calc['Hệ số'].apply(clean_num)
    net_vnd = (gia_net_euro * ty_gia_moi).apply(roundup_to_10k)
    gia_ban = (net_vnd * he_so).apply(roundup_to_10k)
    profit = gia_ban - net_vnd
    margin = (profit / gia_ban).fillna(0)

    df_calc['Giá Net VND'] = net_vnd.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df_calc['Giá bán'] = gia_ban.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df_calc['Profit (Lợi nhuận)'] = profit.apply(lambda x: f"{int(x):,}" if x != 0 else "-")
    df_calc['Margin (Biên lợi nhuận)'] = margin.apply(lambda x: f"{x:.0%}")

    cols_format = ['Unit Price (VND)', 'Tỷ giá', 'Unit Price (Euro)', 'Thuế Nhập Khẩu VND']
    for col in cols_format:
        if col in df_calc.columns:
            df_calc[col] = df_calc[col].apply(format_number_with_comma)
    return df_calc

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    # --- SIDEBAR ---
    st.sidebar.title("⚙️ Cấu hình chung")
    ty_gia_input = st.sidebar.number_input("Nhập Tỷ giá Euro mới (VND):", value=31000, step=100)
    if st.sidebar.button("🔄 Làm mới toàn bộ dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")
    menu_selection = st.sidebar.radio("📂 Danh mục quản lý:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])

    df_sp_raw, df_mst, df_contact = load_all_data(url)

    if df_sp_raw is not None:
        if menu_selection == "📄 Báo Giá Phụ Tùng":
            st.header("📝 Lập Báo Giá")
            
            # --- HÀNG 1: CHỌN KHÁCH HÀNG & NGƯỜI LIÊN HỆ ---
            col_sel_cust, col_sel_cont = st.columns(2)
            
            with col_sel_cust:
                df_mst['Customer name'] = df_mst['Customer name'].astype(str).str.strip()
                customer_list = sorted(df_mst['Customer name'].unique().tolist())
                selected_customer = st.selectbox("🎯 Chọn tên khách hàng (Customer name):", options=customer_list)
                
                # Lấy thông tin cơ bản
                cust_info = df_mst[df_mst['Customer name'] == selected_customer].iloc[0]
                customer_no_val = format_as_int_str(cust_info['Customer no'])
                mst_val = format_as_int_str(cust_info['Mã số thuế'])

            with col_sel_cont:
                # Lọc danh sách người liên hệ dựa trên Customer no
                df_contact['Customer no'] = df_contact['Customer no'].astype(str).str.strip()
                # Đồng bộ format mã khách để lọc chính xác
                current_cust_no = str(cust_info['Customer no']).split('.')[0].strip()
                contacts = df_contact[df_contact['Customer no'] == current_cust_no]
                
                contact_list = contacts['Customer contact'].dropna().unique().tolist()
                
                if contact_list:
                    selected_contact = st.selectbox("👤 Chọn người liên hệ (Contact):", options=contact_list)
                    contact_detail = contacts[contacts['Customer contact'] == selected_contact].iloc[0]
                else:
                    st.selectbox("👤 Chọn người liên hệ (Contact):", options=["Không có dữ liệu"], disabled=True)
                    contact_detail = None

            # --- HÀNG 2: THÔNG TIN MÃ KHÁCH, MST & LIÊN HỆ ---
            col_info_c1, col_info_c2, col_info_cont = st.columns([1, 1, 2])
            
            with col_info_c1:
                st.write(f"**Customer no:** {customer_no_val}")
            with col_info_c2:
                st.write(f"**Mã số thuế:** {mst_val}")
            with col_info_cont:
                if contact_detail is not None:
                    phone = contact_detail.get('Phone', '-')
                    email = contact_detail.get('Email', '-')
                    st.success(f"📞 Phone: {phone} | ✉️ Email: {email}")

            # --- HÀNG 3: ĐỊA CHỈ ---
            st.write(f"**Địa chỉ:**")
            st.text_area(label="Full Address", value=cust_info['Full Information customer'], height=80, label_visibility="collapsed")

            st.divider()
            # Khu vực dành cho phụ tùng tiếp theo
            st.info("💡 Thông tin phụ tùng sẽ hiển thị bên dưới đường gạch này.")

        elif menu_selection == "🗂️ Master Data":
            st.header("🗂️ Master Data - Phụ tùng")
            df_final_sp = tinh_toan_sp(df_sp_raw, ty_gia_input)
            search_query = st.text_input("Tìm nhanh Part number:")
            if search_query:
                list_ma = [s.strip() for s in search_query.split(';') if s.strip()]
                result = df_final_sp[df_final_sp['Part number'].astype(str).isin(list_ma)]
                st.dataframe(result, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_final_sp, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
