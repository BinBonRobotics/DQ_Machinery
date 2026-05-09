import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# 1. Hàm làm sạch mã Part Number
def clean_code(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).split('.')[0].strip()
    return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

# 2. Hàm đọc dữ liệu dùng Service Account (JSON/Secrets)
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
        
        try:
            df_off_desc = conn.read(spreadsheet=url, worksheet="offer description")
            df_off_head = conn.read(spreadsheet=url, worksheet="offer header")
            df_off_track = conn.read(spreadsheet=url, worksheet="offer tracking")
        except:
            df_off_desc = df_off_head = df_off_track = pd.DataFrame()

        return df_sp, df_mst, df_con, df_mac, df_staff, df_off_desc, df_off_head, df_off_track
    except Exception as e:
        st.error(f"❌ Lỗi kết nối Google Sheets: {e}")
        return [None] * 8

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    data = load_all_data()
    df_sp, df_mst, df_con, df_mac, df_staff, df_off_desc, df_off_head, df_off_track = data
    if df_mst is None: return

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
                cust_options = sorted(df_mst['Customer name'].dropna().unique())
                cust_name = st.selectbox("🎯 Khách hàng:", options=cust_options)
                row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
                c_no_val = row_mst.get('Customer no', row_mst.get('Customer\nno', ''))
                c_no = str(c_no_val).split('.')[0] if pd.notna(c_no_val) else "N/A"
                mst = str(row_mst.get('Mã số thuế', '-'))
                st.info(f"**Cust No:** {c_no} | **MST:** {mst}")
            with r1c2:
                f_conts = df_con[df_con.iloc[:, 1].astype(str).str.contains(clean_code(c_no))] if df_con is not None else pd.DataFrame()
                list_conts = f_conts.iloc[:, 7].dropna().unique().tolist() if not f_conts.empty else []
                st.selectbox("👤 Contact Person:", options=list_conts if list_conts else ["N/A"])
                addr = row_mst.get('Địa chỉ', row_mst.get('Full Information customer', '-'))
                st.markdown(f"📍 **Địa chỉ:** {str(addr)}")

            r2c1, r2c2 = st.columns(2)
            with r2c1:
                f_macs = df_mac[df_mac.iloc[:, 1].astype(str).str.contains(clean_code(c_no))] if df_mac is not None else pd.DataFrame()
                list_macs = f_macs.iloc[:, 4].dropna().unique().tolist() if not f_macs.empty else []
                st.selectbox("🤖 Machine Number:", options=list_macs if list_macs else ["N/A"])
            with r2c2:
                list_staff = df_staff['Name'].dropna().unique().tolist() if 'Name' in df_staff.columns else ["Admin"]
                st.selectbox("✍️ Người lập báo giá:", options=list_staff)

            st.divider()
            
            # --- TÌM PART NUMBER ---
            st.subheader("🔍 Tìm Part Number")
            input_search = st.text_input("Nhập mã (ví dụ: 3608080970; 4007010482...):")
            if st.session_state.not_found_codes:
                st.error(f"❌ Không tìm thấy: {', '.join(st.session_state.not_found_codes)}")

            if st.button("🛒 Thêm vào giỏ hàng", type="primary"):
                if input_search:
                    st.session_state.not_found_codes = []
                    codes = [clean_code(c) for c in input_search.split(';') if c.strip()]
                    df_sp['CLEAN_PN'] = df_sp['Part number'].apply(clean_code)
                    for code in codes:
                        match = df_sp[df_sp['CLEAN_PN'] == code]
                        if not match.empty:
                            item = match.iloc[0]
                            price = item.get('Giá bán', 0)
                            st.session_state.cart.append({
                                "Part Number": item['Part number'], "Part name": item['Part name'],
                                "Qty": 1, "Unit": item['Unit'], "VAT": 8, # Để giá trị là 8
                                "Unit Price": float(price) if pd.notna(price) else 0.0,
                                "%Dist": 0.0, "Xoá": False
                            })
                        else:
                            st.session_state.not_found_codes.append(code)
                    st.rerun()

            # --- BẢNG DANH SÁCH CHI TIẾT (KHÓA DỮ LIỆU CHỈ MỞ QTY & %DIST) ---
            if st.session_state.cart:
                st.markdown("### 📋 Danh sách chi tiết")
                df_cart = pd.DataFrame(st.session_state.cart)
                df_cart.insert(0, 'No.', range(1, len(df_cart) + 1))
                df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)
                
                edited_df = st.data_editor(
                    df_cart[["No.", "Part Number", "Part name", "Qty", "Unit", "VAT", "Unit Price", "%Dist", "Amount", "Xoá"]],
                    column_config={
                        "No.": st.column_config.NumberColumn("No.", width=40, disabled=True),
                        "Part Number": st.column_config.TextColumn("Part Number", disabled=True),
                        "Part name": st.column_config.TextColumn("Part name", disabled=True),
                        "Unit": st.column_config.TextColumn("Unit", disabled=True),
                        "VAT": st.column_config.NumberColumn("VAT", format="%d", disabled=True),
                        "Unit Price": st.column_config.NumberColumn("Unit Price", format="%,d", disabled=True),
                        "Amount": st.column_config.NumberColumn("Amount", format="%,d", disabled=True),
                        # Chỉ cột Qty và %Dist là không có disabled=True
                        "Qty": st.column_config.NumberColumn("Qty", width=60, min_value=1),
                        "%Dist": st.column_config.NumberColumn("%Dist", width=70, format="%d%%"),
                        "Xoá": st.column_config.CheckboxColumn("Xoá", width=50)
                    },
                    use_container_width=True, hide_index=True, key="cart_editor"
                )

                if not edited_df.equals(df_cart[["No.", "Part Number", "Part name", "Qty", "Unit", "VAT", "Unit Price", "%Dist", "Amount", "Xoá"]]):
                    new_cart = []
                    for i, row in edited_df.iterrows():
                        if not row['Xoá']:
                            item = st.session_state.cart[i].copy()
                            item['Qty'] = row['Qty']
                            item['%Dist'] = row['%Dist']
                            new_cart.append(item)
                    st.session_state.cart = new_cart
                    st.rerun()

                # --- BẢNG TỔNG KẾT BÁO GIÁ (KHÓA TẤT CẢ TRỪ SHIPMENT COST) ---
                st.divider()
                total_amt = df_cart['Amount'].sum()
                sub_total = total_amt + st.session_state.ship_cost
                vat_amount = sub_total * 0.08
                grand_total = sub_total + vat_amount

                summary_df = pd.DataFrame([
                    {"Nội dung": "Total Amount", "Số tiền (VND)": total_amt},
                    {"Nội dung": "Shipment Cost", "Số tiền (VND)": st.session_state.ship_cost},
                    {"Nội dung": "Sub-Total", "Số tiền (VND)": sub_total},
                    {"Nội dung": "VAT (8%)", "Số tiền (VND)": vat_amount},
                    {"Nội dung": "GRAND TOTAL", "Số tiền (VND)": grand_total}
                ])

                _, col_calc = st.columns([2, 1.5])
                with col_calc:
                    st.markdown("**Tổng kết báo giá**")
                    edited_summary = st.data_editor(
                        summary_df,
                        column_config={
                            "Nội dung": st.column_config.TextColumn("Nội dung", disabled=True),
                            "Số tiền (VND)": st.column_config.NumberColumn("Số tiền (VND)", format="%,d")
                        },
                        # Khóa cột "Số tiền" một cách logic: Chỉ cho phép sửa nếu đó là hàng Shipment Cost
                        # Thực tế: Ta dùng st.rerun để đè lại giá trị nếu user cố tình sửa các hàng kia.
                        hide_index=True, 
                        use_container_width=True, 
                        key="summary_editor"
                    )
                    
                    # Logic cập nhật và khóa giá trị
                    new_ship = edited_summary.iloc[1]["Số tiền (VND)"]
                    
                    # Nếu user sửa bất kỳ hàng nào khác (0, 2, 3, 4), giá trị sẽ tự reset về đúng công thức
                    if (edited_summary.iloc[0]["Số tiền (VND)"] != total_amt or 
                        edited_summary.iloc[2]["Số tiền (VND)"] != sub_total or
                        edited_summary.iloc[3]["Số tiền (VND)"] != vat_amount or
                        edited_summary.iloc[4]["Số tiền (VND)"] != grand_total or
                        new_ship != st.session_state.ship_cost):
                        
                        st.session_state.ship_cost = new_ship # Cập nhật cái duy nhất được phép
                        st.rerun() # Ghi đè lại toàn bộ bảng theo công thức chuẩn
                
                st.button("💾 Lưu báo giá", use_container_width=True, type="primary")

        elif st.session_state.sub_action == "search":
            st.subheader("🔍 Order Management")
            t1, t2, t3 = st.tabs(["📄 Offers List", "🚚 Tracking", "📊 Reports"])
            with t1: st.dataframe(df_off_head, use_container_width=True)

    elif menu_selection == "🗂️ Master Data":
        st.dataframe(df_sp, use_container_width=True)

if __name__ == "__main__":
    main()
