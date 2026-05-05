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
    """Chuyển đổi các số như 43903.0 thành chuỗi '43903'"""
    if pd.isna(val) or str(val).strip() in ['-', '']: return ""
    try:
        return str(int(float(str(val).replace(',', '').strip())))
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
            
            # 1. Chọn khách hàng (Giao diện ngắn lại bằng cách dùng columns)
            df_mst['Customer name'] = df_mst['Customer name'].astype(str).str.strip()
            customer_list = sorted(df_mst['Customer name'].unique().tolist())
            
            col_sel1, col_sel2 = st.columns([1, 2])
            with col_sel1:
                # Yêu cầu 1: Tiêu đề bên trái drop menu
                selected_customer = st.selectbox("Customer name:", options=customer_list)

            # Lấy thông tin
            cust_info = df_mst[df_mst['Customer name'] == selected_customer].iloc[0]
            
            # Xử lý số nguyên cho Mã khách và Mã số thuế (Yêu cầu 2 & 3)
            customer_no = format_as_int_str(cust_info['Customer no'])
            ma_so_thue = format_as_int_str(cust_info['Mã số thuế'])

            # Yêu cầu 3: Customer no và Mã số thuế ngang hàng, không nền xanh
            col_info1, col_info2, col_info3 = st.columns([1, 1, 2])
            with col_info1:
                st.write(f"**Customer no:** {customer_no}")
            with col_info2:
                st.write(f"**Mã số thuế:** {ma_so_thue}")

            # Yêu cầu 4: Đưa địa chỉ lên trên đường kẻ và đổi tên tiêu đề
            st.write(f"**Địa chỉ:**")
            st.text_area(label="Địa chỉ chi tiết", value=cust_info['Full Information customer'], height=100, label_visibility="collapsed")

            # Người liên hệ
            df_contact['Customer no'] = df_contact['Customer no'].astype(str).str.strip()
            contacts = df_contact[df_contact['Customer no'] == str(cust_info['Customer no']).split('.')[0]]
            contact_list = contacts['Customer contact'].dropna().unique().tolist()
            
            if contact_list:
                col_cont1, col_cont2 = st.columns([1, 2])
                with col_cont1:
                    selected_contact = st.selectbox("👤 Contact:", options=contact_list)
                with col_cont2:
                    detail = contacts[contacts['Customer contact'] == selected_contact].iloc[0]
                    st.write("") # Căn chỉnh dòng
                    st.write(f"📞 {detail.get('Phone', 'N/A')} | ✉️ {detail.get('Email', 'N/A')}")

            st.divider()
            st.info("💡 Thông tin phụ tùng (Sẽ hiển thị tại đây)")

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
