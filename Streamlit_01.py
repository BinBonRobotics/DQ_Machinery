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
    
    # --- 2. SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Hệ thống")
        st.radio("Menu chính:", ["Báo giá phụ tùng", "Báo giá dịch vụ"]) # Yêu cầu 1
        st.write("---")
        st.number_input("Tỷ giá (EUR/VND):", value=28000, step=100)
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear(); st.rerun()

    data_list = load_all_data()
    if data_list[0] is None: 
        st.error("Không thể tải dữ liệu"); return
    df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored = data_list

    if 'current_tab' not in st.session_state: st.session_state.current_tab = "Tạo báo giá"
    if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False
    if 'temp_edit_details' not in st.session_state: st.session_state.temp_edit_details = None

    # --- 3. ĐIỀU HƯỚNG ---
    c_nav1, c_nav2 = st.columns(2)
    with c_nav1:
        if st.button("➕ Tạo báo giá", use_container_width=True, type="primary" if st.session_state.current_tab == "Tạo báo giá" else "secondary"):
            st.session_state.current_tab = "Tạo báo giá"; st.rerun()
    with c_nav2:
        if st.button("📋 Order Management", use_container_width=True, type="primary" if st.session_state.current_tab == "Order Management" else "secondary"):
            st.session_state.current_tab = "Order Management"; st.rerun()

    st.write("---")

    # --- 4. TRANG TẠO BÁO GIÁ (Giữ nguyên theo yêu cầu 2) ---
    if st.session_state.current_tab == "Tạo báo giá":
        st.warning("Tab này đang được giữ nguyên code cũ.")
        # [Code cũ của bạn ở đây...]

    # --- 5. ORDER MANAGEMENT (TẬP TRUNG SỬA MỤC EDIT - Yêu cầu 3) ---
    elif st.session_state.current_tab == "Order Management":
        sub_tab = st.radio("Menu:", ["Quotation", "Offers_Tracking", "SP_Report"], horizontal=True)
        
        if sub_tab == "Quotation":
            st.subheader("Danh sách báo giá")
            st.dataframe(df_h_stored, use_container_width=True)
            
            target = st.selectbox("Chọn Offer No để xử lý:", [""] + list(df_h_stored['Offer_No'].unique()))
            
            if target:
                c_edit, c_confirm = st.columns(2)
                with c_edit:
                    if st.button("📝 Edit", use_container_width=True, type="primary" if st.session_state.edit_mode else "secondary"):
                        st.session_state.edit_mode = True
                        # Load dữ liệu vào session để chỉnh sửa không bị mất khi rerun
                        det = df_d_stored[df_d_stored['Offer_No'] == target].copy()
                        det['Xoá'] = False
                        st.session_state.temp_edit_details = det
                with c_confirm:
                    st.button("✅ Confirm", use_container_width=True)

                if st.session_state.edit_mode and st.session_state.temp_edit_details is not None:
                    st.write("---")
                    st.info(f"🛠️ Đang trong chế độ chỉnh sửa: {target}")
                    
                    # 5.1 Tìm part number và Thêm vào giỏ hàng (Chỉ hiện khi Edit)
                    col_s1, col_s2 = st.columns([3, 1])
                    with col_s1:
                        new_pn = st.text_input("🔍 Tìm Part Number để thêm vào Offer này:", key="edit_search")
                    with col_s2:
                        st.write("##") # Căn chỉnh nút
                        if st.button("➕ Thêm vào giỏ", use_container_width=True):
                            match = df_sp[df_sp['Part number'].apply(clean_code) == clean_code(new_pn)]
                            if not match.empty:
                                item = match.iloc[0]
                                new_row = pd.DataFrame([{
                                    "Offer_No": target, "Part_Number": item['Part number'],
                                    "Part_Name": item['Part name'], "Qty": 1.0, "Unit": item['Unit'],
                                    "Unit_Price": float(pd.to_numeric(item['Giá bán'], errors='coerce') or 0),
                                    "VAT_Rate": 8, "Discount_Percent": 0.0, "Xoá": False
                                }])
                                st.session_state.temp_edit_details = pd.concat([st.session_state.temp_edit_details, new_row], ignore_index=True)
                                st.rerun()
                            else:
                                st.error("Không tìm thấy mã!")

                    # 5.2 Bảng chỉnh sửa (Có cột Xoá)
                    st.session_state.temp_edit_details['Amount'] = st.session_state.temp_edit_details['Unit_Price'] * st.session_state.temp_edit_details['Qty'] * (1 - st.session_state.temp_edit_details['Discount_Percent']/100)
                    
                    # Thứ tự cột: ... Discount, Xoá, Amount
                    cols = ['Part_Number', 'Part_Name', 'Qty', 'Unit', 'Unit_Price', 'VAT_Rate', 'Discount_Percent', 'Xoá', 'Amount']
                    
                    edited_db = st.data_editor(
                        st.session_state.temp_edit_details[cols],
                        use_container_width=True, hide_index=True,
                        column_config={
                            "Amount": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
                            "Unit_Price": st.column_config.NumberColumn(format="%,.0f"),
                            "Xoá": st.column_config.CheckboxColumn()
                        },
                        key="editor_edit_mode"
                    )

                    # Cập nhật session khi người dùng sửa trên table
                    if not edited_db.equals(st.session_state.temp_edit_details[cols]):
                        # Xử lý xoá dòng ngay lập tức nếu checkbox Xoá được tích
                        st.session_state.temp_edit_details = edited_db[~edited_db['Xoá']].copy()
                        st.rerun()

                    # 5.3 Bảng Tổng kết chi tiết (Đủ 5 dòng như yêu cầu)
                    st.write("### 📊 Tổng kết báo giá mới")
                    header_data = df_h_stored[df_h_stored['Offer_No'] == target].iloc[0]
                    
                    total_amt = edited_db['Amount'].sum()
                    ship_cost = float(header_data.get('Shipment_Cost', 0))
                    sub_total = total_amt + ship_cost
                    vat_amt = sub_total * 0.08
                    grand_total = sub_total + vat_amt

                    summary_df = pd.DataFrame({
                        "Hạng mục": ["Total amount", "Shipment Cost", "Sub-Total", "VAT (8%)", "Grand Total"],
                        "Giá trị (VND)": [format_vnd(total_amt), format_vnd(ship_cost), format_vnd(sub_total), format_vnd(vat_amt), format_vnd(grand_total)]
                    })
                    st.table(summary_df)

                    # 5.4 Nút Update để lưu lại
                    if st.button("💾 Update (Cập nhật báo giá)", use_container_width=True, type="primary"):
                        # Cập nhật Header
                        df_h_stored.loc[df_h_stored['Offer_No'] == target, ['Total_Amount', 'VAT_Amount', 'Grand_Total']] = [total_amt, vat_amt, grand_total]
                        # Cập nhật Details (Xoá cái cũ của Offer này và ghi đè cái mới)
                        new_details_all = pd.concat([df_d_stored[df_d_stored['Offer_No'] != target], st.session_state.temp_edit_details.drop(columns=['Xoá', 'Amount'], errors='ignore')], ignore_index=True)
                        
                        update_sheet("Offer_Header", df_h_stored)
                        update_sheet("Offer_Details", new_details_all)
                        
                        st.success(f"✅ Đã cập nhật Offer {target} thành công!")
                        st.session_state.edit_mode = False
                        st.cache_data.clear(); st.rerun()

if __name__ == "__main__":
    main()
