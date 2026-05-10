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
        
        # Đồng nhất kiểu dữ liệu String cho Offer_No
        for df in [df_h_stored, df_d_stored, df_tracking]:
            if df is not None and 'Offer_No' in df.columns:
                df['Offer_No'] = df['Offer_No'].astype(str).str.strip()
                
        return [df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored, df_tracking]
    except Exception as e:
        st.error(f"❌ Lỗi kết nối dữ liệu: {e}")
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

    # --- ĐIỀU HƯỚNG ---
    c_nav1, c_nav2 = st.columns(2)
    with c_nav1:
        if st.button("➕ Tạo báo giá mới", use_container_width=True):
            st.session_state.menu_action = "Tạo báo giá"
            st.session_state.edit_mode_header = None
            st.session_state.cart = []; st.session_state.ship_cost = 0; st.rerun()
    with c_nav2:
        if st.button("📋 Order Management", use_container_width=True):
            st.session_state.menu_action = "Order Management"; st.rerun()
    st.divider()

    if st.session_state.menu_action == "Tạo báo giá":
        edit_h = st.session_state.edit_mode_header
        
        # Giao diện Header
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            cust_list = sorted(df_mst['Customer name'].dropna().unique())
            idx_cust = cust_list.index(edit_h['Customer_Name']) if edit_h and edit_h['Customer_Name'] in cust_list else 0
            cust_name = st.selectbox("🎯 Khách hàng:", options=cust_list, index=idx_cust)
            row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
            c_no = str(row_mst.get('Customer no', '')).split('.')[0]
            mst_val = row_mst.get('Mã số thuế', '-')
        
        with r1c2:
            off_no = st.text_input("🆔 Offer No:", value=str(edit_h['Offer_No']) if edit_h else f"OFF-{datetime.now().strftime('%Y%m%d%H%M')}")
            off_date = st.date_input("📅 Offer Date:", value=pd.to_datetime(edit_h['Offer_Date']) if edit_h else datetime.now())

        st.divider()

        # --- THÊM PART VÀO GIỎ HÀNG ---
        search_pn = st.text_input("🔍 Nhập Part Number (ví dụ: 123; 456):")
        if st.button("🛒 Thêm vào giỏ hàng", type="primary"):
            if search_pn:
                codes = [clean_code(c) for c in search_pn.split(';') if c.strip()]
                df_sp['CLEAN_PN'] = df_sp['Part number'].apply(clean_code)
                
                # Lấy mã Offer hiện tại để tự động điền
                current_off_id = str(off_no).strip()

                for code in codes:
                    match = df_sp[df_sp['CLEAN_PN'] == code]
                    if not match.empty:
                        item = match.iloc[0]
                        st.session_state.cart.append({
                            "Offer_No": current_off_id,  # <--- TỰ ĐỘNG ĐIỀN THEO Ý BẠN
                            "Part Number": item['Part number'],
                            "Part Name": item['Part name'],
                            "Qty": 1,
                            "Unit": item['Unit'],
                            "VAT": 8,
                            "Unit Price": float(item.get('Giá bán', 0)),
                            "%Dist": 0.0,
                            "Xoá": False
                        })
                    else: st.error(f"Không thấy mã: {code}")
                st.rerun()

        # --- HIỂN THỊ GIỎ HÀNG ---
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            
            # Đảm bảo cột Offer_No luôn xuất hiện ở đầu bảng để người dùng thấy
            cols = ["Offer_No"] + [c for c in df_cart.columns if c != "Offer_No"]
            df_cart = df_cart[cols]
            
            df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)
            
            edited_df = st.data_editor(
                df_cart, 
                use_container_width=True, 
                hide_index=True, 
                column_config={"Xoá": st.column_config.CheckboxColumn(), "Offer_No": st.column_config.TextColumn(disabled=True)}
            )
            
            if not edited_df.equals(df_cart):
                st.session_state.cart = edited_df[~edited_df['Xoá']].drop(columns=['Amount']).to_dict('records')
                st.rerun()

            if st.button("💾 Lưu Báo Giá", use_container_width=True, type="primary"):
                current_off = str(off_no).strip()
                
                # 1. Xử lý Header
                df_h_final = pd.concat([df_h_stored[df_h_stored['Offer_No'] != current_off], pd.DataFrame([{
                    "Offer_No": current_off, "Offer_Date": off_date.strftime("%Y-%m-%d"),
                    "Customer_Name": cust_name, "Cust_No": c_no, "VAT_Code": mst_val,
                    "Total_Amount": edited_df['Amount'].sum(), "Grand_Total": edited_df['Amount'].sum() * 1.08
                }])], ignore_index=True)
                
                # 2. Xử lý Details (Đảm bảo Ghi đè Offer_No một lần nữa trước khi lưu)
                details = edited_df[~edited_df['Xoá']].copy()
                details['Offer_No'] = current_off # Chốt chặn cuối cùng để không bao giờ bị trống
                
                details = details.rename(columns={
                    "Part Number":"Part_Number", 
                    "Part Name":"Part_Name", 
                    "VAT":"VAT_Rate", 
                    "Unit Price":"Unit_Price", 
                    "%Dist":"Discount_Percent"
                })
                
                # Lọc bỏ các cột thừa trước khi concat vào DB
                cols_to_save = ['Offer_No','Part_Number','Part_Name','Qty','Unit','Unit_Price','VAT_Rate','Discount_Percent','Amount']
                df_d_final = pd.concat([df_d_stored[df_d_stored['Offer_No'] != current_off], details[cols_to_save]], ignore_index=True)

                # 3. Update lên Cloud
                update_sheet("Offer_Header", df_h_final)
                update_sheet("Offer_Details", df_d_final)
                st.success(f"✅ Đã lưu thành công Offer: {current_off}")
                st.cache_data.clear(); st.rerun()

    elif st.session_state.menu_action == "Order Management":
        st.subheader("Danh sách báo giá")
        st.dataframe(df_h_stored, use_container_width=True)
        sel = st.selectbox("Chọn Offer để sửa:", [""] + list(df_h_stored['Offer_No'].unique()))
        if sel and st.button("📝 Bắt đầu sửa"):
            h = df_h_stored[df_h_stored['Offer_No'] == sel].iloc[0]
            st.session_state.edit_mode_header = h.to_dict()
            d = df_d_stored[df_d_stored['Offer_No'] == sel]
            st.session_state.cart = d.rename(columns={
                "Part_Number":"Part Number","Part_Name":"Part Name","VAT_Rate":"VAT","Unit_Price":"Unit Price","Discount_Percent":"%Dist"
            }).to_dict('records')
            st.session_state.menu_action = "Tạo báo giá"; st.rerun()

if __name__ == "__main__":
    main()
