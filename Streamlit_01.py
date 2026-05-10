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
        
        # Chuẩn hóa Offer_No
        for df in [df_h_stored, df_d_stored]:
            if df is not None and 'Offer_No' in df.columns:
                df['Offer_No'] = df['Offer_No'].astype(str).str.strip()
        return [df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored]
    except Exception as e:
        st.error(f"❌ Lỗi kết nối dữ liệu: {e}")
        return [None] * 7

def update_sheet(worksheet_name, dataframe):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=dataframe)

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    
    data_list = load_all_data()
    if data_list[0] is None: return
    df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored = data_list

    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'menu_action' not in st.session_state: st.session_state.menu_action = "Tạo báo giá"
    if 'ship_cost' not in st.session_state: st.session_state.ship_cost = 0.0
    if 'edit_mode_header' not in st.session_state: st.session_state.edit_mode_header = None

    # --- ĐIỀU HƯỚNG ---
    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ Tạo báo giá mới", use_container_width=True):
            st.session_state.menu_action = "Tạo báo giá"; st.session_state.edit_mode_header = None
            st.session_state.cart = []; st.session_state.ship_cost = 0.0; st.rerun()
    with c2:
        if st.button("📋 Order Management", use_container_width=True):
            st.session_state.menu_action = "Order Management"; st.rerun()

    if st.session_state.menu_action == "Tạo báo giá":
        edit_h = st.session_state.edit_mode_header
        
        # --- HEADER INFO ---
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

        # --- ADD TO CART (Xử lý lỗi dữ liệu triệt để) ---
        search_pn = st.text_input("🔍 Nhập Part Number (ví dụ: 4008610195; 123):")
        if st.button("🛒 Thêm vào giỏ hàng", type="primary"):
            if search_pn:
                codes = [clean_code(c) for c in search_pn.split(';') if c.strip()]
                df_sp['CLEAN_PN'] = df_sp['Part number'].apply(clean_code)
                for code in codes:
                    match = df_sp[df_sp['CLEAN_PN'] == code]
                    if not match.empty:
                        item = match.iloc[0]
                        # Chuyển đổi giá về số, nếu lỗi (như #ERROR!) thì để là 0
                        raw_price = pd.to_numeric(item.get('Giá bán', 0), errors='coerce')
                        price = float(raw_price) if pd.notnull(raw_price) else 0.0
                        
                        st.session_state.cart.append({
                            "Offer_No": str(off_no).strip(),
                            "Part Number": str(item['Part number']), 
                            "Part Name": str(item['Part name']),
                            "Qty": 1.0, "Unit": str(item['Unit']), "VAT": 8.0,
                            "Unit Price": price, "%Dist": 0.0, "Xoá": False
                        })
                    else: st.warning(f"⚠️ Không thấy mã: {code}")
                st.rerun()

        # --- DISPLAY CART ---
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            # Ép kiểu số cho toàn bảng giỏ hàng trước khi tính Amount
            for col in ['Qty', 'Unit Price', '%Dist', 'VAT']:
                df_cart[col] = pd.to_numeric(df_cart[col], errors='coerce').fillna(0.0)
            
            df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)

            edited_df = st.data_editor(
                df_cart, use_container_width=True, hide_index=True,
                column_config={
                    "Xoá": st.column_config.CheckboxColumn(),
                    "Unit Price": st.column_config.NumberColumn(format="%,.0f"),
                    "Amount": st.column_config.NumberColumn(format="%,.0f")
                }
            )
            
            if not edited_df.equals(df_cart):
                st.session_state.cart = edited_df[~edited_df['Xoá']].drop(columns=['Amount']).to_dict('records')
                st.rerun()

            # --- SUMMARY ---
            st.subheader("📊 Tổng kết báo giá:")
            ship_val = st.number_input("🚚 Phí vận chuyển (VND):", value=float(st.session_state.ship_cost), step=1000.0)
            st.session_state.ship_cost = ship_val
            
            total_goods = edited_df['Amount'].sum()
            vat_amt = (total_goods + ship_val) * 0.08
            grand_total = total_goods + ship_val + vat_amt

            summary_df = pd.DataFrame({
                "Hạng mục": ["Tiền hàng", "Phí vận chuyển", "VAT (8%)", "TỔNG CỘNG"],
                "Giá trị (VND)": [f"{total_goods:,.0f}", f"{ship_val:,.0f}", f"{vat_amt:,.0f}", f"{grand_total:,.0f}"]
            })
            st.table(summary_df)

            # --- SAVE ---
            if st.button("💾 Lưu Báo Giá", use_container_width=True, type="primary"):
                try:
                    curr_off = str(off_no).strip()
                    # 1. Header
                    new_h = pd.DataFrame([{
                        "Offer_No": curr_off, "Offer_Date": off_date.strftime("%Y-%m-%d"),
                        "Customer_Name": cust_name, "Cust_No": c_no, "VAT_Code": mst_val,
                        "Address": row_mst.get('Địa chỉ', '-'), "Contact_Person": contact_person,
                        "Machine_No": machine_no, "Staff": staff_name, 
                        "Total_Amount": total_goods, "Shipment_Cost": ship_val, 
                        "VAT_Amount": vat_amt, "Grand_Total": grand_total
                    }])
                    df_h_final = pd.concat([df_h_stored[df_h_stored['Offer_No'] != curr_off], new_h], ignore_index=True)
                    
                    # 2. Details
                    details = edited_df[~edited_df['Xoá']].copy()
                    details['Offer_No'] = curr_off
                    details = details.rename(columns={"Part Number":"Part_Number","Part Name":"Part_Name","VAT":"VAT_Rate","Unit Price":"Unit_Price","%Dist":"Discount_Percent"})
                    df_d_final = pd.concat([df_d_stored[df_d_stored['Offer_No'] != curr_off], details[['Offer_No','Part_Number','Part_Name','Qty','Unit','Unit_Price','VAT_Rate','Discount_Percent','Amount']]], ignore_index=True)

                    update_sheet("Offer_Header", df_h_final)
                    update_sheet("Offer_Details", df_d_final)
                    st.success(f"✅ Đã lưu {curr_off}!"); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi lưu: {e}")

    elif st.session_state.menu_action == "Order Management":
        st.subheader("📋 Danh sách báo giá")
        st.dataframe(df_h_stored, use_container_width=True)
        sel = st.selectbox("Sửa Offer:", [""] + list(df_h_stored['Offer_No'].unique()))
        if sel and st.button("📝 Sửa"):
            h = df_h_stored[df_h_stored['Offer_No'] == sel].iloc[0]
            st.session_state.edit_mode_header = h.to_dict()
            st.session_state.ship_cost = float(h.get('Shipment_Cost', 0))
            d = df_d_stored[df_d_stored['Offer_No'] == sel].copy()
            d = d.rename(columns={"Part_Number":"Part Number","Part_Name":"Part Name","VAT_Rate":"VAT","Unit_Price":"Unit Price","Discount_Percent":"%Dist"})
            # Ép kiểu số khi tải dữ liệu sửa
            for col in ["Qty", "Unit Price", "VAT", "%Dist"]:
                d[col] = pd.to_numeric(d[col], errors='coerce').fillna(0.0)
            st.session_state.cart = d.to_dict('records')
            st.session_state.menu_action = "Tạo báo giá"; st.rerun()

if __name__ == "__main__":
    main()
