import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. CÁC CHƯƠNG TRÌNH CON (FUNCTIONS)
# ==========================================

@st.cache_data(ttl=3600)
def load_data(url_link, sheet_name):
    """Tải dữ liệu và chuẩn hóa tên cột + định dạng số"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=url_link, worksheet=sheet_name, ttl=0)
        # 1. Xóa khoảng trắng thừa ở tên cột
        data.columns = data.columns.str.strip()
        
        # 2. Tự động xử lý các cột số dễ bị lỗi thập phân .0
        cols_to_fix = ['Customer no', 'Tax Code', 'Machine No', 'Part number', 'Price']
        for col in data.columns:
            if col in cols_to_fix:
                # Chuyển về số, lỗi thì để NaN, sau đó thay NaN bằng 0, ép về kiểu Int rồi thành chuỗi
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(int).astype(str)
                # Nếu là '0' thì để trống cho đẹp giao diện
                data[col] = data[col].replace('0', '')
                
        return data
    except Exception as e:
        st.error(f"❌ Lỗi khi tải Sheet '{sheet_name}': {e}")
        return None

def chuc_nang_dang_nhap(df_user):
    """Xử lý đăng nhập"""
    st.markdown("---")
    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        with st.form("login_form"):
            user_input = st.text_input("Tên đăng nhập / Email")
            pass_input = st.text_input("Mật khẩu", type="password")
            if st.form_submit_button("Xác nhận Đăng nhập"):
                if user_input and pass_input:
                    user_match = df_user[
                        ((df_user['email'].astype(str) == user_input.strip()) | (df_user['name'].astype(str) == user_input.strip())) & 
                        (df_user['password'].astype(str) == pass_input.strip())
                    ]
                    if not user_match.empty:
                        st.session_state['logged_in'] = True
                        st.session_state['display_name'] = user_match.iloc[0]['name']
                        st.session_state['user_role'] = user_match.iloc[0]['role']
                        st.rerun()
                    else:
                        st.error("Sai tài khoản hoặc mật khẩu!")

def chuc_nang_tra_cuu_vat_tu(df_vattu):
    """Tra cứu phụ tùng"""
    st.header("🔍 Hệ thống Tra cứu Phụ tùng")
    col_search, _ = st.columns([2, 6])
    with col_search:
        search_query = st.text_input("Nhập Part numbers (cách nhau bởi dấu ;):")
    
    if search_query:
        list_ma = [s.strip() for s in search_query.replace(',', ';').split(';') if s.strip()]
        result = df_vattu[df_vattu['Part number'].astype(str).isin(list_ma)]
        if not result.empty:
            st.dataframe(result, use_container_width=True)
        else:
            st.warning("❌ Không tìm thấy mã.")
    else:
        st.dataframe(df_vattu, use_container_width=True)

def chuc_nang_bao_gia(df_vattu, df_customer):
    """Tạo báo giá chuyên nghiệp"""
    st.header("📄 Tạo Báo giá Phụ tùng")
    
    if df_customer is None or df_customer.empty:
        st.error("Dữ liệu khách hàng trống!")
        return

    st.subheader("1. Thông tin khách hàng")
    
    # Layout nhỏ lại tỷ lệ [2:6]
    col_sel, _ = st.columns([2, 6])
    with col_sel:
        list_customers = sorted(df_customer['Customer-name'].dropna().unique().tolist())
        selected_customer = st.selectbox("Chọn khách hàng:", ["-- Chọn khách hàng --"] + list_customers)

    if selected_customer != "-- Chọn khách hàng --":
        cus_info = df_customer[df_customer['Customer-name'] == selected_customer]
        
        c1, c2, c3 = st.columns(3)
        with c1:
            # Customer no đã được ép kiểu sạch ở load_data
            st.text_input("Customer no:", value=cus_info.iloc[0]['Customer no'], disabled=True)
            m_types = sorted(cus_info['Machine-Type'].dropna().unique().tolist())
            selected_m_type = st.selectbox("Machine Type:", m_types)
        
        with c2:
            # Tax Code đã được ép kiểu sạch ở load_data
            st.text_input("Tax Code:", value=cus_info.iloc[0]['Tax Code'], disabled=True)
            m_nos = sorted(cus_info[cus_info['Machine-Type'] == selected_m_type]['Machine No'].dropna().unique().tolist())
            selected_m_no = st.selectbox("Machine No:", m_nos)
            
        with c3:
            st.text_area("Address:", value=str(cus_info.iloc[0]['Address']), disabled=True, height=100)

        st.divider()
        st.subheader("2. Chọn phụ tùng vào Offer")
        
        if 'cart' not in st.session_state:
            st.session_state['cart'] = []

        ca, cb, cc = st.columns([3, 1, 1])
        with ca:
            part_input = st.text_input("Nhập mã phụ tùng:")
        with cb:
            qty_input = st.number_input("Số lượng:", min_value=1, value=1)
        with cc:
            st.write("##")
            if st.button("➕ Thêm"):
                part_match = df_vattu[df_vattu['Part number'].astype(str) == part_input.strip()]
                if not part_match.empty:
                    st.session_state['cart'].append({
                        'Part No': part_input,
                        'Description': part_match.iloc[0]['Part name'],
                        'Qty': qty_input,
                        'Price': part_match.iloc[0]['Price']
                    })
                    st.success("Đã thêm!")
                else:
                    st.error("Mã không tồn tại!")

        if st.session_state['cart']:
            st.table(pd.DataFrame(st.session_state['cart']))
            if st.button("🗑️ Xóa danh sách"):
                st.session_state['cart'] = []
                st.rerun()

# ==========================================
# 2. CHƯƠNG TRÌNH CHÍNH (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        df_user = load_data(url, "members") 
        st.title("🛡️ D&Q Machinery - Portal")
        if df_user is not None:
            chuc_nang_dang_nhap(df_user)
    else:
        st.sidebar.markdown(f"### 👤 {st.session_state['display_name']}")
        st.sidebar.markdown(f"**Quyền hạn:** `{st.session_state['user_role']}`")
        if st.sidebar.button("🚪 Đăng xuất"):
            st.session_state['logged_in'] = False
            st.rerun()

        st.sidebar.divider()
        menu = st.sidebar.radio("CHỨC NĂNG", ["🔍 Quản lý Phụ tùng", "📄 Báo giá Phụ tùng"])

        df_vattu = load_data(url, "SP-List")
        df_customer = load_data(url, "Customer-machine")

        if menu == "🔍 Quản lý Phụ tùng":
            if df_vattu is not None:
                chuc_nang_tra_cuu_vat_tu(df_vattu)
        else:
            if df_vattu is not None and df_customer is not None:
                chuc_nang_bao_gia(df_vattu, df_customer)

if __name__ == "__main__":
    main()
