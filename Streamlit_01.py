import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime

# --- CẤU HÌNH KẾT NỐI ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

def clean_code(val):
    if pd.isna(val) or val == "": return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(val).split('.')[0]).strip().upper()

@st.cache_data(ttl=5)
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
        return [df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored, df_tracking]
    except Exception as e:
        st.error(f"❌ Lỗi kết nối dữ Holmes: {e}")
        return [None] * 8

def update_sheet(worksheet_name, dataframe):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=dataframe)

def main():
    st.set_page_config(page_title="D&Q Machinery Management", layout="wide")
    
    data_list = load_all_data()
    if data_list[0] is None: return
    df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored, df_tracking = data_list

    # Khởi tạo Session State
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'menu_action' not in st.session_state: st.session_state.menu_action = "Tạo báo giá"
    if 'ship_cost' not in st.session_state: st.session_state.ship_cost = 0
    if 'edit_mode_header' not in st.session_state: st.session_state.edit_mode_header = None

    # --- 1. SIDEBAR BÊN TAY TRÁI ---
    with st.sidebar:
        st.header("⚙️ Hệ thống")
        st.number_input("Tỷ giá Euro (VND):", value=31000, step=100)
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        st.subheader("📂 Báo Giá Phụ Tùng")
        if st.button("➕ Tạo báo giá / Quản lý", use_container_width=True):
            st.session_state.menu_action = "Tạo báo giá"
            st.rerun()
        
        st.subheader("📊 Master Data")
        if st.button("🗄️ Dữ liệu gốc", use_container_width=True):
            st.session_state.menu_action = "Master Data"
            st.rerun()

    # --- ĐIỀU HƯỚNG TRANG CHÍNH ---
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("➕ Tạo báo giá", use_container_width=True):
            st.session_state.menu_action = "Tạo báo giá"
            st.session_state.edit_mode_header = None
            st.session_state.cart = []
            st.rerun()
    with col_nav2:
        if st.button("📋 Order Management", use_container_width=True):
            st.session_state.menu_action = "Order Management"
            st.rerun()
    st.divider()

    # --- 3. TRANG TẠO BÁO GIÁ ---
    if st.session_state.menu_action == "Tạo báo giá":
        edit_h = st.session_state.edit_mode_header
        
        # 3.1 Thông tin khách hàng
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            cust_list = sorted(df_mst['Customer name'].dropna().unique())
            idx_cust = cust_list.index(edit_h['Customer_Name']) if edit_h and edit_h['Customer_Name'] in cust_list else 0
            cust_name = st.selectbox("🎯 Khách hàng:", options=cust_list, index=idx_cust)
            row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
            c_no = str(row_mst.get('Customer no', '')).split('.')[0]
            mst_val = row_mst.get('Mã số thuế', '-')
            st.info(f"**Cust No:** {c_no} | **MST:** {mst_val}")
        
        with r1c2:
            list_conts = df_con[df_con['Customer name'] == cust_name]['Customer contact'].dropna().unique().tolist()
            idx_cont = list_conts.index(edit_h['Contact_Person']) if edit_h and edit_h['Contact_Person'] in list_conts else 0
            contact_person = st.selectbox("👤 Contact Person:", options=list_conts if list_conts else ["N/A"], index=idx_cont)
            st.markdown(f"📍 **Địa chỉ:** {row_mst.get('Địa chỉ', '-')}")

        # --- HÀNG MACHINE NUMBER (NẰM TRÊN) ---
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            # Lọc chính xác Machine Number theo Khách hàng
            list_macs = df_mac[df_mac['Customers'] == cust_name]['Machine No.'].dropna().unique().tolist()
            idx_mac = 0
            if edit_h and edit_h['Machine_No'] in list_macs:
                idx_mac = list_macs.index(edit_h['Machine_No'])
            machine_no = st.selectbox("🤖 Machine Number:", options=list_macs if list_macs else ["No Machine Found"], index=idx_mac)
        with r2c2:
            list_staff = df_staff['Name'].dropna().unique().tolist()
            idx_staff = list_staff.index(edit_h['Staff']) if edit_h and edit_h['Staff'] in list_staff else 0
            staff_name = st.selectbox("✍️ Người lập báo giá:", options=list_staff, index=idx_staff)

        # --- HÀNG OFFER NO & DATE (NẰM DƯỚI MACHINE NUMBER) ---
        r3c1, r3c2 = st.columns(2)
        with r3c1:
            off_no = st.text_input("🆔 Offer No:", value=edit_h['Offer_No'] if edit_h else f"OFF-{datetime.now().strftime('%Y%m%d%H%M')}")
        with r3c2:
            off_date = st.date_input("📅 Offer Date:", value=pd.to_datetime(edit_h['Offer_Date']) if edit_h else datetime.now())

        st.divider()
        # 3.2 & 3.3 Tìm Part Number
        search_pn = st.text_input("🔍 Nhập Part Number (ngăn cách bởi dấu ;):")
        if st.button("🛒 Thêm vào giỏ hàng", type="primary"):
            if search_pn:
                codes = [clean_code(c) for c in search_pn.split(';') if c.strip()]
                df_sp['CLEAN_PN'] = df_sp['Part number'].apply(clean_code)
                for code in codes:
                    match = df_sp[df_sp['CLEAN_PN'] == code]
                    if not match.empty:
                        item = match.iloc[0]
                        st.session_state.cart.append({
                            "Part Number": item['Part number'], "Part Name": item['Part name'],
                            "Qty": 1, "Unit": item['Unit'], "VAT": 8,
                            "Unit Price": float(item.get('Giá bán', 0)), "%Dist": 0.0, "Xoá": False
                        })
                    else: st.error(f"Không tìm thấy: {code}")
                st.rerun()

        # 3.4 Bảng chi tiết
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            df_cart.insert(0, 'No', range(1, len(df_cart) + 1))
            df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)
            
            edited_df = st.data_editor(df_cart, column_config={
                "No": st.column_config.NumberColumn(disabled=True),
                "Part Number": st.column_config.TextColumn(disabled=True),
                "Part Name": st.column_config.TextColumn(disabled=True),
                "Unit": st.column_config.TextColumn(disabled=True),
                "VAT": st.column_config.NumberColumn(format="%d", disabled=True),
                "Unit Price": st.column_config.NumberColumn(format="%,d", disabled=True),
                "Amount": st.column_config.NumberColumn(format="%,d", disabled=True),
                "Qty": st.column_config.NumberColumn(min_value=1),
                "%Dist": st.column_config.NumberColumn(min_value=0, max_value=100),
                "Xoá": st.column_config.CheckboxColumn()
            }, use_container_width=True, hide_index=True)

            if not edited_df.equals(df_cart):
                st.session_state.cart = edited_df[~edited_df['Xoá']].drop(columns=['No', 'Amount']).to_dict('records')
                st.rerun()

            ship_val = st.number_input("🚚 Shipment Cost (VND):", value=int(st.session_state.ship_cost), step=1000)
            st.session_state.ship_cost = ship_val

            # 3.5 Tổng kết
            total_amt = edited_df['Amount'].sum()
            sub_total = total_amt + ship_val
            vat_amt = sub_total * 0.08
            grand_total = sub_total + vat_amt

            st.markdown("### 📊 Tổng kết báo giá")
            summary_data = [
                {"Nội dung": "Total amount", "Giá trị (VND)": total_amt},
                {"Nội dung": "Shipment Cost", "Giá trị (VND)": ship_val},
                {"Nội dung": "Sub-Total", "Giá trị (VND)": sub_total},
                {"Nội dung": "VAT (8%)", "Giá trị (VND)": vat_amt},
                {"Nội dung": "Grand Total", "Giá trị (VND)": grand_total}
            ]
            st.table(pd.DataFrame(summary_data)) # Dùng table để thẳng hàng tuyệt đối

            c_act1, c_act2 = st.columns(2)
            with c_act1:
                if st.button("🗑️ Xoá hết hàng", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()
            with c_act2:
                if st.button("💾 Lưu Báo Giá", use_container_width=True, type="primary"):
                    # Logic ghi đè an toàn
                    df_h_new = df_h_stored[df_h_stored['Offer_No'].astype(str) != str(off_no)].copy()
                    h_row = {
                        "Offer_No": str(off_no), "Offer_Date": off_date.strftime("%Y-%m-%d"),
                        "Customer_Name": cust_name, "Cust_No": c_no, "VAT_Code": mst_val,
                        "Address": row_mst.get('Địa chỉ', '-'), "Contact_Person": contact_person,
                        "Machine_No": machine_no, "Staff": staff_name, "Total_Amount": total_amt,
                        "Shipment_Cost": ship_val, "VAT_Amount": vat_amt, "Grand_Total": grand_total
                    }
                    df_h_new = pd.concat([df_h_new, pd.DataFrame([h_row])], ignore_index=True)
                    
                    df_d_new = df_d_stored[df_d_stored['Offer_No'].astype(str) != str(off_no)].copy()
                    details = edited_df[~edited_df['Xoá']].copy()
                    details['Offer_No'] = str(off_no)
                    details = details.rename(columns={"Part Number": "Part_Number", "Part Name": "Part_Name", "VAT": "VAT_Rate", "Unit Price": "Unit_Price", "%Dist": "Discount_Percent"})
                    df_d_new = pd.concat([df_d_new, details[['Offer_No', 'Part_Number', 'Part_Name', 'Qty', 'Unit', 'Unit_Price', 'VAT_Rate', 'Discount_Percent', 'Amount']]], ignore_index=True)

                    update_sheet("Offer_Header", df_h_new)
                    update_sheet("Offer_Details", df_d_new)
                    st.success(f"✅ Đã lưu báo giá {off_no}!")
                    st.cache_data.clear()

    # --- 4. ORDER MANAGEMENT ---
    elif st.session_state.menu_action == "Order Management":
        tab1, tab2, tab3 = st.tabs(["📄 Quotation", "🚚 Offers_Tracking", "📊 SP_Report"])
        
        with tab1:
            st.subheader("Danh sách báo giá")
            st.dataframe(df_h_stored, hide_index=True, use_container_width=True)
            
            sel_off = st.selectbox("Chọn Offer No:", options=[""] + list(df_h_stored['Offer_No'].unique()))
            if sel_off:
                c1, c2 = st.columns(2)
                h_row = df_h_stored[df_h_stored['Offer_No'].astype(str) == str(sel_off)].iloc[0]
                with c1:
                    if st.button("📝 Sửa báo giá này", use_container_width=True):
                        st.session_state.edit_mode_header = h_row.to_dict()
                        st.session_state.ship_cost = h_row['Shipment_Cost']
                        d_rows = df_d_stored[df_d_stored['Offer_No'].astype(str) == str(sel_off)]
                        st.session_state.cart = d_rows.rename(columns={"Part_Number": "Part Number", "Part_Name": "Part Name", "VAT_Rate": "VAT", "Unit_Price": "Unit Price", "Discount_Percent": "%Dist"}).to_dict('records')
                        st.session_state.menu_action = "Tạo báo giá"
                        st.rerun()
                with c2:
                    if st.button("✅ Xác nhận báo giá", use_container_width=True, type="primary"):
                        if str(sel_off) not in df_tracking['Offer_No'].astype(str).values:
                            new_tr = pd.DataFrame([{"Offer_No": str(sel_off), "Confirm_Date": datetime.now().strftime("%Y-%m-%d"), "Customer_Name": h_row['Customer_Name'], "Grand_Total": h_row['Grand_Total'], "Status": "Confirmed"}])
                            update_sheet("Offer_Tracking", pd.concat([df_tracking, new_tr], ignore_index=True))
                            st.success("Đã chuyển sang Tracking!")
                            st.cache_data.clear()

        with tab2:
            st.subheader("🚚 Theo dõi đơn hàng")
            # Hiển thị dữ liệu Tracking thực tế từ Google Sheet
            if not df_tracking.empty:
                st.dataframe(df_tracking, use_container_width=True, hide_index=True)
            else:
                st.info("Chưa có dữ liệu tracking.")

    elif st.session_state.menu_action == "Master Data":
        st.title("🗄️ Master Data")
        st.write("Dữ liệu gốc từ Google Sheets")
        st.dataframe(df_sp.head(100))

if __name__ == "__main__":
    main()
