import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import math

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=60)
def load_all_data(url_link):
    """Tải tất cả các sheet cần thiết một lần để tối ưu hiệu suất"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_sp = conn.read(spreadsheet=url_link, worksheet="SP List", ttl=0)
        df_mst = conn.read(spreadsheet=url_link, worksheet="Customer_MST", ttl=0)
        df_contact = conn.read(spreadsheet=url_link, worksheet="Customer_Contact", ttl=0)
        
        # Làm sạch tên cột
        df_sp.columns = [c.replace('\n', ' ').strip() for c in df_sp.columns]
        df_mst.columns = [c.replace('\n', ' ').strip() for c in df_mst.columns]
        df_contact.columns = [c.replace('\n', ' ').strip() for c in df_contact.columns]
        
        return df_sp, df_mst, df_contact
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu từ Google Sheets: {e}")
        return None, None, None

def roundup_to_10k(x):
    if x == 0: return 0
    return math.ceil(x / 10000) * 10000

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

    if df_calc.shape[1] >= 21:
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
    st.set_page_config(page_title="D&Q Machinery - Hệ thống Báo giá", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    # Sidebar cấu hình
    st.sidebar.title("⚙️ Cấu hình chung")
    ty_gia_input = st.sidebar.number_input("Nhập Tỷ giá Euro mới (VND):", value=31000, step=100)
    
    if st.sidebar.button("🔄 Làm mới toàn bộ dữ liệu"):
        st.cache_data.clear()
        st.rerun()

    # Tải dữ liệu
    df_sp_raw, df_mst, df_contact = load_all_data(url)

    if df_sp_raw is not None:
        # Khởi tạo Tabs
        tab_quote, tab_master = st.tabs(["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])

        # --- STEP 1: TAB MASTER DATA ---
        with tab_master:
            st.header("🗂️ Hệ thống Tra cứu Phụ tùng (Master)")
            df_final_sp = tinh_toan_sp(df_sp_raw, ty_gia_input)
            
            search_query = st.text_input("Tìm nhanh Part number (Dùng dấu ;):")
            if search_query:
                list_ma = [s.strip() for s in search_query.split(';') if s.strip()]
                df_final_sp['Part number'] = df_final_sp['Part number'].astype(str)
                result = df_final_sp[df_final_sp['Part number'].isin(list_ma)]
                st.dataframe(result, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_final_sp, use_container_width=True, hide_index=True)

        # --- STEP 2 & 3: TAB BÁO GIÁ PHỤ TÙNG ---
        with tab_quote:
            st.header("📝 Lập Báo Giá")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 2-1: Dropdown chọn khách hàng
                customer_list = df_mst['Customer name'].dropna().unique().tolist()
                selected_customer = st.selectbox("🎯 Chọn tên khách hàng:", options=customer_list)

                # Truy xuất thông tin khách hàng từ Customer_MST
                cust_info = df_mst[df_mst['Customer name'] == selected_customer].iloc[0]
                customer_no = cust_info['Mã khách'] # Đây chính là Customer no

                # 2-2: Hiển thị thông tin khách hàng
                st.info(f"**Mã khách (Customer no):** {customer_no}")
                st.write(f"**Mã số thuế:** {cust_info['Mã số thuế']}")
            
            with col2:
                # STEP 3: Lấy Customer Contact
                # Lọc contact dựa trên Customer no (Mã khách)
                # Lưu ý: Cột trong file excel của bạn là 'Customer no.' (có dấu chấm)
                contacts = df_contact[df_contact['Customer no.'] == customer_no]
                contact_list = contacts['Customer contact'].dropna().unique().tolist()
                
                if contact_list:
                    selected_contact = st.selectbox("👤 Chọn người liên hệ (Contact):", options=contact_list)
                    # Hiển thị thêm chi tiết liên hệ nếu cần
                    detail = contacts[contacts['Customer contact'] == selected_contact].iloc[0]
                    st.success(f"📱 Phone/Email: {detail.get('Phone', 'N/A')} | {detail.get('Email', 'N/A')}")
                else:
                    st.warning("⚠️ Không tìm thấy người liên hệ cho mã khách này.")

            st.divider()
            st.markdown(f"### 📋 Thông tin chi tiết khách hàng")
            st.code(cust_info['Full Information customer'], language='markdown')

if __name__ == "__main__":
    main()
