import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime

# --- 1. CẤU HÌNH & KẾT NỐI ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

def clean_code(val):
    if pd.isna(val) or val == "": return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(val).split('.')[0]).strip().upper()

def format_vnd(value):
    return f"{int(round(value)):,}"

@st.cache_data(ttl=2)
def load_all_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_sp = conn.read(spreadsheet=SHEET_URL, worksheet="SP List")
        df_mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST")
        df_con = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact")
        df_mac = conn.read(spreadsheet=SHEET_URL, worksheet="List of machines")
        df_staff = conn.read(spreadsheet=SHEET_URL, worksheet="Staff")
        df_h_stored = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Header")
        df_d_stored = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details")
        
        for df in [df_h_stored, df_d_stored]:
            if df is not None and 'Offer_No' in df.columns:
                df['Offer_No'] = df['Offer_No'].astype(str).str.strip()
        return [df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored]
    except Exception as e:
        return [None] * 7

def update_sheet(worksheet_name, dataframe):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=dataframe)

def main():
    st.set_page_config(page_title="D&Q Machinery Management", layout="wide")
    
    # 2.1 Sidebar cố định
    with st.sidebar:
        st.header("Báo Giá Phụ Tùng")
        st.write("---")
        st.number_input("Tỷ giá (EUR/VND):", value=28000, step=100)
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear(); st.rerun()

    data_list = load_all_data()
    if data_list[0] is None: 
        st.error("Không thể tải dữ liệu từ Google Sheets"); return
    df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored = data_list

    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'ship_cost' not in st.session_state: st.session_state.ship_cost = 0
    if 'current_tab' not in st.session_state: st.session_state.current_tab = "Tạo báo giá"

    # 2.2 Điều hướng
    c_nav1, c_nav2 = st.columns(2)
    with c_nav1:
        if st.button("➕ Tạo báo giá", use_container_width=True, type="primary" if st.session_state.current_tab == "Tạo báo giá" else "secondary"):
            st.session_state.current_tab = "Tạo báo giá"; st.rerun()
    with c_nav2:
        if st.button("📋 Order Management", use_container_width=True, type="primary" if st.session_state.current_tab == "Order Management" else "secondary"):
            st.session_state.current_tab = "Order Management"; st.rerun()

    st.write("---")

    # --- 3. TRANG TẠO BÁO GIÁ ---
    if st.session_state.current_tab == "Tạo báo giá":
        # Logic bảo vệ để tránh lỗi index khi đổi khách hàng
        c1, c2 = st.columns(2)
        with c1:
            cust_list = sorted(df_mst['Customer name'].dropna().unique())
            cust_name = st.selectbox("🎯 Khách hàng:", options=cust_list)
            
            row_mst = df_mst[df_mst['Customer name'] == cust_name]
            if not row_mst.empty:
                info = row_mst.iloc[0]
                st.info(f"**Cust No:** {str(info.get('Customer no', '')).split('.')[0]} | **MST:** {info.get('Mã số thuế', '-')}")
                st.markdown(f"📍 **Địa chỉ:** {info.get('Địa chỉ', '-')}")
            else: st.warning("Không tìm thấy thông tin khách hàng")

        with c2:
            con_list = df_con[df_con['Customer name'] == cust_name]['Customer contact'].dropna().unique()
            contact_person = st.selectbox("👤 Contact Person:", options=con_list if len(con_list)>0 else ["N/A"])
            
            mac_list = df_mac[df_mac['Customers'] == cust_name]['Machine No.'].dropna().unique()
            machine_no = st.selectbox("🤖 Machine Number:", options=mac_list if len(mac_list)>0 else ["N/A"])
            
            staff_list = df_staff['Name'].dropna().unique()
            staff_name = st.selectbox("✍️ Người lập báo giá:", options=staff_list)

        c3, c4 = st.columns(2)
        with c3:
            off_no = st.text_input("🆔 Offer No:", value=f"OFF-{datetime.now().strftime('%Y%m%d%H%M')}")
        with c4:
            off_date = st.date_input("📅 Offer Date:", value=datetime.now())

        st.divider()

        # Tìm kiếm & Thêm
        col_search, _ = st.columns([2, 2])
        with col_search:
            search_pn = st.text_input("🔍 Nhập Part Number:")
            if st.button("🛒 Thêm vào giỏ hàng", use_container_width=True, type="primary"):
                if search_pn:
                    match = df_sp[df_sp['Part number'].apply(clean_code) == clean_code(search_pn)]
                    if not match.empty:
                        item = match.iloc[0]
                        st.session_state.cart.append({
                            "No": len(st.session_state.cart) + 1,
                            "Part Number": item['Part number'], "Part Name": item['Part name'],
                            "Qty": 1.0, "Unit": item['Unit'], "VAT": 8,
                            "Unit Price": float(pd.to_numeric(item['Giá bán'], errors='coerce') or 0),
                            "%Dist": 0.0, "Xoá": False
                        })
                        st.rerun()
                    else: st.error(f"❌ Không tìm thấy mã: {search_pn}")

        # Bảng chi tiết
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)
            
            edited_df = st.data_editor(
                df_cart, use_container_width=True, hide_index=True,
                column_config={
                    "No": st.column_config.NumberColumn(disabled=True),
                    "Part Number": st.column_config.TextColumn(disabled=True),
                    "Part Name": st.column_config.TextColumn(disabled=True),
                    "Qty": st.column_config.NumberColumn(min_value=1, format="%d"),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(disabled=True, format="%d"),
                    "Unit Price": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
                    "%Dist": st.column_config.NumberColumn(min_value=0, max_value=100, format="%d"),
                    "Amount": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
                    "Xoá": st.column_config.CheckboxColumn()
                }
            )
            
            if not edited_df.equals(df_cart):
                st.session_state.cart = edited_df[~edited_df['Xoá']].to_dict('records')
                st.rerun()

            # TỔNG KẾT BÁO GIÁ (Summary)
            st.write("### 📊 Tổng kết báo giá")
            c_ship, _ = st.columns([2, 2])
            with c_ship:
                ship_input = st.text_input("🚚 Shipment Cost (VND):", value=f"{st.session_state.ship_cost:,}")
                try: st.session_state.ship_cost = int(re.sub(r'[^0-9]', '', ship_input))
                except: st.session_state.ship_cost = 0

            total_amt = edited_df['Amount'].sum()
            ship_cost = st.session_state.ship_cost
            sub_total = total_amt + ship_cost
            vat_amt = sub_total * 0.08
            grand_total = sub_total + vat_amt

            summary_df = pd.DataFrame({
                "Hạng mục": ["Total amount", "Shipment Cost", "Sub-Total", "VAT (8%)", "Grand Total"],
                "Giá trị (VND)": [format_vnd(total_amt), format_vnd(ship_cost), format_vnd(sub_total), format_vnd(vat_amt), format_vnd(grand_total)]
            })
            st.table(summary_df)

            col_bot1, col_bot2 = st.columns(2)
            with col_bot1:
                if st.button("🗑️ Xoá hết hàng", use_container_width=True):
                    st.session_state.cart = []; st.rerun()
            with col_bot2:
                if st.button("💾 Lưu Báo Giá", use_container_width=True, type="primary"):
                    st.success("✅ Đã lưu thành công!")

    # --- 4. ORDER MANAGEMENT ---
    elif st.session_state.current_tab == "Order Management":
        sub_tab = st.radio("Menu:", ["Quotation", "Offers_Tracking", "SP_Report"], horizontal=True)
        
        if sub_tab == "Quotation":
            st.dataframe(df_h_stored, use_container_width=True)
            target = st.selectbox("Chọn Offer No để sửa:", [""] + list(df_h_stored['Offer_No'].unique()))
            
            if target:
                if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button("📝 Edit", use_container_width=True): st.session_state.edit_mode = True
                with c_btn2:
                    if st.button("✅ Confirm", use_container_width=True, type="primary"): st.info("Confirming...")

                # Hiển thị bảng chi tiết để sửa
                details = df_d_stored[df_d_stored['Offer_No'] == target].copy()
                details['Xoá'] = False
                # Ép kiểu số
                for col in ['Qty', 'Unit_Price', 'Discount_Percent']:
                    details[col] = pd.to_numeric(details[col], errors='coerce').fillna(0)
                
                details['Amount'] = details['Unit_Price'] * details['Qty'] * (1 - details['Discount_Percent']/100)
                
                # Sắp xếp cột: Xoá nằm bên trái Amount
                cols = ['Part_Number', 'Part_Name', 'Qty', 'Unit', 'Unit_Price', 'VAT_Rate', 'Discount_Percent', 'Xoá', 'Amount']
                
                edited_details = st.data_editor(
                    details[cols], use_container_width=True, hide_index=True,
                    disabled=not st.session_state.edit_mode,
                    column_config={
                        "Amount": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
                        "Unit_Price": st.column_config.NumberColumn(format="%,.0f"),
                        "Xoá": st.column_config.CheckboxColumn()
                    }
                )

                # NEW TOTAL SUMMARY (Cho trang Edit)
                st.write("### 📊 New Total Summary")
                new_total_amt = edited_details['Amount'].sum()
                # Lấy ship cost từ header cũ
                old_h = df_h_stored[df_h_stored['Offer_No'] == target].iloc[0]
                old_ship = float(old_h.get('Shipment_Cost', 0))
                
                new_sub = new_total_amt + old_ship
                new_vat = new_sub * 0.08
                new_grand = new_sub + new_vat

                new_summary = pd.DataFrame({
                    "Hạng mục": ["Total amount", "Shipment Cost", "Sub-Total", "VAT (8%)", "Grand Total"],
                    "Giá trị (VND)": [format_vnd(new_total_amt), format_vnd(old_ship), format_vnd(new_sub), format_vnd(new_vat), format_vnd(new_grand)]
                })
                st.table(new_summary)

if __name__ == "__main__":
    main()
