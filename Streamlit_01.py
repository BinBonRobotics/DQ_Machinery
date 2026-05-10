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
        
        # Đồng bộ kiểu dữ liệu Offer_No là String
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
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Hệ thống")
        st.radio("Menu chính:", ["Báo giá phụ tùng", "Báo giá dịch vụ"])
        st.write("---")
        st.number_input("Tỷ giá (EUR/VND):", value=28000, step=100)
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear(); st.rerun()

    data_list = load_all_data()
    if data_list[0] is None: return
    df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored = data_list

    if 'current_tab' not in st.session_state: st.session_state.current_tab = "Tạo báo giá"
    if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False
    if 'temp_edit_details' not in st.session_state: st.session_state.temp_edit_details = None

    # --- NAVIGATION ---
    c_nav1, c_nav2 = st.columns(2)
    with c_nav1:
        if st.button("➕ Tạo báo giá", use_container_width=True, type="primary" if st.session_state.current_tab == "Tạo báo giá" else "secondary"):
            st.session_state.current_tab = "Tạo báo giá"; st.rerun()
    with c_nav2:
        if st.button("📋 Order Management", use_container_width=True, type="primary" if st.session_state.current_tab == "Order Management" else "secondary"):
            st.session_state.current_tab = "Order Management"; st.session_state.edit_mode = False; st.rerun()

    st.write("---")

    # --- TRANG TẠO BÁO GIÁ (Giữ nguyên) ---
    if st.session_state.current_tab == "Tạo báo giá":
        st.info("Tab Tạo báo giá đang được giữ nguyên code.")

    # --- ORDER MANAGEMENT (FIXED EDIT) ---
    elif st.session_state.current_tab == "Order Management":
        sub_tab = st.radio("Menu:", ["Quotation", "Offers_Tracking", "SP_Report"], horizontal=True)
        
        if sub_tab == "Quotation":
            st.dataframe(df_h_stored, use_container_width=True, hide_index=True)
            target = st.selectbox("Chọn Offer No để xử lý:", [""] + list(df_h_stored['Offer_No'].unique()))
            
            if target:
                c_edit, c_confirm = st.columns(2)
                with c_edit:
                    if st.button("📝 Edit", use_container_width=True, type="primary" if st.session_state.edit_mode else "secondary"):
                        st.session_state.edit_mode = True
                        # Load dữ liệu gốc từ Sheets vào biến tạm duy nhất một lần
                        det = df_d_stored[df_d_stored['Offer_No'] == target].copy()
                        det['Xoá'] = False
                        # Ép kiểu số để tính toán không lỗi
                        for col in ['Qty', 'Unit_Price', 'VAT_Rate', 'Discount_Percent']:
                            det[col] = pd.to_numeric(det[col], errors='coerce').fillna(0)
                        st.session_state.temp_edit_details = det

                with c_confirm:
                    st.button("✅ Confirm", use_container_width=True)

                if st.session_state.edit_mode and st.session_state.temp_edit_details is not None:
                    st.divider()
                    st.info(f"🛠️ Chế độ chỉnh sửa: {target}")
                    
                    # 5.1 Tìm và Thêm hàng mới
                    col_s1, col_s2 = st.columns([3, 1])
                    with col_s1:
                        new_pn = st.text_input("🔍 Nhập Part Number để THÊM vào báo giá này:", key="pn_edit_input")
                    with col_s2:
                        st.write("##")
                        if st.button("➕ Thêm hàng", use_container_width=True):
                            if new_pn:
                                match = df_sp[df_sp['Part number'].apply(clean_code) == clean_code(new_pn)]
                                if not match.empty:
                                    item = match.iloc[0]
                                    new_row = pd.DataFrame([{
                                        "Offer_No": target, "Part_Number": str(item['Part number']),
                                        "Part_Name": str(item['Part name']), "Qty": 1.0, "Unit": str(item['Unit']),
                                        "Unit_Price": float(pd.to_numeric(item['Giá bán'], errors='coerce') or 0),
                                        "VAT_Rate": 8, "Discount_Percent": 0.0, "Xoá": False
                                    }])
                                    # Cập nhật trực tiếp vào session_state để không bị mất hàng cũ
                                    st.session_state.temp_edit_details = pd.concat([st.session_state.temp_edit_details, new_row], ignore_index=True)
                                    st.rerun()
                                else:
                                    st.error("Mã không tồn tại trong danh mục SP!")

                    # 5.2 Hiển thị bảng Editor
                    curr_df = st.session_state.temp_edit_details
                    curr_df['Amount'] = curr_df['Unit_Price'] * curr_df['Qty'] * (1 - curr_df['Discount_Percent']/100)
                    
                    cols = ['Part_Number', 'Part_Name', 'Qty', 'Unit', 'Unit_Price', 'VAT_Rate', 'Discount_Percent', 'Xoá', 'Amount']
                    
                    edited_db = st.data_editor(
                        curr_df[cols],
                        use_container_width=True, hide_index=True,
                        column_config={
                            "Amount": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
                            "Unit_Price": st.column_config.NumberColumn(format="%,.0f"),
                            "Xoá": st.column_config.CheckboxColumn()
                        },
                        key="main_edit_editor"
                    )

                    # Đồng bộ lại dữ liệu khi người dùng sửa Qty/Price/Xoá
                    if not edited_db.equals(curr_df[cols]):
                        # Loại bỏ những dòng bị tích "Xoá"
                        st.session_state.temp_edit_details = edited_db[~edited_db['Xoá']].copy()
                        st.rerun()

                    # 5.3 Bảng Tổng kết chi tiết (Luôn lấy từ bảng đang hiển thị)
                    st.write("### 📊 Tổng kết báo giá sau chỉnh sửa")
                    header_row = df_h_stored[df_h_stored['Offer_No'] == target].iloc[0]
                    
                    total_amt = edited_db['Amount'].sum()
                    ship_cost = float(pd.to_numeric(header_row.get('Shipment_Cost', 0), errors='coerce') or 0)
                    sub_total = total_amt + ship_cost
                    vat_amt = sub_total * 0.08
                    grand_total = sub_total + vat_amt

                    summary_df = pd.DataFrame({
                        "Hạng mục": ["Total amount", "Shipment Cost", "Sub-Total", "VAT (8%)", "Grand Total"],
                        "Giá trị (VND)": [format_vnd(total_amt), format_vnd(ship_cost), format_vnd(sub_total), format_vnd(vat_amt), format_vnd(grand_total)]
                    })
                    st.table(summary_df)

                    # 5.4 Nút Update (Lưu đè lên Sheets)
                    if st.button("💾 UPDATE (Cập nhật dữ liệu vào hệ thống)", use_container_width=True, type="primary"):
                        try:
                            # Cập nhật Header
                            df_h_stored.loc[df_h_stored['Offer_No'] == target, ['Total_Amount', 'VAT_Amount', 'Grand_Total']] = [total_amt, vat_amt, grand_total]
                            
                            # Cập nhật Details: Lấy dữ liệu mới nhất từ session
                            final_details = st.session_state.temp_edit_details.drop(columns=['Xoá', 'Amount'], errors='ignore')
                            
                            # Gộp dữ liệu: Giữ lại các Offer khác + Dữ liệu mới của Offer này
                            df_d_updated = pd.concat([df_d_stored[df_d_stored['Offer_No'] != target], final_details], ignore_index=True)
                            
                            # Lưu vào Sheets
                            update_sheet("Offer_Header", df_h_stored)
                            update_sheet("Offer_Details", df_d_updated)
                            
                            st.success(f"✅ Đã cập nhật thành công Offer {target}!")
                            st.session_state.edit_mode = False
                            st.session_state.temp_edit_details = None
                            st.cache_data.clear(); st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi lưu: {e}")

if __name__ == "__main__":
    main()
