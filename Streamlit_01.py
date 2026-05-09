import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# 1. Hàm làm sạch mã Part Number
def clean_code(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).split('.')[0].strip()
    return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

@st.cache_data(ttl=60)
def load_all_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
        df_sp = conn.read(spreadsheet=url, worksheet="SP List")
        df_mst = conn.read(spreadsheet=url, worksheet="Customer_MST")
        df_con = conn.read(spreadsheet=url, worksheet="Customer_Contact")
        df_mac = conn.read(spreadsheet=url, worksheet="List of machines")
        df_staff = conn.read(spreadsheet=url, worksheet="Staff")
        return df_sp, df_mst, df_con, df_mac, df_staff
    except Exception as e:
        st.error(f"❌ Lỗi kết nối: {e}")
        return [None] * 5

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    data = load_all_data()
    df_sp, df_mst, df_con, df_mac, df_staff = data
    if df_mst is None: return

    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'sub_action' not in st.session_state: st.session_state.sub_action = "create"
    if 'ship_cost' not in st.session_state: st.session_state.ship_cost = 0.0

    # --- SIDEBAR ---
    st.sidebar.title("⚙️ Cấu hình")
    if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    menu_selection = st.sidebar.radio("📂 Danh mục chính:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])

    if menu_selection == "📄 Báo Giá Phụ Tùng":
        col_btn1, col_btn2, _ = st.columns([1.5, 2, 3])
        if col_btn1.button("➕ Tạo Báo Giá", use_container_width=True, type="primary" if st.session_state.sub_action=="create" else "secondary"):
            st.session_state.sub_action = "create"
        if col_btn2.button("🔍 Order Management", use_container_width=True, type="primary" if st.session_state.sub_action=="search" else "secondary"):
            st.session_state.sub_action = "search"
        
        st.divider()

        if st.session_state.sub_action == "create":
            # --- THÔNG TIN KHÁCH HÀNG ---
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                cust_name = st.selectbox("🎯 Khách hàng:", options=sorted(df_mst['Customer name'].dropna().unique()))
                row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
                c_no = str(row_mst.get('Customer no', row_mst.get('Customer\nno', ''))).split('.')[0]
                st.info(f"**Cust No:** {c_no} | **MST:** {row_mst.get('Mã số thuế', '-')}")
            with r1c2:
                st.selectbox("👤 Contact Person:", options=["N/A"])
                st.markdown(f"📍 **Địa chỉ:** {str(row_mst.get('Địa chỉ', '-'))}")

            st.divider()
            
            # --- TÌM PART NUMBER ---
            st.subheader("🔍 Tìm Part Number")
            input_search = st.text_input("Nhập mã (cách nhau bởi dấu ;):")
            if st.button("🛒 Thêm vào giỏ hàng", type="primary"):
                if input_search:
                    codes = [clean_code(c) for c in input_search.split(';') if c.strip()]
                    df_sp['CLEAN_PN'] = df_sp['Part number'].apply(clean_code)
                    for code in codes:
                        match = df_sp[df_sp['CLEAN_PN'] == code]
                        if not match.empty:
                            item = match.iloc[0]
                            st.session_state.cart.append({
                                "Part Number": item['Part number'], "Part name": item['Part name'],
                                "Qty": 1, "Unit": item['Unit'], "VAT": 8,
                                "Unit Price": float(item.get('Giá bán', 0)), "%Dist": 0.0, "Xoá": False
                            })
                    st.rerun()

            # --- BẢNG CHI TIẾT ---
            if st.session_state.cart:
                st.markdown("### 📋 Danh sách chi tiết")
                df_cart = pd.DataFrame(st.session_state.cart)
                df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)
                
                edited_df = st.data_editor(
                    df_cart,
                    column_config={
                        "Part Number": st.column_config.TextColumn(disabled=True),
                        "Part name": st.column_config.TextColumn(disabled=True),
                        "Unit": st.column_config.TextColumn(disabled=True),
                        "VAT": st.column_config.NumberColumn(format="%d", disabled=True),
                        "Unit Price": st.column_config.NumberColumn(format="%,d", disabled=True),
                        "Amount": st.column_config.NumberColumn(format="%,d", disabled=True),
                        "Qty": st.column_config.NumberColumn(min_value=1),
                        "%Dist": st.column_config.NumberColumn(format="%d%%"),
                    },
                    use_container_width=True, hide_index=True, key="main_editor"
                )

                # Cập nhật giỏ hàng nếu có thay đổi Qty, %Dist hoặc Xoá
                if not edited_df.equals(df_cart):
                    new_cart = []
                    for i, row in edited_df.iterrows():
                        if not row['Xoá']:
                            item = st.session_state.cart[i].copy()
                            item['Qty'] = row['Qty']
                            item['%Dist'] = row['%Dist']
                            new_cart.append(item)
                    st.session_state.cart = new_cart
                    st.rerun()

                # --- BẢNG TỔNG KẾT (CỰC KỲ ỔN ĐỊNH) ---
                st.divider()
                total_amt = edited_df['Amount'].sum()
                
                _, col_calc = st.columns([2, 1.5])
                with col_calc:
                    st.markdown("#### Tổng kết báo giá")
                    
                    # Ô nhập Shipment Cost riêng biệt để không gây lỗi bảng
                    ship_input = st.number_input("Nhập Shipment Cost (VND):", value=float(st.session_state.ship_cost), step=1000.0, format="%.0f")
                    if ship_input != st.session_state.ship_cost:
                        st.session_state.ship_cost = ship_input
                        st.rerun()

                    sub_total = total_amt + st.session_state.ship_cost
                    vat_val = sub_total * 0.08
                    grand_total = sub_total + vat_val

                    # Hiển thị bảng tổng kết dạng Table (Grey out tự nhiên, không thể sửa)
                    summary_data = {
                        "Nội dung": ["Total Amount", "Shipment Cost", "Sub-Total", "VAT (8%)", "GRAND TOTAL"],
                        "Số tiền (VND)": [f"{total_amt:,.0f}", f"{st.session_state.ship_cost:,.0f}", 
                                         f"{sub_total:,.0f}", f"{vat_val:,.0f}", f"{grand_total:,.0f}"]
                    }
                    st.table(pd.DataFrame(summary_data))
                
                st.button("💾 Lưu báo giá", use_container_width=True, type="primary")

        elif st.session_state.sub_action == "search":
            st.info("Tính năng Order Management đang được cập nhật...")

    elif menu_selection == "🗂️ Master Data":
        st.dataframe(df_sp, use_container_width=True)

if __name__ == "__main__":
    main()
