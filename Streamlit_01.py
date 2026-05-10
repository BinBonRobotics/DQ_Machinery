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
    try: return f"{int(round(float(value))):,}"
    except: return "0"

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
        
        # Đồng bộ Offer_No và xử lý cột Status nếu chưa có trong DataFrame
        for df in [df_h_stored, df_d_stored]:
            if df is not None and 'Offer_No' in df.columns:
                df['Offer_No'] = df['Offer_No'].astype(str).str.strip()
        
        if df_h_stored is not None and 'Status' not in df_h_stored.columns:
            df_h_stored['Status'] = "Draft" # Tạo cột tạm nếu Sheets chưa có
            
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

    # --- NAVIGATION ---
    c_nav1, c_nav2 = st.columns(2)
    with c_nav1:
        if st.button("➕ Tạo báo giá", use_container_width=True, type="primary" if st.session_state.current_tab == "Tạo báo giá" else "secondary"):
            st.session_state.current_tab = "Tạo báo giá"; st.rerun()
    with c_nav2:
        if st.button("📋 Order Management", use_container_width=True, type="primary" if st.session_state.current_tab == "Order Management" else "secondary"):
            st.session_state.current_tab = "Order Management"; st.rerun()

    st.write("---")

    # --- TAB TẠO BÁO GIÁ (Giữ nguyên logic cũ nhưng thêm Status mặc định) ---
    if st.session_state.current_tab == "Tạo báo giá":
        st.info("Phần này đang được giữ nguyên code theo yêu cầu của bạn.")

    # --- TAB ORDER MANAGEMENT (FIXED EDIT + STATUS COLUMN) ---
    elif st.session_state.current_tab == "Order Management":
        sub_tab = st.radio("Chế độ:", ["Quotation", "Offers_Tracking", "SP_Report"], horizontal=True)
        
        if sub_tab == "Quotation":
            # Hiển thị bảng Header bao gồm cột Status
            st.dataframe(df_h_stored, use_container_width=True, hide_index=True)
            
            target_id = st.selectbox("Chọn Offer No để xử lý:", [""] + list(df_h_stored['Offer_No'].unique()), key="sel_target")
            
            if target_id:
                if f"edit_{target_id}" not in st.session_state:
                    st.session_state[f"edit_{target_id}"] = False
                
                col_e, col_c = st.columns(2)
                with col_e:
                    if st.button("📝 Edit", use_container_width=True):
                        st.session_state[f"edit_{target_id}"] = True
                        det = df_d_stored[df_d_stored['Offer_No'] == target_id].copy()
                        det['Xoá'] = False
                        for col in ['Qty', 'Unit_Price', 'VAT_Rate', 'Discount_Percent']:
                            det[col] = pd.to_numeric(det[col], errors='coerce').fillna(0)
                        st.session_state[f"data_{target_id}"] = det

                with col_c:
                    st.button("✅ Confirm", use_container_width=True)

                if st.session_state[f"edit_{target_id}"]:
                    st.divider()
                    st.subheader(f"🛠️ Chỉnh sửa báo giá: {target_id}")
                    
                    # Thêm lựa chọn thay đổi trạng thái (Status) ngay trong khi Edit
                    current_status = df_h_stored[df_h_stored['Offer_No'] == target_id]['Status'].iloc[0]
                    new_status = st.selectbox("📌 Trạng thái báo giá:", ["Draft", "Sent", "Confirmed", "Cancelled"], 
                                             index=["Draft", "Sent", "Confirmed", "Cancelled"].index(current_status) if current_status in ["Draft", "Sent", "Confirmed", "Cancelled"] else 0)

                    # 1. Ô thêm hàng mới
                    c_s1, c_s2 = st.columns([3, 1])
                    with c_s1:
                        new_p_input = st.text_input("🔍 Nhập Part Number để THÊM:", key=f"in_{target_id}")
                    with c_s2:
                        st.write("##")
                        if st.button("➕ Thêm hàng", use_container_width=True):
                            m = df_sp[df_sp['Part number'].apply(clean_code) == clean_code(new_p_input)]
                            if not m.empty:
                                itm = m.iloc[0]
                                new_row = pd.DataFrame([{
                                    "Offer_No": target_id, "Part_Number": str(itm['Part number']),
                                    "Part_Name": str(itm['Part name']), "Qty": 1.0, "Unit": str(itm['Unit']),
                                    "Unit_Price": float(pd.to_numeric(itm['Giá bán'], errors='coerce') or 0),
                                    "VAT_Rate": 8, "Discount_Percent": 0.0, "Xoá": False
                                }])
                                st.session_state[f"data_{target_id}"] = pd.concat([st.session_state[f"data_{target_id}"], new_row], ignore_index=True)
                                st.rerun()
                            else: st.error("Mã không tồn tại!")

                    # 2. Bảng Editor
                    curr_data = st.session_state[f"data_{target_id}"]
                    curr_data['Amount'] = curr_data['Unit_Price'] * curr_data['Qty'] * (1 - curr_data['Discount_Percent']/100)
                    
                    display_cols = ['Part_Number', 'Part_Name', 'Qty', 'Unit', 'Unit_Price', 'VAT_Rate', 'Discount_Percent', 'Xoá', 'Amount']
                    
                    edited_result = st.data_editor(
                        curr_data[display_cols],
                        use_container_width=True, hide_index=True,
                        column_config={
                            "Amount": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
                            "Unit_Price": st.column_config.NumberColumn(format="%,.0f"),
                            "Xoá": st.column_config.CheckboxColumn()
                        },
                        key=f"editor_{target_id}"
                    )

                    if not edited_result.equals(curr_data[display_cols]):
                        st.session_state[f"data_{target_id}"] = edited_result[~edited_result['Xoá']].copy()
                        st.rerun()

                    # 3. Tổng kết chi tiết
                    st.write("### 📊 Tổng kết báo giá")
                    h_row = df_h_stored[df_h_stored['Offer_No'] == target_id].iloc[0]
                    
                    t_amt = edited_result['Amount'].sum()
                    s_cost = float(h_row.get('Shipment_Cost', 0))
                    s_total = t_amt + s_cost
                    v_amt = s_total * 0.08
                    g_total = s_total + v_amt

                    summary_tbl = pd.DataFrame({
                        "Hạng mục": ["Total amount", "Shipment Cost", "Sub-Total", "VAT (8%)", "Grand Total"],
                        "Giá trị (VND)": [format_vnd(t_amt), format_vnd(s_cost), format_vnd(s_total), format_vnd(v_amt), format_vnd(g_total)]
                    })
                    st.table(summary_tbl)

                    # 4. NÚT UPDATE
                    if st.button("💾 UPDATE & SAVE TO SYSTEM", use_container_width=True, type="primary"):
                        try:
                            final_d = st.session_state[f"data_{target_id}"].copy()
                            final_d = final_d.drop(columns=['Xoá', 'Amount'], errors='ignore')
                            
                            # CẬP NHẬT HEADER (Bao gồm cả cột STATUS)
                            df_h_stored.loc[df_h_stored['Offer_No'] == target_id, ['Total_Amount', 'VAT_Amount', 'Grand_Total', 'Status']] = [t_amt, v_amt, g_total, new_status]
                            
                            df_d_final = pd.concat([df_d_stored[df_d_stored['Offer_No'] != str(target_id)], final_d], ignore_index=True)
                            
                            update_sheet("Offer_Header", df_h_stored)
                            update_sheet("Offer_Details", df_d_final)
                            
                            st.success(f"✅ Đã cập nhật Offer {target_id} thành công!")
                            st.session_state[f"edit_{target_id}"] = False
                            st.cache_data.clear(); st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi lưu dữ liệu: {e}")

if __name__ == "__main__":
    main()
