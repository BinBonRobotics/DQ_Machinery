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
        
        # Chuẩn hóa Offer_No thành String ngay từ đầu
        for df in [df_h_stored, df_d_stored, df_tracking]:
            if df is not None and 'Offer_No' in df.columns:
                df['Offer_No'] = df['Offer_No'].astype(str).str.strip()
        return [df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored, df_tracking]
    except Exception as e:
        st.error(f"❌ Lỗi load data: {e}")
        return [None] * 8

def update_sheet(worksheet_name, dataframe):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=dataframe)

def main():
    st.set_page_config(page_title="D&Q Machinery Management", layout="wide")
    
    data_list = load_all_data()
    if data_list[0] is None: return
    df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored, df_tracking = data_list

    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'menu_action' not in st.session_state: st.session_state.menu_action = "Tạo báo giá"
    if 'ship_cost' not in st.session_state: st.session_state.ship_cost = 0
    if 'edit_mode_header' not in st.session_state: st.session_state.edit_mode_header = None

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Hệ thống")
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear(); st.rerun()
        st.divider()
        if st.button("➕ Tạo báo giá / Quản lý", use_container_width=True):
            st.session_state.menu_action = "Tạo báo giá"; st.rerun()

    # --- NAVIGATION ---
    c_nav1, c_nav2 = st.columns(2)
    with c_nav1:
        if st.button("➕ Tạo báo giá mới", use_container_width=True):
            st.session_state.menu_action = "Tạo báo giá"; st.session_state.edit_mode_header = None
            st.session_state.cart = []; st.session_state.ship_cost = 0; st.rerun()
    with c_nav2:
        if st.button("📋 Order Management", use_container_width=True):
            st.session_state.menu_action = "Order Management"; st.rerun()
    st.divider()

    if st.session_state.menu_action == "Tạo báo giá":
        edit_h = st.session_state.edit_mode_header
        
        # Header Fields
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

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            list_macs = df_mac[df_mac['Customers'] == cust_name]['Machine No.'].dropna().unique().tolist()
            idx_mac = list_macs.index(edit_h['Machine_No']) if edit_h and edit_h['Machine_No'] in list_macs else 0
            machine_no = st.selectbox("🤖 Machine Number:", options=list_macs if list_macs else ["N/A"], index=idx_mac)
        with r2c2:
            list_staff = df_staff['Name'].dropna().unique().tolist()
            idx_staff = list_staff.index(edit_h['Staff']) if edit_h and edit_h['Staff'] in list_staff else 0
            staff_name = st.selectbox("✍️ Người lập báo giá:", options=list_staff, index=idx_staff)

        r3c1, r3c2 = st.columns(2)
        with r3c1:
            off_no = st.text_input("🆔 Offer No:", value=str(edit_h['Offer_No']) if edit_h else f"OFF-{datetime.now().strftime('%Y%m%d%H%M')}")
        with r3c2:
            off_date = st.date_input("📅 Offer Date:", value=pd.to_datetime(edit_h['Offer_Date']) if edit_h else datetime.now())

        st.divider()

        # Add Part
        search_pn = st.text_input("🔍 Nhập Part Number (ví dụ: 123; 456):")
        if st.button("🛒 Thêm vào giỏ hàng", type="primary"):
            if search_pn:
                codes = [clean_code(c) for c in search_pn.split(';') if c.strip()]
                df_sp['CLEAN_PN'] = df_sp['Part number'].apply(clean_code)
                current_off_id = str(off_no).strip()
                for code in codes:
                    match = df_sp[df_sp['CLEAN_PN'] == code]
                    if not match.empty:
                        item = match.iloc[0]
                        st.session_state.cart.append({
                            "Offer_No": current_off_id,
                            "Part Number": item['Part number'], "Part Name": item['Part name'],
                            "Qty": 1.0, "Unit": item['Unit'], "VAT": 8.0,
                            "Unit Price": float(item.get('Giá bán', 0)), "%Dist": 0.0, "Xoá": False
                        })
                    else: st.error(f"Không thấy mã: {code}")
                st.rerun()

        # Cart Table
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            # Ép kiểu dữ liệu ngay lập tức để đồng nhất
            df_cart['Offer_No'] = str(off_no).strip()
            df_cart['Qty'] = df_cart['Qty'].astype(float)
            df_cart['Unit Price'] = df_cart['Unit Price'].astype(float)
            df_cart['%Dist'] = df_cart['%Dist'].astype(float)
            df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)
            
            # Sắp xếp cột
            disp_cols = ["Offer_No", "Part Number", "Part Name", "Qty", "Unit", "Unit Price", "VAT", "%Dist", "Amount", "Xoá"]
            df_cart = df_cart[disp_cols]

            edited_df = st.data_editor(
                df_cart, use_container_width=True, hide_index=True,
                column_config={
                    "Xoá": st.column_config.CheckboxColumn(),
                    "Offer_No": st.column_config.TextColumn(disabled=True),
                    "Unit Price": st.column_config.NumberColumn(format="%,.0f"),
                    "Amount": st.column_config.NumberColumn(format="%,.0f")
                }
            )
            
            if not edited_df.equals(df_cart):
                st.session_state.cart = edited_df[~edited_df['Xoá']].drop(columns=['Amount']).to_dict('records')
                st.rerun()

            # Summary Table
            st.subheader("📊 Tổng kết báo giá:")
            ship_val = st.number_input("🚚 Shipment Cost (VND):", value=float(st.session_state.ship_cost), step=1000.0)
            st.session_state.ship_cost = ship_val
            
            total_goods = edited_df['Amount'].sum()
            vat_amt = (total_goods + ship_val) * 0.08
            grand_total = total_goods + ship_val + vat_amt

            summary_df = pd.DataFrame({
                "Hạng mục": ["Tiền hàng", "Phí vận chuyển", "VAT (8%)", "TỔNG CỘNG"],
                "Giá trị (VND)": [f"{total_goods:,.0f}", f"{ship_val:,.0f}", f"{vat_amt:,.0f}", f"{grand_total:,.0f}"]
            })
            st.table(summary_df)

            # SAVE LOGIC
            if st.button("💾 Lưu Báo Giá", use_container_width=True, type="primary"):
                try:
                    current_off = str(off_no).strip()
                    
                    # 1. Update Header
                    new_h = pd.DataFrame([{
                        "Offer_No": current_off, "Offer_Date": off_date.strftime("%Y-%m-%d"),
                        "Customer_Name": cust_name, "Cust_No": c_no, "VAT_Code": mst_val,
                        "Address": row_mst.get('Địa chỉ', '-'), "Contact_Person": contact_person,
                        "Machine_No": machine_no, "Staff": staff_name, 
                        "Total_Amount": float(total_goods), "Shipment_Cost": float(ship_val), 
                        "VAT_Amount": float(vat_amt), "Grand_Total": float(grand_total)
                    }])
                    df_h_final = pd.concat([df_h_stored[df_h_stored['Offer_No'] != current_off], new_h], ignore_index=True)
                    
                    # 2. Update Details (Đồng bộ kiểu dữ liệu tuyệt đối)
                    details = edited_df[~edited_df['Xoá']].copy()
                    details['Offer_No'] = current_off
                    details = details.rename(columns={
                        "Part Number":"Part_Number", "Part Name":"Part_Name",
                        "VAT":"VAT_Rate", "Unit Price":"Unit_Price", "%Dist":"Discount_Percent"
                    })
                    
                    # Lọc lấy các cột cần thiết và ép kiểu
                    final_cols = ['Offer_No','Part_Number','Part_Name','Qty','Unit','Unit_Price','VAT_Rate','Discount_Percent','Amount']
                    details = details[final_cols]
                    for col in ['Qty', 'Unit_Price', 'VAT_Rate', 'Discount_Percent', 'Amount']:
                        details[col] = details[col].astype(float)
                    
                    # Concat dữ liệu cũ và mới
                    df_d_final = pd.concat([df_d_stored[df_d_stored['Offer_No'] != current_off], details], ignore_index=True)

                    # 3. Push to Sheets
                    update_sheet("Offer_Header", df_h_final)
                    update_sheet("Offer_Details", df_d_final)
                    
                    st.success(f"✅ Đã lưu báo giá {current_off}!")
                    st.cache_data.clear(); st.rerun()
                except Exception as save_error:
                    st.error(f"❌ Lỗi khi lưu: {save_error}")

    elif st.session_state.menu_action == "Order Management":
        st.subheader("Quản lý báo giá")
        st.dataframe(df_h_stored, use_container_width=True, hide_index=True)
        sel = st.selectbox("Chọn Offer để sửa:", [""] + list(df_h_stored['Offer_No'].unique()))
        if sel and st.button("📝 Bắt đầu sửa"):
            h = df_h_stored[df_h_stored['Offer_No'] == sel].iloc[0]
            st.session_state.edit_mode_header = h.to_dict()
            st.session_state.ship_cost = float(h['Shipment_Cost'])
            d = df_d_stored[df_d_stored['Offer_No'] == sel]
            st.session_state.cart = d.rename(columns={
                "Part_Number":"Part Number","Part_Name":"Part Name","VAT_Rate":"VAT","Unit_Price":"Unit Price","Discount_Percent":"%Dist"
            }).to_dict('records')
            st.session_state.menu_action = "Tạo báo giá"; st.rerun()

if __name__ == "__main__":
    main()
