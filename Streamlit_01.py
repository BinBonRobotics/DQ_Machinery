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
        
        # Làm sạch tên cột (bỏ xuống dòng)
        for df in [df_sp, df_mst, df_contact, df_machines, df_staff]:
            df.columns = [c.replace('\n', ' ').strip() for c in df.columns]
        return df_sp, df_mst, df_contact, df_machines, df_staff
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None, None, None, None, None

def to_pure_number_str(val):
    """Biến mọi giá trị (số/chuỗi/dấu chấm) thành chuỗi số nguyên duy nhất"""
    if pd.isna(val): return ""
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2] # Bỏ đuôi .0 của số float
    return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'sub_action' not in st.session_state: st.session_state.sub_action = None

    # SIDEBAR
    st.sidebar.title("⚙️ HỆ THỐNG D&Q")
    menu_selection = st.sidebar.radio("📂 Danh mục chính:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])

    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
    df_sp_raw, df_mst, df_contact, df_machines, df_staff = load_all_data(url)

    if df_sp_raw is not None:
        if menu_selection == "📄 Báo Giá Phụ Tùng":
            # Nút chức năng chính
            col_m1, col_m2 = st.columns([1, 4])
            with col_m1:
                if st.button("➕ Tạo Báo Giá", use_container_width=True): st.session_state.sub_action = "create"
            with col_m2:
                if st.button("🔍 Tra Cứu", use_container_width=True): st.session_state.sub_action = "search"

            if st.session_state.sub_action == "create":
                st.divider()
                
                # --- KHỐI THÔNG TIN KHÁCH HÀNG ---
                c1, c2 = st.columns(2)
                with c1:
                    cust_name = st.selectbox("🎯 Khách hàng:", options=sorted(df_mst['Customer name'].unique()))
                    row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
                    c_no = to_pure_number_str(row_mst['Customer no'])
                    st.info(f"**Cust No:** {c_no} | **MST:** {row_mst['Mã số thuế']}")
                    
                    # Machine Number (Thẳng hàng ngang với Người lập)
                    m_list = df_machines[df_machines['Customer no'].astype(str).str.contains(c_no)]['Customer Machine'].tolist()
                    st.selectbox("🛠️ Machine number:", options=m_list if m_list else ["N/A"])

                with c2:
                    # Contact & Thông tin liên hệ (Dưới contact là Phone/Email)
                    f_conts = df_contact[df_contact['Customer no'].astype(str).str.contains(c_no)]
                    list_conts = f_conts['Customer contact'].dropna().unique().tolist()
                    selected_c = st.selectbox("👤 Contact Person:", options=list_conts if list_conts else ["N/A"])
                    
                    if list_conts and selected_c != "N/A":
                        dt = f_conts[f_conts['Customer contact'] == selected_c].iloc[0]
                        st.write(f"📞 {dt.get('Phone','-')} | ✉️ {dt.get('Email','-')}")
                    else: st.write("📞 - | ✉️ -")
                    
                    # Người lập (Nằm ngay dưới dòng Phone/Email để cân đối với Machine Number bên trái)
                    staff_list = df_staff['Name'].tolist() if df_staff is not None else ["Admin"]
                    st.selectbox("✍️ Người lập báo giá:", options=staff_list)

                st.markdown(f"> **📍 Địa chỉ:** {row_mst['Full Information customer']}")
                st.divider()

                # --- TÌM KIẾM ĐA MÃ (FIX THẲNG HÀNG & SEARCH LỖI) ---
                st.subheader("🔍 Tìm Part Number")
                
                # Dùng columns để nút bấm và input nằm trên 1 hàng
                search_col, btn_col = st.columns([4, 1])
                
                with search_col:
                    # label_visibility="collapsed" giúp ô nhập liệu mất cái nhãn trống phía trên -> Thẳng hàng với nút bấm
                    input_search = st.text_input("Search", placeholder="Dán dãy mã cách nhau bởi dấu ; vào đây...", label_visibility="collapsed")
                
                with btn_col:
                    add_btn = st.button("🛒 Thêm vào giỏ hàng", use_container_width=True, type="primary")

                if add_btn and input_search:
                    # 1. Tách danh sách mã từ chuỗi nhập vào
                    codes_to_find = [to_pure_number_str(c) for c in input_search.split(';') if c.strip()]
                    
                    # 2. Tạo cột tạm để so sánh (đã làm sạch hết dấu chấm/phẩy trong database)
                    df_sp_raw['CODE_CLEAN'] = df_sp_raw['Part number'].apply(to_pure_number_str)
                    
                    found_items = df_sp_raw[df_sp_raw['CODE_CLEAN'].isin(codes_to_find)]
                    
                    if not found_items.empty:
                        for _, item in found_items.iterrows():
                            # Format VAT sang %
                            v_raw = item['VAT']
                            v_display = f"{int(float(v_raw)*100)}%" if pd.notna(v_raw) else "0%"
                            
                            st.session_state.cart.append({
                                "Part Number": item['Part number'],
                                "Part name": item['Part name'],
                                "Qty": 1,
                                "Unit": item['Unit'],
                                "VAT": v_display,
                                "Unit Price": float(item['Giá bán']) if pd.notna(item['Giá bán']) else 0
                            })
                        st.toast(f"✅ Đã thêm {len(found_items)} mã vào giỏ hàng!")
                    else:
                        st.error("❌ Không tìm thấy mã nào. Hãy kiểm tra lại dãy mã vừa nhập.")

                # --- BẢNG GIỎ HÀNG ---
                if st.session_state.cart:
                    st.markdown("### 📋 Danh sách đã chọn")
                    df_cart = pd.DataFrame(st.session_state.cart)
                    df_cart.insert(0, 'No', range(1, len(df_cart) + 1))
                    
                    st.data_editor(
                        df_cart,
                        column_config={
                            "Unit Price": st.column_config.NumberColumn("Unit Price", format="%d"),
                            "VAT": st.column_config.TextColumn("VAT"),
                        },
                        use_container_width=True,
                        hide_index=True,
                        key="editor_v3"
                    )
                    if st.button("🗑️ Xóa hết"):
                        st.session_state.cart = []
                        st.rerun()

                st.markdown("<br>" * 5, unsafe_allow_html=True)
                cs1, cs2, _ = st.columns([1.5, 1.5, 5])
                cs1.button("💾 Lưu Báo Giá", use_container_width=True)
                cs2.button("🛒 Đặt Hàng", use_container_width=True)

        elif menu_selection == "🗂️ Master Data":
            st.header("🗂️ Master Data")
            st.dataframe(df_sp_raw, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
