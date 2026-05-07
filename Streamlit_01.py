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

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    # 1. SIDEBAR LUÔN HIỂN THỊ (Đưa lên đầu)
    st.sidebar.title("⚙️ HỆ THỐNG D&Q")
    menu_selection = st.sidebar.radio("📂 Danh mục chính:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])
    
    st.sidebar.divider()
    ty_gia_input = st.sidebar.number_input("Tỷ giá Euro:", value=31000, step=100)
    
    if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Khởi tạo session state
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'sub_action' not in st.session_state: st.session_state.sub_action = None

    # CSS
    st.markdown("""
        <style>
        .stVerticalBlock { gap: 0.8rem; }
        .address-box { margin-top: 10px; margin-bottom: 10px; padding: 12px; background-color: #f8f9fa; border-left: 5px solid #ff4b4b; border-radius: 4px; }
        </style>
    """, unsafe_allow_html=True)

    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
    df_sp_raw, df_mst, df_contact, df_machines, df_staff = load_all_data(url)

    if df_sp_raw is not None:
        
        # --- TRƯỜNG HỢP 1: BÁO GIÁ PHỤ TÙNG ---
        if menu_selection == "📄 Báo Giá Phụ Tùng":
            # Menu nút bấm ngang
            col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)
            with col_btn1:
                if st.button("➕ Tạo Báo Giá", use_container_width=True): st.session_state.sub_action = "create"
            with col_btn2:
                if st.button("🔍 Tra Cứu", use_container_width=True): st.session_state.sub_action = "search"

            if st.session_state.sub_action == "create":
                st.divider()
                # --- THÔNG TIN KHÁCH HÀNG ---
                c1, c2 = st.columns(2)
                with c1:
                    selected_customer = st.selectbox("🎯 Chọn khách hàng:", options=sorted(df_mst['Customer name'].unique()))
                    cust_info = df_mst[df_mst['Customer name'] == selected_customer].iloc[0]
                    c_no = format_as_int_str(cust_info['Customer no'])
                    st.write(f"**Cust No:** {c_no} | **MST:** {format_as_int_str(cust_info['Mã số thuế'])}")
                    
                    m_list = df_machines[df_machines['Customer no'].apply(format_as_int_str) == c_no]['Customer Machine'].tolist()
                    st.selectbox("⚙️ Machine number:", options=m_list if m_list else ["N/A"])

                with c2:
                    cont_list = df_contact[df_contact['Customer no'].apply(format_as_int_str) == c_no]['Customer contact'].tolist()
                    st.selectbox("👤 Contact Person:", options=cont_list if cont_list else ["N/A"])
                    staff_list = df_staff['Name'].tolist() if df_staff is not None else ["Admin"]
                    st.selectbox("✍️ Người lập:", options=staff_list)

                st.markdown(f'<div class="address-box"><b>📍 Địa chỉ:</b> {cust_info["Full Information customer"]}</div>', unsafe_allow_html=True)
                st.divider()

                # --- TÌM KIẾM PHỤ TÙNG ---
                st.subheader("🔍 Tìm Part Number")
                col_search, col_add = st.columns([4, 1])
                with col_search:
                    part_search = st.text_input("Nhập mã phụ tùng:", key="ps_input", help="Nhấn Enter sau khi nhập")
                
                if part_search:
                    # SỬA LỖI TÌM KIẾM: Ép cả 2 về String và xóa khoảng trắng
                    search_str = str(part_search).strip()
                    df_sp_raw['Part number_str'] = df_sp_raw['Part number'].astype(str).str.strip()
                    
                    match = df_sp_raw[df_sp_raw['Part number_str'] == search_str]
                    
                    if not match.empty:
                        item = match.iloc[0]
                        with col_add:
                            st.write("##")
                            if st.button("➕ Thêm", use_container_width=True, type="primary"):
                                # Lấy giá bán (Cột J) và xử lý số
                                unit_price = item['Giá bán']
                                st.session_state.cart.append({
                                    "Part Number": item['Part number'],
                                    "Part name": item['Part name'],
                                    "Qty": 1,
                                    "Unit": item['Unit'],
                                    "VAT": item['VAT'],
                                    "Unit Price": unit_price
                                })
                                st.toast(f"Đã thêm mã {search_str}")
                    else:
                        st.error(f"❌ Không tìm thấy mã '{search_str}' trong SP List. Vui lòng kiểm tra lại!")

                # --- BẢNG DANH SÁCH ---
                st.markdown("### 📋 Danh sách phụ tùng")
                if st.session_state.cart:
                    df_cart = pd.DataFrame(st.session_state.cart)
                    df_cart.insert(0, 'No', range(1, len(df_cart) + 1))
                    
                    st.data_editor(
                        df_cart,
                        column_config={
                            "Qty": st.column_config.NumberColumn("Qty", min_value=1),
                            "Part name": st.column_config.TextColumn("Part name", width="large")
                        },
                        use_container_width=True, hide_index=True, key="editor"
                    )
                    if st.button("🗑️ Xoá bảng"):
                        st.session_state.cart = []
                        st.rerun()

                # Nút điều khiển cuối
                st.markdown("<br>" * 10, unsafe_allow_html=True)
                cs1, cs2, _ = st.columns([1.5, 1.5, 5])
                cs1.button("💾 Lưu Báo Giá", use_container_width=True)
                cs2.button("🛒 Đặt Hàng", use_container_width=True)

        # --- TRƯỜNG HỢP 2: MASTER DATA ---
        elif menu_selection == "🗂️ Master Data":
            st.header("🗂️ Dữ liệu Master Data")
            st.session_state.sub_action = None # Reset sub-menu khi chuyển tab
            st.dataframe(df_sp_raw, use_container_width=True)

if __name__ == "__main__":
    main()
