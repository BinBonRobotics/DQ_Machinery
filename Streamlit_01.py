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
    return f"{int(value):,}"

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
        df_tracking = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Tracking")
        
        for df in [df_h_stored, df_d_stored, df_tracking]:
            if df is not None and 'Offer_No' in df.columns:
                df['Offer_No'] = df['Offer_No'].astype(str).str.strip()
        return [df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored, df_tracking]
    except Exception as e:
        st.error(f"Lỗi kết nối: {e}")
        return [None] * 8

def update_sheet(worksheet_name, dataframe):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=dataframe)

# --- 2. GIAO DIỆN CHÍNH ---
def main():
    st.set_page_config(page_title="D&Q Machinery Management", layout="wide")
    
    # 2.1 Sidebar cố định
    with st.sidebar:
        st.header("Báo Giá Phụ Tùng")
        st.write("---")
        st.number_input("Tỷ giá (EUR/VND):", value=28000, step=100)
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    data_list = load_all_data()
    if data_list[0] is None: return
    df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored, df_tracking = data_list

    # Khởi tạo session state
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'ship_cost' not in st.session_state: st.session_state.ship_cost = 0
    if 'current_tab' not in st.session_state: st.session_state.current_tab = "Tạo báo giá"

    # 2.2 Điều hướng chính
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("➕ Tạo báo giá", use_container_width=True, type="primary" if st.session_state.current_tab == "Tạo báo giá" else "secondary"):
            st.session_state.current_tab = "Tạo báo giá"; st.rerun()
    with col_nav2:
        if st.button("📋 Order Management", use_container_width=True, type="primary" if st.session_state.current_tab == "Order Management" else "secondary"):
            st.session_state.current_tab = "Order Management"; st.rerun()

    st.write("---")

    # --- 3. TRANG TẠO BÁO GIÁ ---
    if st.session_state.current_tab == "Tạo báo giá":
        # 3.1 Dropdowns Thông tin khách hàng
        c1, c2 = st.columns(2)
        with c1:
            cust_name = st.selectbox("🎯 Khách hàng:", options=sorted(df_mst['Customer name'].dropna().unique()))
            row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
            st.info(f"**Cust No:** {str(row_mst.get('Customer no', '')).split('.')[0]} | **MST:** {row_mst.get('Mã số thuế', '-')}")
            st.markdown(f"📍 **Địa chỉ:** {row_mst.get('Địa chỉ', '-')}")
        with c2:
            contact_person = st.selectbox("👤 Contact Person:", options=df_con[df_con['Customer name'] == cust_name]['Customer contact'].unique())
            machine_no = st.selectbox("🤖 Machine Number:", options=df_mac[df_mac['Customers'] == cust_name]['Machine No.'].unique())
            staff_name = st.selectbox("✍️ Người lập báo giá:", options=df_staff['Name'].unique())

        c3, c4 = st.columns(2)
        with c3:
            off_no = st.text_input("🆔 Offer No:", value=f"OFF-{datetime.now().strftime('%Y%m%d%H%M')}")
        with c4:
            off_date = st.date_input("📅 Offer Date:", value=datetime.now())

        st.write("---")

        # 3.2 Tìm kiếm Part Number
        search_pn = st.text_input("🔍 Nhập Part Number:")
        if st.button("🛒 Thêm vào giỏ hàng", use_container_width=False):
            if search_pn:
                match = df_sp[df_sp['Part number'].apply(clean_code) == clean_code(search_pn)]
                if not match.empty:
                    item = match.iloc[0]
                    st.session_state.cart.append({
                        "No": len(st.session_state.cart) + 1,
                        "Part Number": item['Part number'],
                        "Part Name": item['Part name'],
                        "Qty": 1.0,
                        "Unit": item['Unit'],
                        "VAT": 8,
                        "Unit Price": float(pd.to_numeric(item['Giá bán'], errors='coerce') or 0),
                        "%Dist": 0.0,
                        "Xoá": False
                    })
                    st.rerun()
                else:
                    st.error(f"❌ Không tìm thấy Part Number: {search_pn}")

        # 3.4 Bảng chi tiết giỏ hàng
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)
            
            # Cấu hình Disable/Enable cho từng cột
            edited_df = st.data_editor(
                df_cart, use_container_width=True, hide_index=True,
                column_config={
                    "No": st.column_config.NumberColumn(disabled=True),
                    "Part Number": st.column_config.TextColumn(disabled=True),
                    "Part Name": st.column_config.TextColumn(disabled=True),
                    "Qty": st.column_config.NumberColumn(min_value=1, step=1),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(disabled=True),
                    "Unit Price": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
                    "%Dist": st.column_config.NumberColumn(min_value=0, max_value=100),
                    "Amount": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
                    "Xoá": st.column_config.CheckboxColumn()
                }
            )
            
            # Xử lý cập nhật giỏ hàng khi có thay đổi (Qty, Dist, Delete)
            if not edited_df.equals(df_cart):
                st.session_state.cart = edited_df[~edited_df['Xoá']].to_dict('records')
                st.rerun()

            # 3.5 & 3.6 & 3.7 Tổng kết báo giá
            st.write("### 📊 Tổng kết báo giá")
            ship_input = st.text_input("🚚 Shipment Cost (VND):", value=format_vnd(st.session_state.ship_cost))
            # Clean format input
            st.session_state.ship_cost = int(re.sub(r'[^0-9]', '', ship_input))

            total_amount = edited_df['Amount'].sum()
            shipment_cost = st.session_state.ship_cost
            sub_total = total_amount + shipment_cost
            vat_val = sub_total * 0.08
            grand_total = sub_total + vat_val

            summary_data = {
                "Hạng mục": ["Total amount", "Shipment Cost", "Sub-Total", "VAT (8%)", "Grand Total"],
                "Giá trị (VND)": [format_vnd(total_amount), format_vnd(shipment_cost), format_vnd(sub_total), format_vnd(vat_val), format_vnd(grand_total)]
            }
            st.table(pd.DataFrame(summary_data)) # Trải dài theo yêu cầu

            # 3.8 & 3.9 Nút điều khiển
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🗑️ Xoá hết hàng", use_container_width=True):
                    st.session_state.cart = []; st.rerun()
            with col_btn2:
                if st.button("💾 Lưu Báo Giá", use_container_width=True, type="primary"):
                    # Logic lưu vào Sheets...
                    st.success("✅ Đã lưu báo giá thành công!")

    # --- 4. ORDER MANAGEMENT ---
    elif st.session_state.current_tab == "Order Management":
        sub_tab = st.radio("Chế độ:", ["Quotation", "Offers_Tracking", "SP_Report"], horizontal=True)
        
        if sub_tab == "Quotation":
            st.subheader("Quotation Management")
            st.dataframe(df_h_stored, use_container_width=True)
            
            target_off = st.selectbox("Chọn Offer No để xử lý:", [""] + list(df_h_stored['Offer_No'].unique()))
            
            if target_off:
                col_edit, col_confirm = st.columns(2)
                
                # Trạng thái khóa/mở bảng edit
                if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False
                
                with col_edit:
                    if st.button("📝 Edit", use_container_width=True):
                        st.session_state.edit_mode = True
                with col_confirm:
                    if st.button("✅ Confirm", use_container_width=True, type="primary"):
                        # Chuyển dữ liệu sang Offer_Tracking
                        st.info(f"Đang di chuyển {target_off} sang Tracking...")
                
                # Hiển thị bảng chi tiết để sửa
                details = df_d_stored[df_d_stored['Offer_No'] == target_off].copy()
                
                # Tính toán lại tổng tiền hiển thị ngay tại chỗ
                st.write(f"Chi tiết Offer: {target_off}")
                
                # Cột Xóa nằm bên trái Amount
                cols_order = ['Part_Number','Part_Name','Qty','Unit','Unit_Price','VAT_Rate','Discount_Percent','Xoá','Amount']
                details['Xoá'] = False
                details['Amount'] = details['Unit_Price'] * details['Qty'] * (1 - details['Discount_Percent']/100)
                
                # Chế độ Edit: Grey out nếu chưa nhấn nút Edit
                is_disabled = not st.session_state.edit_mode
                
                edited_details = st.data_editor(
                    details[cols_order],
                    use_container_width=True,
                    hide_index=True,
                    disabled=is_disabled,
                    column_config={
                        "Unit_Price": st.column_config.NumberColumn(format="%,.0f"),
                        "Amount": st.column_config.NumberColumn(format="%,.0f", disabled=True),
                        "Part_Number": st.column_config.TextColumn(disabled=True),
                        "Part_Name": st.column_config.TextColumn(disabled=True),
                    }
                )
                
                # Hiển thị Tổng kết mới cho mục Sửa
                st.write("#### 📊 New Total Summary")
                new_total = edited_details['Amount'].sum()
                st.write(f"**Total Amount mới:** {format_vnd(new_total)} VND")

        elif sub_tab == "Offers_Tracking":
            st.info("🚀 Offers Tracking: Coming Soon")
        else:
            st.info("🚀 SP Report: Coming Soon")

if __name__ == "__main__":
    main()
