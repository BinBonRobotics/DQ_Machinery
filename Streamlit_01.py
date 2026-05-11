import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import json

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(layout="wide", page_title="Spare Part Quotation System")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8/edit#gid=903775380"

# --- 2. HÀM LOAD DỮ LIỆU ---
@st.cache_data(ttl=300)
def load_base_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST").dropna(how='all')
        contact = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact").dropna(how='all')
        staff = conn.read(spreadsheet=SHEET_URL, worksheet="Staff").dropna(how='all')
        machines = conn.read(spreadsheet=SHEET_URL, worksheet="List_of_ machines").dropna(how='all')
        sp = conn.read(spreadsheet=SHEET_URL, worksheet="SP_List").dropna(how='all')
        return mst, contact, staff, machines, sp
    except Exception as e:
        st.error(f"Lỗi kết nối cơ sở dữ liệu: {e}")
        return None, None, None, None, None

df_mst, df_contact, df_staff, df_machines, df_sp = load_base_data()

# Khởi tạo session_state
if 'cart' not in st.session_state: st.session_state.cart = []
if 'page_view' not in st.session_state: st.session_state.page_view = "New"
if 'shipment_cost' not in st.session_state: st.session_state.shipment_cost = 0
if 'editing_mode' not in st.session_state: st.session_state.editing_mode = False
if 'edit_header' not in st.session_state: st.session_state.edit_header = {}
if 'original_snapshot' not in st.session_state: st.session_state.original_snapshot = None

# --- 3. CALLBACK EDIT QUOTATION (Giữ nguyên logic cũ) ---
def on_edit_click():
    target_no = st.session_state.get('selected_offer_to_edit')
    if not target_no: return
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        all_offers = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details", ttl=0)
        edit_df = all_offers[all_offers["Offer_No"].astype(str) == str(target_no)]
        if not edit_df.empty:
            first_row = edit_df.iloc[0]
            st.session_state.edit_header = {
                "Customer_Name": first_row["Customer_Name"],
                "Contact_Person": first_row["Contact_Person"],
                "Officer": first_row["Officer"],
                "Machine_Number": first_row["Machine_Number"],
                "Offer_Date": str(first_row["Offer_Date"]),
                "Offer_No": first_row["Offer_No"],
                "Clean_Tax": str(first_row["Tax_Code"]).replace("'", "")
            }
            new_cart = []
            for _, r in edit_df.iterrows():
                new_cart.append({
                    "Part Number": str(r["Part_Number"]).split('.')[0], # Sửa lỗi .0
                    "Part Name": str(r["Part_Name"]),
                    "Qty": int(r["Qty"]), "Unit": str(r["Unit"]), "VAT": int(r["VAT_Rate"]),
                    "Unit Price": int(r["Unit_Price"]), "% Discount": float(r["Discount_Percent"]),
                    "Delete": False
                })
            st.session_state.cart = new_cart
            st.session_state.shipment_cost = int(first_row["Shipment_Cost"])
            st.session_state.original_snapshot = {"cart": json.dumps(new_cart, sort_keys=True), "shipment": int(first_row["Shipment_Cost"])}
            st.session_state.editing_mode = True
            st.session_state.page_view = "New"
    except Exception as e: st.error(f"Lỗi load Edit: {e}")

# --- 4. GIAO DIỆN CHÍNH ---
with st.sidebar:
    st.header("MENU")
    option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh App", use_container_width=True):
        st.cache_data.clear(); st.rerun()

if df_mst is not None and option == "Spare Part Quotation":
    col_b1, col_b2, _ = st.columns([2, 2, 5])
    if col_b1.button("New Spare Part Offer", use_container_width=True): 
        st.session_state.page_view = "New"; st.session_state.editing_mode = False; st.session_state.cart = []; st.session_state.edit_header = {}; st.rerun()
    if col_b2.button("Order Management", use_container_width=True): st.session_state.page_view = "Manage"

    if st.session_state.page_view == "New":
        # (Phần Header giữ nguyên hoàn toàn như cũ)
        names = df_mst.iloc[:, 2].dropna().unique().tolist()
        default_name = st.session_state.edit_header.get("Customer_Name", names[0] if names else "")
        selected_name = st.selectbox("Customer Name:", options=names, index=names.index(default_name) if default_name in names else 0)
        
        cust_row = df_mst[df_mst.iloc[:, 2] == selected_name].iloc[0]
        c_no = str(cust_row.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=c_no, disabled=True)
        
        t_code_display = st.session_state.edit_header.get("Clean_Tax", str(int(float(cust_row.iloc[5]))).zfill(10) if not pd.isna(cust_row.iloc[5]) else "")
        st.text_input("Tax Code:", value=t_code_display, disabled=True)
        
        addr = str(cust_row.iloc[4]) if not pd.isna(cust_row.iloc[4]) else ""
        st.text_area("Address:", value=addr, height=70, disabled=True)
        
        f_contact = df_contact[df_contact.iloc[:, 1].astype(str).str.contains(c_no)]
        contact_list = f_contact.iloc[:, 7].dropna().tolist() if not f_contact.empty else ["N/A"]
        contact_person = st.selectbox("Contact Person:", options=contact_list, index=contact_list.index(st.session_state.edit_header.get("Contact_Person", contact_list[0])) if st.session_state.edit_header.get("Contact_Person") in contact_list else 0)
        
        staff_list = df_staff.iloc[:, 1].dropna().tolist()
        officer = st.selectbox("Officer:", options=staff_list, index=staff_list.index(st.session_state.edit_header.get("Officer", staff_list[0])) if st.session_state.edit_header.get("Officer") in staff_list else 0)
        
        f_machines = df_machines[df_machines.iloc[:, 1].astype(str).str.contains(c_no)]
        machine_list = f_machines.iloc[:, 14].dropna().tolist() if not f_machines.empty else ["N/A"]
        machine_no = st.selectbox("Machine Number:", options=machine_list, index=machine_list.index(st.session_state.edit_header.get("Machine_Number", machine_list[0])) if st.session_state.edit_header.get("Machine_Number") in machine_list else 0)
        
        d_val = st.session_state.edit_header.get("Offer_Date", datetime.now())
        if isinstance(d_val, str): d_val = datetime.strptime(d_val, '%Y-%m-%d')
        off_date = st.date_input("Offer Date:", value=d_val)
        offer_no = st.text_input("Offer No:", value=st.session_state.edit_header.get("Offer_No", f"{off_date.year}-{off_date.month:02d}-0001"))

        st.markdown("---")
        # --- CART SECTION ---
        search_input = st.text_input("Search Part Number:", placeholder="2024956492;2031956280")
        col_btn1, col_btn2, _ = st.columns([1.5, 1.5, 7])
        
        if col_btn1.button("Add to Cart", type="primary", use_container_width=True):
            if search_input:
                not_found = []
                for code in [c.strip() for c in search_input.split(';')]:
                    # Sửa lỗi so sánh Part Number (bỏ .0)
                    match = df_sp[df_sp.iloc[:, 1].astype(str).str.replace(r'\.0$', '', regex=True) == code]
                    if not match.empty:
                        item = match.iloc[0]
                        st.session_state.cart.append({
                            "Part Number": str(item.iloc[1]).split('.')[0], 
                            "Part Name": str(item.iloc[4]), "Qty": 1, "Unit": str(item.iloc[7]), 
                            "VAT": 8, "Unit Price": int(float(item.iloc[18])) if not pd.isna(item.iloc[18]) else 0, 
                            "% Discount": 0.0, "Delete": False
                        })
                    else:
                        not_found.append(code)
                if not_found:
                    st.error(f"Không tìm thấy Part Number: {', '.join(not_found)}")
                st.rerun()
        
        if col_btn2.button("Delete Cart", use_container_width=True):
            st.session_state.cart = []; st.session_state.shipment_cost = 0; st.rerun()

        if st.session_state.cart:
            df_c = pd.DataFrame(st.session_state.cart)
            # Tính toán Amount trực tiếp
            df_c["Amount"] = (df_c["Qty"] * df_c["Unit Price"] * (1 - df_c["% Discount"] / 100)).astype(int)
            
            # Cấu hình bảng hiển thị: Chỉ cho phép Qty, % Discount và Delete
            edited_df = st.data_editor(
                df_c,
                column_config={
                    "Part Number": st.column_config.TextColumn("Part Number", disabled=True),
                    "Part Name": st.column_config.TextColumn("Part Name", disabled=True),
                    "Unit": st.column_config.TextColumn("Unit", disabled=True),
                    "VAT": st.column_config.NumberColumn("VAT", disabled=True),
                    "Unit Price": st.column_config.NumberColumn("Unit Price", format="%d", disabled=True),
                    "Qty": st.column_config.NumberColumn("Qty", min_value=1),
                    "% Discount": st.column_config.NumberColumn("% Discount", min_value=0.0, max_value=100.0, format="%.1f%%"),
                    "Amount": st.column_config.NumberColumn("Amount", format="%d", disabled=True),
                    "Delete": st.column_config.CheckboxColumn("Delete")
                },
                hide_index=True,
                use_container_width=True,
                key="editor"
            )

            # Xử lý xóa dòng và cập nhật session_state để Amount thay đổi ngay
            if not edited_df.equals(df_c):
                # Lọc bỏ các dòng bị tích "Delete"
                new_cart = edited_df[edited_df["Delete"] == False].to_dict('records')
                st.session_state.cart = new_cart
                st.rerun()

            # --- SUMMARY TABLE ---
            st.markdown("---")
            col_sum1, col_sum2 = st.columns([6, 4])
            with col_sum2:
                total_amount = int(edited_df["Amount"].sum())
                shipment = st.number_input("Shipment Cost:", value=int(st.session_state.shipment_cost))
                st.session_state.shipment_cost = shipment
                total_vat = int((edited_df["VAT"] * edited_df["Amount"] / 100).sum())
                
                # Định dạng hiển thị hàng nghìn cho bảng Summary
                summary_data = {
                    "Description": ["Total Amount", "Shipment Cost", "Sub-Total", "VAT Total", "Grand Total"],
                    "Value": [total_amount, shipment, total_amount+shipment, total_vat, total_amount+shipment+total_vat]
                }
                st.table(pd.DataFrame(summary_data).style.format({"Value": "{:,.0f}"}))

            # --- NÚT BẤM LƯU ---
            def save_final(status=""):
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    has_chg = False
                    if st.session_state.editing_mode and st.session_state.original_snapshot:
                        if json.dumps(st.session_state.cart, sort_keys=True) != st.session_state.original_snapshot["cart"]:
                            has_chg = True
                    f_date = str(datetime.now().date()) if has_chg else str(off_date)
                    
                    rows = []
                    for idx, r in edited_df.iterrows():
                        rows.append({
                            "Offer_No": offer_no, "Offer_Date": f_date, "Customer_Name": selected_name, 
                            "Customer_No": c_no, "Tax_Code": f"'{t_code_display}", "Address": addr,
                            "Contact_Person": contact_person, "Officer": officer, "Machine_Number": machine_no,
                            "Ordinal_Number": idx + 1, "Part_Number": r["Part Number"], "Part_Name": r["Part Name"],
                            "Qty": r["Qty"], "Unit": r["Unit"], "VAT_Rate": r["VAT"], "Unit_Price": r["Unit Price"],
                            "Discount_Percent": r["% Discount"], "Amount": r["Amount"], "Total_Amount": total_amount,
                            "Shipment_Cost": shipment, "Sub_Total": total_amount+shipment, "VAT_Total": total_vat,
                            "Grand_Total": total_amount+shipment+total_vat, "Status": status
                        })
                    
                    exist = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details", ttl=0)
                    upd = pd.concat([exist[exist["Offer_No"].astype(str) != str(offer_no)], pd.DataFrame(rows)], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Offer_Details", data=upd)
                    st.success("Đã lưu báo giá thành công!"); st.session_state.cart = []; st.session_state.editing_mode = False; st.rerun()
                except Exception as e: st.error(f"Lỗi Save: {e}")

            col_f1, col_f2, col_f3, _ = st.columns([1.5, 1.5, 2, 5])
            if col_f1.button("Save Quotation", type="primary", use_container_width=True): save_final("")
            if col_f2.button("Print PDF", use_container_width=True): st.warning("Tính năng Print PDF tạm tắt theo yêu cầu.")
            if st.session_state.editing_mode and col_f3.button("Confirmed Quotation", use_container_width=True): save_final("confirmed")

        # --- SEARCH EDIT ---
        st.markdown("---")
        st.subheader("Search & Edit Saved Quotation")
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            off_data = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details", ttl=0)
            if not off_data.empty:
                s_list = sorted(off_data["Offer_No"].astype(str).unique().tolist(), reverse=True)
                st.selectbox("Select Offer No:", options=s_list, key="selected_offer_to_edit")
                st.button("Edit Quotation", use_container_width=True, on_click=on_edit_click)
        except: st.write("Đang tải danh sách báo giá...")
