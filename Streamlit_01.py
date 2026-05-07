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
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return None, None, None, None, None

def format_clean_str(val):
    if pd.isna(val): return ""
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    # CSS để xử lý nút bấm thẳng hàng với ô input
    st.markdown("""
        <style>
        div[data-testid="stColumn"] > div > div > div > div > div > label {
            display: none;
        }
        .align-btn {
            margin-top: 0px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # SIDEBAR
    st.sidebar.title("⚙️ HỆ THỐNG D&Q")
    menu_selection = st.sidebar.radio("📂 Danh mục chính:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])
    
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'sub_action' not in st.session_state: st.session_state.sub_action = None

    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
    df_sp_raw, df_mst, df_contact, df_machines, df_staff = load_all_data(url)

    if df_sp_raw is not None:
        if menu_selection == "📄 Báo Giá Phụ Tùng":
            col_btn1, col_btn2, _, _, _ = st.columns(5)
            with col_btn1:
                if st.button("➕ Tạo Báo Giá", use_container_width=True): st.session_state.sub_action = "create"
            with col_btn2:
                if st.button("🔍 Tra Cứu", use_container_width=True): st.session_state.sub_action = "search"

            if st.session_state.sub_action == "create":
                st.divider()
                
                # --- KHỐI THÔNG TIN KHÁCH HÀNG ---
                r1_c1, r1_c2 = st.columns(2)
                with r1_c1:
                    selected_customer = st.selectbox("🎯 Chọn khách hàng:", options=sorted(df_mst['Customer name'].unique()))
                    cust_info = df_mst[df_mst['Customer name'] == selected_customer].iloc[0]
                    c_no = format_clean_str(cust_info['Customer no'])
                    st.write(f"**Cust No:** {c_no} | **MST:** {format_clean_str(cust_info['Mã số thuế'])}")
                
                with r1_c2:
                    df_contact['C_NO_STR'] = df_contact['Customer no'].apply(format_clean_str)
                    f_contacts = df_contact[df_contact['C_NO_STR'] == c_no]
                    cont_options = f_contacts['Customer contact'].dropna().unique().tolist()
                    selected_contact = st.selectbox("👤 Contact Person:", options=cont_options if cont_options else ["N/A"])
                    if cont_options and selected_contact != "N/A":
                        c_det = f_contacts[f_contacts['Customer contact'] == selected_contact].iloc[0]
                        st.write(f"📞 {c_det.get('Phone', '-')} | ✉️ {c_det.get('Email', '-')}")
                    else: st.write("📞 - | ✉️ -")

                r2_c1, r2_c2 = st.columns(2)
                with r2_c1:
                    m_list = df_machines[df_machines['Customer no'].apply(format_clean_str) == c_no]['Customer Machine'].tolist()
                    st.selectbox("🛠️ Machine number:", options=m_list if m_list else ["N/A"])
                with r2_c2:
                    staff_list = df_staff['Name'].tolist() if df_staff is not None else ["Admin"]
                    st.selectbox("✍️ Người lập báo giá:", options=staff_list)

                st.markdown(f'<div style="margin-top:10px; padding:12px; background-color:#f8f9fa; border-left:5px solid #ff4b4b; border-radius:4px;"><b>📍 Địa chỉ:</b> {cust_info["Full Information customer"]}</div>', unsafe_allow_html=True)
                st.divider()

                # --- TÌM KIẾM PHỤ TÙNG (FIX THẲNG HÀNG) ---
                st.subheader("🔍 Tìm Part Number")
                # Dùng layout mới để ép nút và input sát nhau
                col_search, col_add_btn = st.columns([4, 1])
                
                with col_search:
                    input_text = st.text_input("Mã phụ tùng", placeholder="Nhập mã cách nhau bởi dấu ; (Ví dụ: 2024956492;2031956280)", label_visibility="collapsed")
                
                with col_add_btn:
                    add_trigger = st.button("🛒 Thêm vào giỏ hàng", use_container_width=True, type="primary")

                if add_trigger and input_text:
                    list_search = [s.strip() for s in input_text.split(';') if s.strip()]
                    df_sp_raw['PN_MATCH'] = df_sp_raw['Part number'].apply(format_clean_str)
                    
                    found_count = 0
                    for code in list_search:
                        clean_code = format_clean_str(code)
                        match = df_sp_raw[df_sp_raw['PN_MATCH'] == clean_code]
                        
                        if not match.empty:
                            item = match.iloc[0]
                            # Xử lý VAT hiển thị %
                            vat_val = item['VAT']
                            vat_display = f"{int(float(vat_val)*100)}%" if pd.notna(vat_val) else "0%"
                            
                            st.session_state.cart.append({
                                "Part Number": item['Part number'],
                                "Part name": item['Part name'],
                                "Qty": 1,
                                "Unit": item['Unit'],
                                "VAT": vat_display,
                                "Unit Price": float(item['Giá bán']) if pd.notna(item['Giá bán']) else 0
                            })
                            found_count += 1
                    
                    if found_count > 0:
                        st.toast(f"✅ Đã thêm {found_count} mã!")
                    else:
                        st.error("❌ Không tìm thấy mã nào!")

                # --- BẢNG DANH SÁCH (ĐỊNH DẠNG TIỀN TỆ) ---
                st.markdown("### 📋 Danh sách phụ tùng đã chọn")
                if st.session_state.cart:
                    df_cart = pd.DataFrame(st.session_state.cart)
                    df_cart.insert(0, 'No', range(1, len(df_cart) + 1))
                    
                    st.data_editor(
                        df_cart,
                        column_config={
                            "No": st.column_config.NumberColumn("No", width="small"),
                            "Qty": st.column_config.NumberColumn("Qty", min_value=1, step=1),
                            "Unit Price": st.column_config.NumberColumn("Unit Price", format="%d"), # Hiển thị số nguyên
                            "VAT": st.column_config.TextColumn("VAT", width="small"),
                        },
                        use_container_width=True,
                        hide_index=True,
                        key="cart_table_v2"
                    )
                    
                    # CSS để làm bảng đẹp hơn và format số có dấu phẩy trong hiển thị (Streamlit Editor tự làm việc này)
                    if st.button("🗑️ Xoá toàn bộ bảng"):
                        st.session_state.cart = []
                        st.rerun()

                st.markdown("<br>" * 5, unsafe_allow_html=True)
                cs1, cs2, _ = st.columns([1.5, 1.5, 5])
                cs1.button("💾 Lưu Báo Giá", use_container_width=True)
                cs2.button("🛒 Đặt Hàng", use_container_width=True)

if __name__ == "__main__":
    main()
