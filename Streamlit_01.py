import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re

# 1. Hàm làm sạch mã Part Number
def clean_code(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).split('.')[0].strip()
    return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

@st.cache_data(ttl=60)
def load_all_data(url):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_sp = conn.read(spreadsheet=url, worksheet="SP List", ttl=0)
        df_mst = conn.read(spreadsheet=url, worksheet="Customer_MST", ttl=0)
        df_con = conn.read(spreadsheet=url, worksheet="Customer_Contact", ttl=0)
        df_mac = conn.read(spreadsheet=url, worksheet="List of machines", ttl=0)
        df_staff = conn.read(spreadsheet=url, worksheet="Staff", ttl=0)
        return df_sp, df_mst, df_con, df_mac, df_staff
    except Exception as e:
        st.error(f"Lỗi kết nối dữ liệu: {e}")
        return None, None, None, None, None

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
    df_sp, df_mst, df_con, df_mac, df_staff = load_all_data(url)

    # Khởi tạo session state
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'sub_action' not in st.session_state: st.session_state.sub_action = "create"
    if 'ship_cost' not in st.session_state: st.session_state.ship_cost = 0.0
    if 'not_found_codes' not in st.session_state: st.session_state.not_found_codes = []

    # --- SIDEBAR ---
    st.sidebar.title("⚙️ Cấu hình")
    ty_gia = st.sidebar.number_input("Tỷ giá Euro (VND):", value=31000, step=100)
    if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.divider()
    menu_selection = st.sidebar.radio("📂 Danh mục chính:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])

    if menu_selection == "📄 Báo Giá Phụ Tùng":
        col_btn1, col_btn2, _ = st.columns([1, 1, 4])
        if col_btn1.button("➕ Tạo Báo Giá", use_container_width=True, type="primary" if st.session_state.sub_action=="create" else "secondary"):
            st.session_state.sub_action = "create"
        if col_btn2.button("🔍 Tra Cứu", use_container_width=True, type="primary" if st.session_state.sub_action=="search" else "secondary"):
            st.session_state.sub_action = "search"
        
        st.divider()

        if st.session_state.sub_action == "create":
            if df_mst is not None:
                r1c1, r1c2 = st.columns(2)
                with r1c1:
                    cust_name = st.selectbox("🎯 Khách hàng:", options=sorted(df_mst['Customer name'].unique()))
                    row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
                    c_no_raw = row_mst.get('Customer no', row_mst.get('Customer\nno', ''))
                    c_no = str(c_no_raw).split('.')[0] if pd.notna(c_no_raw) else "N/A"
                    mst = str(row_mst.get('Mã số thuế', '-'))
                    st.info(f"**Cust No:** {c_no} | **MST:** {mst}")
                
                with r1c2:
                    f_conts = df_con[df_con.iloc[:, 1].astype(str).str.contains(clean_code(c_no))]
                    list_conts = f_conts.iloc[:, 7].dropna().unique().tolist()
                    st.selectbox("👤 Contact Person:", options=list_conts if list_conts else ["N/A"])
                    addr = row_mst.get('Địa chỉ', row_mst.get('Full Information customer', '-'))
                    st.markdown(f"📍 **Địa chỉ:** {str(addr)}")

                r2c1, r2c2 = st.columns(2)
                with r2c1:
                    f_machines = df_mac[df_mac.iloc[:, 1].astype(str).str.contains(clean_code(c_no))]
                    list_machines = f_machines.iloc[:, 3].dropna().unique().tolist() if not f_machines.empty else []
                    st.selectbox("🤖 Machine Number:", options=list_machines if list_machines else ["N/A"])
                
                with r2c2:
                    list_staff = df_staff.iloc[:, 1].dropna().unique().tolist() if df_staff is not None else []
                    st.selectbox("✍️ Người lập báo giá:", options=list_staff if list_staff else ["Admin"])

            st.divider()

            st.subheader("🔍 Tìm Part Number")
            input_search = st.text_input("Nhập mã (ví dụ: 4007010482; 2024956492...):")
            
            if st.session_state.not_found_codes:
                st.error(f"❌ Không tìm thấy Part Number: {', '.join(st.session_state.not_found_codes)}")

            if st.button("🛒 Thêm vào giỏ hàng", type="primary"):
                if input_search:
                    st.session_state.not_found_codes = [] 
                    codes = [clean_code(c) for c in input_search.split(';') if c.strip()]
                    df_sp['CLEAN_PN'] = df_sp.iloc[:, 1].apply(clean_code)
                    
                    for code in codes:
                        match = df_sp[df_sp['CLEAN_PN'] == code]
                        if not match.empty:
                            item = match.iloc[0]
                            price = item.iloc[18] if len(item) > 18 else 0
                            vat_val = item.iloc[12] if len(item) > 12 else 0.08
                            try:
                                vat_f = float(vat_val)
                                vat_display = f"{int(vat_f*100)}%"
                            except:
                                vat_f = 0.08
                                vat_display = "8%"
                            
                            st.session_state.cart.append({
                                "Part Number": item.iloc[1],
                                "Part name": item.iloc[4],
                                "Qty": 1,
                                "Unit": item.iloc[7],
                                "VAT": vat_display,
                                "vat_num": vat_f,
                                "Unit Price": float(price) if pd.notna(price) else 0.0,
                                "%Dist": 0.0,
                                "Xoá": False
                            })
                        else:
                            st.session_state.not_found_codes.append(code)
                    st.rerun()

            if st.session_state.cart:
                st.markdown("### 📋 Danh sách chi tiết")
                df_cart = pd.DataFrame(st.session_state.cart)
                df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)
                
                display_cols = ["Part Number", "Part name", "Qty", "Unit", "VAT", "Unit Price", "%Dist", "Amount", "Xoá"]
                df_cart_render = df_cart[display_cols].copy()
                df_cart_render.insert(0, 'No', range(1, len(df_cart_render) + 1))

                # --- CẬP NHẬT: PHÂN QUYỀN CHỈNH SỬA CỘT ---
                edited_df = st.data_editor(
                    df_cart_render,
                    column_config={
                        "No": st.column_config.NumberColumn("No", width=35, disabled=True),
                        "Part Number": st.column_config.TextColumn("Part Number", disabled=True),
                        "Part name": st.column_config.TextColumn("Part name", disabled=True),
                        "Qty": st.column_config.NumberColumn("Qty", width=60, min_value=1, disabled=False), # Cho phép sửa
                        "Unit": st.column_config.TextColumn("Unit", width=50, disabled=True),
                        "VAT": st.column_config.TextColumn("VAT", width=50, disabled=True),
                        "Unit Price": st.column_config.NumberColumn("Unit Price", format="%,d", disabled=True),
                        "%Dist": st.column_config.NumberColumn("%Dist", width=60, min_value=0.0, max_value=100.0, disabled=False), # Cho phép sửa
                        "Amount": st.column_config.NumberColumn("Amount", format="%,d", disabled=True),
                        "Xoá": st.column_config.CheckboxColumn("Xoá", width=50, disabled=False)
                    },
                    use_container_width=True,
                    hide_index=True,
                    key="main_editor"
                )

                if not edited_df.equals(df_cart_render):
                    remaining_indices = edited_df[edited_df['Xoá'] == False].index.tolist()
                    new_cart = []
                    for i in remaining_indices:
                        item = st.session_state.cart[i].copy()
                        # Cập nhật giá trị mới từ bảng editor vào session state
                        item['Qty'] = edited_df.loc[i, 'Qty']
                        item['%Dist'] = edited_df.loc[i, '%Dist']
                        new_cart.append(item)
                    st.session_state.cart = new_cart
                    st.rerun()

                st.markdown("---")
                total_amt = df_cart['Amount'].sum()
                total_vat = (df_cart['Amount'] * df_cart['vat_num']).sum()

                c_left, c_right = st.columns([6, 4])
                with c_right:
                    def summary_row(label, value, is_input=False, is_bold=False):
                        sc1, sc2 = st.columns([1.5, 2])
                        with sc1: st.write(f"**{label}**" if is_bold else label)
                        with sc2:
                            if is_input:
                                res = st.number_input(label, label_visibility="collapsed", 
                                                      value=st.session_state.ship_cost, step=1000.0, format="%.f")
                                if res != st.session_state.ship_cost:
                                    st.session_state.ship_cost = res
                                    st.rerun()
                            else:
                                st.write(f"**{value:,.0f} VND**" if is_bold else f"{value:,.0f} VND")

                    summary_row("Total Amount:", total_amt)
                    summary_row("Shipment Cost:", 0, is_input=True)
                    sub_total = total_amt + st.session_state.ship_cost
                    summary_row("Sub-Total:", sub_total)
                    summary_row("VAT:", total_vat)
                    grand_total = sub_total + total_vat
                    summary_row("Grand Total:", grand_total, is_bold=True)

                if st.button("🗑️ Xóa sạch toàn bộ bảng"):
                    st.session_state.cart = []
                    st.session_state.ship_cost = 0.0
                    st.session_state.not_found_codes = []
                    st.rerun()

                st.write("")
                b1, b2, _ = st.columns([1.5, 1.5, 4])
                b1.button("💾 Lưu báo giá", use_container_width=True)
                b2.button("✅ Xác nhận đặt hàng", use_container_width=True)

    elif menu_selection == "🗂️ Master Data":
        st.header("🗂️ Master Data")
        if df_sp is not None:
            st.dataframe(df_sp, use_container_width=True)

if __name__ == "__main__":
    main()
