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
        
        for df in [df_h_stored, df_d_stored]:
            if df is not None and 'Offer_No' in df.columns:
                df['Offer_No'] = df['Offer_No'].astype(str).str.strip()
        
        if df_h_stored is not None and 'Status' not in df_h_stored.columns:
            df_h_stored['Status'] = "Draft"
            
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

    if 'cart' not in st.session_state: st.session_state.cart = []
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

    # --- 4. TAB TẠO BÁO GIÁ (ĐÃ MỞ LẠI & FIX LỖI) ---
    if st.session_state.current_tab == "Tạo báo giá":
        c1, c2 = st.columns(2)
        with c1:
            cust_list = sorted(df_mst['Customer name'].dropna().unique())
            cust_name = st.selectbox("🎯 Khách hàng:", options=cust_list)
            
            row_mst = df_mst[df_mst['Customer name'] == cust_name]
            if not row_mst.empty:
                info = row_mst.iloc[0]
                st.info(f"**Cust No:** {str(info.get('Customer no', '')).split('.')[0]} | **MST:** {info.get('Mã số thuế', '-')}")
            
        with c2:
            # Fix lỗi không thấy Machine/Contact
            con_list = df_con[df_con['Customer name'] == cust_name]['Customer contact'].dropna().unique()
            contact_person = st.selectbox("👤 Contact Person:", options=list(con_list) if len(con_list)>0 else ["N/A"])
            
            mac_list = df_mac[df_mac['Customers'] == cust_name]['Machine No.'].dropna().unique()
            machine_no = st.selectbox("🤖 Machine Number:", options=list(mac_list) if len(mac_list)>0 else ["N/A"])
            
            staff_list = df_staff['Name'].dropna().unique()
            staff_name = st.selectbox("✍️ Người lập:", options=staff_list)

        c3, c4 = st.columns(2)
        with c3:
            off_no = st.text_input("🆔 Offer No:", value=f"OFF-{datetime.now().strftime('%Y%m%d%H%M')}")
        with c4:
            off_date = st.date_input("📅 Offer Date:", value=datetime.now())

        st.divider()

        # Tìm và thêm vào giỏ hàng
        col_search, _ = st.columns([2, 2])
        with col_search:
            search_pn = st.text_input("🔍 Nhập Part Number để thêm:")
            if st.button("🛒 Thêm vào giỏ hàng", use_container_width=True):
                if search_pn:
                    match = df_sp[df_sp['Part number'].apply(clean_code) == clean_code(search_pn)]
                    if not match.empty:
                        item = match.iloc[0]
                        st.session_state.cart.append({
                            "Part_Number": str(item['Part number']), "Part_Name": str(item['Part name']),
                            "Qty": 1.0, "Unit": str(item['Unit']), "VAT_Rate": 8,
                            "Unit_Price": float(pd.to_numeric(item['Giá bán'], errors='coerce') or 0),
                            "Discount_Percent": 0.0, "Xoá": False
                        })
                        st.rerun()
                    else: st.error("Mã không tồn tại!")

        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            df_cart['Amount'] = df_cart['Unit_Price'] * df_cart['Qty'] * (1 - df_cart['Discount_Percent']/100)
            
            # Editor tạo mới
            edited_create = st.data_editor(
                df_cart, use_container_width=True, hide_index=True,
                column_config={
                    "Amount": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
                    "Unit_Price": st.column_config.NumberColumn(format="%,.0f"),
                    "Xoá": st.column_config.CheckboxColumn()
                },
                key="create_editor"
            )

            if not edited_create.equals(df_cart):
                st.session_state.cart = edited_create[~edited_create['Xoá']].to_dict('records')
                st.rerun()

            # Summary 5 dòng chuẩn
            st.write("### 📊 Tổng kết báo giá")
            ship_cost_in = st.number_input("🚚 Shipment Cost (VND):", value=0, step=10000)
            
            total_amt = edited_create['Amount'].sum()
            sub_total = total_amt + ship_cost_in
            vat_amt = sub_total * 0.08
            grand_total = sub_total + vat_amt

            summary_df = pd.DataFrame({
                "Hạng mục": ["Total amount", "Shipment Cost", "Sub-Total", "VAT (8%)", "Grand Total"],
                "Giá trị (VND)": [format_vnd(total_amt), format_vnd(ship_cost_in), format_vnd(sub_total), format_vnd(vat_amt), format_vnd(grand_total)]
            })
            st.table(summary_df)

            if st.button("💾 LƯU BÁO GIÁ MỚI", use_container_width=True, type="primary"):
                # Ghi vào Header
                new_h = pd.DataFrame([{
                    "Offer_No": off_no, "Date": off_date.strftime('%Y-%m-%d'), "Customer_Name": cust_name,
                    "Contact_Person": contact_person, "Machine_No": machine_no, "Staff": staff_name,
                    "Total_Amount": total_amt, "Shipment_Cost": ship_cost_in, "VAT_Amount": vat_amt, 
                    "Grand_Total": grand_total, "Status": "Draft"
                }])
                # Ghi vào Details
                final_details = edited_create.drop(columns=['Xoá', 'Amount']).copy()
                final_details['Offer_No'] = off_no
                
                update_sheet("Offer_Header", pd.concat([df_h_stored, new_h], ignore_index=True))
                update_sheet("Offer_Details", pd.concat([df_d_stored, final_details], ignore_index=True))
                
                st.success(f"✅ Đã tạo thành công báo giá {off_no}!")
                st.session_state.cart = []
                st.cache_data.clear(); st.rerun()

    # --- 5. TAB ORDER MANAGEMENT (GIỮ NGUYÊN LOGIC EDIT ĐÃ FIX) ---
    elif st.session_state.current_tab == "Order Management":
        sub_tab = st.radio("Chế độ:", ["Quotation", "Offers_Tracking", "SP_Report"], horizontal=True)
        
        if sub_tab == "Quotation":
            st.dataframe(df_h_stored, use_container_width=True, hide_index=True)
            target_id = st.selectbox("Chọn Offer No để xử lý:", [""] + list(df_h_stored['Offer_No'].unique()), key="sel_target")
            
            if target_id:
                if f"edit_{target_id}" not in st.session_state: st.session_state[f"edit_{target_id}"] = False
                
                col_e, col_c = st.columns(2)
                with col_e:
                    if st.button("📝 Edit", use_container_width=True):
                        st.session_state[f"edit_{target_id}"] = True
                        det = df_d_stored[df_d_stored['Offer_No'] == target_id].copy()
                        det['Xoá'] = False
                        for col in ['Qty', 'Unit_Price', 'VAT_Rate', 'Discount_Percent']:
                            det[col] = pd.to_numeric(det[col], errors='coerce').fillna(0)
                        st.session_state[f"data_{target_id}"] = det

                if st.session_state[f"edit_{target_id}"]:
                    st.divider()
                    current_status = df_h_stored[df_h_stored['Offer_No'] == target_id]['Status'].iloc[0]
                    new_status = st.selectbox("📌 Trạng thái báo giá:", ["Draft", "Sent", "Confirmed", "Cancelled"], 
                                             index=["Draft", "Sent", "Confirmed", "Cancelled"].index(current_status) if current_status in ["Draft", "Sent", "Confirmed", "Cancelled"] else 0)

                    # Ô thêm hàng trong Edit
                    c_s1, c_s2 = st.columns([3, 1])
                    with c_s1:
                        new_p_input = st.text_input("🔍 Thêm Part Number:", key=f"in_{target_id}")
                    with c_s2:
                        st.write("##")
                        if st.button("➕ Thêm", use_container_width=True):
                            m = df_sp[df_sp['Part number'].apply(clean_code) == clean_code(new_p_input)]
                            if not m.empty:
                                itm = m.iloc[0]
                                nr = pd.DataFrame([{"Offer_No": target_id, "Part_Number": str(itm['Part number']), "Part_Name": str(itm['Part name']), "Qty": 1.0, "Unit": str(itm['Unit']), "Unit_Price": float(pd.to_numeric(itm['Giá bán'], errors='coerce') or 0), "VAT_Rate": 8, "Discount_Percent": 0.0, "Xoá": False}])
                                st.session_state[f"data_{target_id}"] = pd.concat([st.session_state[f"data_{target_id}"], nr], ignore_index=True)
                                st.rerun()

                    curr_data = st.session_state[f"data_{target_id}"]
                    curr_data['Amount'] = curr_data['Unit_Price'] * curr_data['Qty'] * (1 - curr_data['Discount_Percent']/100)
                    edited_result = st.data_editor(curr_data[['Part_Number', 'Part_Name', 'Qty', 'Unit', 'Unit_Price', 'VAT_Rate', 'Discount_Percent', 'Xoá', 'Amount']], use_container_width=True, hide_index=True, column_config={"Amount": st.column_config.NumberColumn(disabled=True, format="%,.0f"), "Unit_Price": st.column_config.NumberColumn(format="%,.0f"), "Xoá": st.column_config.CheckboxColumn()}, key=f"ed_{target_id}")

                    if not edited_result.equals(curr_data[['Part_Number', 'Part_Name', 'Qty', 'Unit', 'Unit_Price', 'VAT_Rate', 'Discount_Percent', 'Xoá', 'Amount']]):
                        st.session_state[f"data_{target_id}"] = edited_result[~edited_result['Xoá']].copy()
                        st.rerun()

                    # Summary trong Edit
                    t_amt_e = edited_result['Amount'].sum()
                    h_row = df_h_stored[df_h_stored['Offer_No'] == target_id].iloc[0]
                    s_cost_e = float(h_row.get('Shipment_Cost', 0))
                    sum_e = pd.DataFrame({"Hạng mục": ["Total amount", "Shipment Cost", "Sub-Total", "VAT (8%)", "Grand Total"], "Giá trị (VND)": [format_vnd(t_amt_e), format_vnd(s_cost_e), format_vnd(t_amt_e+s_cost_e), format_vnd((t_amt_e+s_cost_e)*0.08), format_vnd((t_amt_e+s_cost_e)*1.08)]})
                    st.table(sum_e)

                    if st.button("💾 UPDATE", use_container_width=True, type="primary"):
                        df_h_stored.loc[df_h_stored['Offer_No'] == target_id, ['Total_Amount', 'VAT_Amount', 'Grand_Total', 'Status']] = [t_amt_e, (t_amt_e+s_cost_e)*0.08, (t_amt_e+s_cost_e)*1.08, new_status]
                        df_d_final = pd.concat([df_d_stored[df_d_stored['Offer_No'] != str(target_id)], st.session_state[f"data_{target_id}"].drop(columns=['Xoá', 'Amount'], errors='ignore')], ignore_index=True)
                        update_sheet("Offer_Header", df_h_stored); update_sheet("Offer_Details", df_d_final)
                        st.success("Cập nhật thành công!"); st.session_state[f"edit_{target_id}"] = False; st.cache_data.clear(); st.rerun()

if __name__ == "__main__":
    main()
