import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re

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
        st.error(f"❌ Lỗi kết nối Google Sheets: {e}")
        return None, None, None, None, None

def to_pure_number_str(val):
    """Làm sạch mã tuyệt đối để không bao giờ lỗi search"""
    if pd.isna(val) or val == "": return ""
    # Chuyển về string, bỏ đuôi .0 nếu là số float, bỏ mọi ký tự lạ
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    # SIDEBAR
    st.sidebar.title("⚙️ HỆ THỐNG D&Q")
    menu_selection = st.sidebar.radio("📂 Danh mục chính:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])
    st.sidebar.divider()
    ty_gia = st.sidebar.number_input("Tỷ giá Euro (VND):", value=31000, step=100)
    if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'sub_action' not in st.session_state: st.session_state.sub_action = None

    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
    data = load_all_data(url)
    df_sp_raw, df_mst, df_contact, df_machines, df_staff = data

    if df_sp_raw is not None:
        if menu_selection == "📄 Báo Giá Phụ Tùng":
            col_m1, col_m2 = st.columns([1, 4])
            with col_m1:
                if st.button("➕ Tạo Báo Giá", use_container_width=True): st.session_state.sub_action = "create"
            with col_m2:
                if st.button("🔍 Tra Cứu", use_container_width=True): st.session_state.sub_action = "search"

            if st.session_state.sub_action == "create":
                st.divider()
                
                # --- KHỐI THÔNG TIN KHÁCH HÀNG (CÂN BẰNG THẲNG HÀNG) ---
                c1, c2 = st.columns(2)
                with c1:
                    cust_name = st.selectbox("🎯 Khách hàng:", options=sorted(df_mst['Customer name'].unique()))
                    row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
                    c_no_clean = to_pure_number_str(row_mst['Customer no'])
                    
                    st.info(f"**Cust No:** {c_no_clean} | **MST:** {row_mst['Mã số thuế']}")
                    
                    # Machine Number
                    m_list = df_machines[df_machines['Customer no'].astype(str).str.contains(c_no_clean)]['Customer Machine'].tolist()
                    st.selectbox("🛠️ Machine number:", options=m_list if m_list else ["N/A"])

                with c2:
                    # Contact Person
                    f_conts = df_contact[df_contact['Customer no'].astype(str).str.contains(c_no_clean)]
                    list_conts = f_conts['Customer contact'].dropna().unique().tolist()
                    selected_c = st.selectbox("👤 Contact Person:", options=list_conts if list_conts else ["N/A"])
                    
                    # Phone & Email (Sử dụng container để giữ chiều cao cố định giống ô st.info bên trái)
                    with st.container():
                        if list_conts and selected_c != "N/A":
                            dt = f_conts[f_conts['Customer contact'] == selected_c].iloc[0]
                            st.markdown(f"<div style='height:52px; padding:10px; border-radius:5px; background-color:#f0f2f6; margin-bottom:15px'>📞 {dt.get('Phone','-')} | ✉️ {dt.get('Email','-')}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown("<div style='height:52px; padding:10px; border-radius:5px; background-color:#f0f2f6; margin-bottom:15px'>📞 - | ✉️ -</div>", unsafe_allow_html=True)
                    
                    # Người lập (Bây giờ sẽ thẳng hàng với Machine Number)
                    staff_list = df_staff['Name'].tolist() if df_staff is not None else ["Admin"]
                    st.selectbox("✍️ Người lập báo giá:", options=staff_list)

                st.markdown(f"> **📍 Địa chỉ:** {row_mst['Full Information customer']}")
                st.divider()

                # --- TÌM KIẾM ĐA MÃ (FIX TRIỆT ĐỂ LỖI CHUỖI DÀI) ---
                st.subheader("🔍 Tìm Part Number")
                search_col, btn_col = st.columns([4, 1])
                with search_col:
                    input_search = st.text_input("Search", placeholder="Dán dãy mã (VD: 4007010482;4007010183...)", label_visibility="collapsed")
                with btn_col:
                    add_btn = st.button("🛒 Thêm vào giỏ hàng", use_container_width=True, type="primary")

                if add_btn and input_search:
                    # 1. Tách chuỗi dán vào thành list các mã sạch
                    codes_to_find = [to_pure_number_str(c) for c in input_search.split(';') if c.strip()]
                    
                    # 2. Làm sạch cột Part number trong Database trước khi so sánh
                    # (Ép về String để tránh lỗi khi gặp mã 40...)
                    df_sp_raw['CODE_CLEAN'] = df_sp_raw['Part number'].apply(to_pure_number_str)
                    
                    found_count = 0
                    missing_codes = []

                    for code in codes_to_find:
                        match = df_sp_raw[df_sp_raw['CODE_CLEAN'] == code]
                        if not match.empty:
                            item = match.iloc[0]
                            vat_val = item['VAT']
                            vat_display = f"{int(float(vat_val)*100)}%" if pd.notna(vat_val) else "0%"
                                
                            st.session_state.cart.append({
                                "Part Number": item['Part number'],
                                "Part name": item['Part name'],
                                "Qty": 1,
                                "Unit": item['Unit'],
                                "VAT": vat_display,
                                "Unit Price": float(item['Giá bán']) if pd.notna(item['Giá bán']) else 0.0
                            })
                            found_count += 1
                        else:
                            missing_codes.append(code)
                    
                    if found_count > 0:
                        st.toast(f"✅ Đã thêm {found_count} mã vào giỏ hàng!")
                    if missing_codes:
                        st.error(f"❌ Không tìm thấy các mã: {', '.join(missing_codes)}")

                # --- BẢNG GIỎ HÀNG ---
                if st.session_state.cart:
                    st.markdown("### 📋 Danh sách đã chọn")
                    df_cart = pd.DataFrame(st.session_state.cart)
                    df_cart.insert(0, 'No', range(1, len(df_cart) + 1))
                    
                    st.data_editor(
                        df_cart,
                        column_config={
                            "No": st.column_config.NumberColumn("No", width="small"),
                            "Unit Price": st.column_config.NumberColumn("Unit Price", format="%,d"),
                            "VAT": st.column_config.TextColumn("VAT", width="small"),
                            "Qty": st.column_config.NumberColumn("Qty", min_value=1),
                        },
                        use_container_width=True,
                        hide_index=True,
                        key="cart_editor_v7"
                    )
                    if st.button("🗑️ Xóa hết bảng"):
                        st.session_state.cart = []
                        st.rerun()

                st.markdown("<br>" * 2, unsafe_allow_html=True)
                cs1, cs2, _ = st.columns([1.5, 1.5, 5])
                cs1.button("💾 Lưu Báo Giá", use_container_width=True)
                cs2.button("🛒 Đặt Hàng", use_container_width=True)

        elif menu_selection == "🗂️ Master Data":
            st.header("🗂️ Master Data")
            st.dataframe(df_sp_raw, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
