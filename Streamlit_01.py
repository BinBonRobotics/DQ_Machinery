import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime

# --- CẤU HÌNH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

def clean_code(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).split('.')[0].strip()
    return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

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
        return df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored, df_tracking
    except Exception as e:
        st.error(f"❌ Lỗi kết nối dữ liệu: {e}")
        return [None] * 8

def update_sheet(worksheet_name, dataframe):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=dataframe)

def main():
    st.set_page_config(page_title="D&Q Machinery Management", layout="wide")
    
    # Load data
    data = load_all_data()
    if data[0] is None: return
    df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored, df_tracking = data

    # Session states
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'sub_action' not in st.session_state: st.session_state.sub_action = "create"
    if 'ship_cost' not in st.session_state: st.session_state.ship_cost = 0
    if 'edit_mode_data' not in st.session_state: st.session_state.edit_mode_data = None

    # --- 1. SIDEBAR ---
    st.sidebar.title("⚙️ Cấu hình")
    ty_gia = st.sidebar.number_input("Tỷ giá Euro (VND):", value=31000, step=100)
    if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.sidebar.markdown("---")
    st.sidebar.radio("📂 Danh mục:", ["📄 Báo Giá Phụ Tùng"])

    # --- 2. ĐIỀU HƯỚNG CHÍNH ---
    col_nav1, col_nav2, _ = st.columns([2, 2, 4])
    if col_nav1.button("➕ Tạo Báo Giá", use_container_width=True, type="primary" if st.session_state.sub_action=="create" else "secondary"):
        st.session_state.sub_action = "create"
        st.session_state.edit_mode_data = None
        st.session_state.cart = []
    if col_nav2.button("🔍 Order Management", use_container_width=True, type="primary" if st.session_state.sub_action=="search" else "secondary"):
        st.session_state.sub_action = "search"
    st.divider()

    # --- 3. TRANG TẠO BÁO GIÁ ---
    if st.session_state.sub_action == "create":
        edit_data = st.session_state.edit_mode_data
        
        # 3.1 Dropdown menus & Info
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            cust_list = sorted(df_mst['Customer name'].dropna().unique())
            idx_cust = cust_list.index(edit_data['Customer_Name']) if edit_data and edit_data['Customer_Name'] in cust_list else 0
            cust_name = st.selectbox("🎯 Khách hàng:", options=cust_list, index=idx_cust)
            row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
            c_no = str(row_mst.get('Customer no', row_mst.get('Customer\nno', ''))).split('.')[0]
            mst_val = row_mst.get('Mã số thuế', '-')
            st.info(f"**Cust No:** {c_no} | **MST:** {mst_val}")
        
        with r1c2:
            f_conts = df_con[df_con.iloc[:, 1].astype(str).str.contains(clean_code(c_no))] if df_con is not None else pd.DataFrame()
            list_conts = f_conts.iloc[:, 7].dropna().unique().tolist() if not f_conts.empty else []
            idx_cont = list_conts.index(edit_data['Contact_Person']) if edit_data and edit_data['Contact_Person'] in list_conts else 0
            contact_person = st.selectbox("👤 Contact Person:", options=list_conts if list_conts else ["N/A"], index=idx_cont)
            addr_val = str(row_mst.get('Địa chỉ', '-'))
            st.markdown(f"📍 **Địa chỉ:** {addr_val}")

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        with r2c1:
            f_macs = df_mac[df_mac.iloc[:, 1].astype(str).str.contains(clean_code(c_no))] if df_mac is not None else pd.DataFrame()
            list_macs = f_macs.iloc[:, 14].dropna().unique().tolist() if not f_macs.empty else []
            idx_mac = list_macs.index(edit_data['Machine_No']) if edit_data and edit_data['Machine_No'] in list_macs else 0
            machine_no = st.selectbox("🤖 Machine Number:", options=list_macs if list_macs else ["N/A"], index=idx_mac)
        with r2c2:
            list_staff = df_staff['Name'].dropna().unique().tolist() if 'Name' in df_staff.columns else ["Admin"]
            idx_staff = list_staff.index(edit_data['Staff']) if edit_data and edit_data['Staff'] in list_staff else 0
            staff_name = st.selectbox("✍️ Người lập:", options=list_staff, index=idx_staff)
        with r2c3:
            offer_date = st.date_input("📅 Offer Date:", value=datetime.now())
        with r2c4:
            init_no = edit_data['Offer_No'] if edit_data else f"{offer_date.year}-{offer_date.month:02d}-0001"
            offer_no = st.text_input("🆔 Offer No:", value=init_no)

        st.divider()
        # 3.2 & 3.3 Part Number Search
        input_search = st.text_input("🔍 Nhập Part Number (cách nhau bởi dấu ;):")
        if st.button("🛒 Thêm vào giỏ hàng", type="primary") and input_search:
            codes = [clean_code(c) for c in input_search.split(';') if c.strip()]
            df_sp['CLEAN_PN'] = df_sp['Part number'].apply(clean_code)
            found_any = False
            for code in codes:
                match = df_sp[df_sp['CLEAN_PN'] == code]
                if not match.empty:
                    item = match.iloc[0]
                    st.session_state.cart.append({
                        "Part Number": item['Part number'], "Part Name": item['Part name'],
                        "Qty": 1, "Unit": item['Unit'], "VAT": 8,
                        "Unit Price": float(item.get('Giá bán', 0)), "%Dist": 0.0, "Xoá": False
                    })
                    found_any = True
                else:
                    st.warning(f"❌ Không tìm thấy mã: {code}")
            if found_any: st.rerun()

        # 3.4 Table Danh sách chi tiết
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            df_cart.insert(0, 'No', range(1, len(df_cart) + 1))
            df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)
            
            st.subheader("📋 Chi tiết hàng hóa")
            edited_df = st.data_editor(df_cart, column_config={
                "No": st.column_config.NumberColumn(disabled=True),
                "Part Number": st.column_config.TextColumn(disabled=True),
                "Part Name": st.column_config.TextColumn(disabled=True),
                "Qty": st.column_config.NumberColumn(min_value=1),
                "Unit": st.column_config.TextColumn(disabled=True),
                "VAT": st.column_config.NumberColumn(format="%d", disabled=True),
                "Unit Price": st.column_config.NumberColumn(format="%,d", disabled=True),
                "%Dist": st.column_config.NumberColumn(format="%d%%"),
                "Amount": st.column_config.NumberColumn(format="%,d", disabled=True),
                "Xoá": st.column_config.CheckboxColumn()
            }, use_container_width=True, hide_index=True)

            if not edited_df.equals(df_cart):
                st.session_state.cart = edited_df[~edited_df['Xoá']].drop(columns=['No', 'Amount']).to_dict('records')
                st.rerun()

            # 3.6 Shipment Cost
            st.divider()
            ship_val = st.number_input("🚚 Nhập Shipment Cost (VND):", value=int(st.session_state.ship_cost), step=1000, format="%d")
            st.session_state.ship_cost = ship_val

            # 3.5 & 3.7 Tổng kết báo giá
            total_amt = edited_df['Amount'].sum()
            sub_total = total_amt + ship_val
            vat_calc = sub_total * 0.08
            grand_total = sub_total + vat_calc

            st.markdown("### 📊 Tổng kết giá trị báo giá")
            summary_data = pd.DataFrame([
                {"Nội dung": "Total Amount", "Giá trị (VND)": total_amt},
                {"Nội dung": "Shipment Cost", "Giá trị (VND)": ship_val},
                {"Nội dung": "Sub-Total", "Giá trị (VND)": sub_total},
                {"Nội dung": "VAT (8%)", "Giá trị (VND)": vat_calc},
                {"Nội dung": "GRAND TOTAL", "Giá trị (VND)": grand_total}
            ])
            st.dataframe(summary_data, column_config={
                "Nội dung": st.column_config.TextColumn(disabled=True),
                "Giá trị (VND)": st.column_config.NumberColumn(format="%,d", disabled=True)
            }, use_container_width=True, hide_index=True)

            # 3.8 & 3.9 Buttons
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🗑️ Xoá hết hàng", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()
            with col_btn2:
                if st.button("💾 Lưu Báo Giá", use_container_width=True, type="primary"):
                    h_data = {
                        "Offer_No": offer_no, "Offer_Date": offer_date.strftime("%Y-%m-%d"),
                        "Customer_Name": cust_name, "Cust_No": c_no, "VAT_Code": mst_val,
                        "Address": addr_val, "Contact_Person": contact_person, "Machine_No": machine_no,
                        "Staff": staff_name, "Total_Amount": total_amt, "Shipment_Cost": ship_val,
                        "VAT_Amount": vat_calc, "Grand_Total": grand_total
                    }
                    d_df = edited_df.drop(columns=['No', 'Xoá'])
                    d_df.columns = ["Part_Number", "Part_Name", "Qty", "Unit", "VAT_Rate", "Unit_Price", "Discount_Percent", "Amount"]
                    d_df.insert(0, "Offer_No", offer_no)

                    df_h_new = pd.concat([df_h_stored[df_h_stored['Offer_No'].astype(str) != str(offer_no)], pd.DataFrame([h_data])], ignore_index=True)
                    df_d_new = pd.concat([df_d_stored[df_d_stored['Offer_No'].astype(str) != str(offer_no)], d_df], ignore_index=True)
                    
                    update_sheet("Offer_Header", df_h_new)
                    update_sheet("Offer_Details", df_d_new)
                    st.success("✅ Đã lưu báo giá thành công!")
                    st.cache_data.clear()

    # --- 4. ORDER MANAGEMENT ---
    elif st.session_state.sub_action == "search":
        tab_q, tab_t, tab_r = st.tabs(["📄 Quotation", "🚚 Offers_Tracking", "📊 SP_Report"])
        
        with tab_q:
            st.subheader("Danh sách báo giá")
            st.dataframe(df_h_stored, column_config={
                "Total_Amount": st.column_config.NumberColumn(format="%,d"),
                "Shipment_Cost": st.column_config.NumberColumn(format="%,d"),
                "Grand_Total": st.column_config.NumberColumn(format="%,d")
            }, use_container_width=True, hide_index=True)
            
            c_sel, c_btn1, c_btn2, _ = st.columns([3, 1.5, 2, 3])
            with c_sel:
                sel_id = st.selectbox("Chọn Offer No:", options=[""] + list(df_h_stored['Offer_No'].unique()))
            
            if sel_id:
                h_row = df_h_stored[df_h_stored['Offer_No'].astype(str) == str(sel_id)].iloc[0]
                d_rows = df_d_stored[df_d_stored['Offer_No'].astype(str) == str(sel_id)]
                
                with c_btn1:
                    if st.button("📝 Sửa báo giá", use_container_width=True):
                        st.session_state.edit_mode_data = h_row.to_dict()
                        st.session_state.ship_cost = h_row['Shipment_Cost']
                        st.session_state.cart = d_rows.rename(columns={
                            "Part_Number": "Part Number", "Part_Name": "Part Name", "VAT_Rate": "VAT", "Unit_Price": "Unit Price", "Discount_Percent": "%Dist"
                        }).to_dict('records')
                        st.session_state.sub_action = "create"; st.rerun()
                
                with c_btn2:
                    if st.button("✅ Xác nhận đơn hàng", use_container_width=True, type="primary"):
                        if str(sel_id) in df_tracking['Offer_No'].astype(str).values:
                            st.warning("⚠️ Đơn này đã nằm trong danh sách Tracking.")
                        else:
                            new_track = pd.DataFrame([{
                                "Offer_No": h_row['Offer_No'],
                                "Confirm_Date": datetime.now().strftime("%Y-%m-%d"),
                                "Customer_Name": h_row['Customer_Name'],
                                "Grand_Total": h_row['Grand_Total'],
                                "Status": "Confirmed",
                                "Deposite_Status": False, "Deposite_Date": "", "ETA": "", "PO_Number": "", "Tracking_Note": ""
                            }])
                            df_tr_new = pd.concat([df_tracking, new_track], ignore_index=True)
                            update_sheet("Offer_Tracking", df_tr_new)
                            st.success(f"🚀 Đã chuyển {sel_id} sang tab Tracking!")
                            st.cache_data.clear(); st.rerun()
                
                st.dataframe(d_rows, column_config={
                    "Unit_Price": st.column_config.NumberColumn(format="%,d"),
                    "Amount": st.column_config.NumberColumn(format="%,d")
                }, use_container_width=True, hide_index=True)

        with tab_t:
            st.subheader("Theo dõi tiến độ (Offers_Tracking)")
            if not df_tracking.empty:
                edited_tracking = st.data_editor(df_tracking, column_config={
                    "Grand_Total": st.column_config.NumberColumn(format="%,d", disabled=True),
                    "Status": st.column_config.SelectboxColumn(options=["Confirmed", "Ordered", "Shipping", "Delivered", "Completed"]),
                    "Deposite_Status": st.column_config.CheckboxColumn(),
                    "Deposite_Date": st.column_config.DateColumn(),
                    "ETA": st.column_config.DateColumn()
                }, use_container_width=True, hide_index=True)
                if st.button("💾 Cập nhật Tracking"):
                    update_sheet("Offer_Tracking", edited_tracking)
                    st.success("✅ Cập nhật thành công!")
                    st.cache_data.clear(); st.rerun()
            else:
                st.info("Chưa có đơn hàng nào được xác nhận.")

        with tab_r:
            st.info("📊 SP_Report: Tính năng đang phát triển...")

if __name__ == "__main__":
    main()
