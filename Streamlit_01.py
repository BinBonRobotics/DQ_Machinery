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
        st.error(f"Lỗi kết nối: {e}")
        return None, None, None, None, None

df_mst, df_contact, df_staff, df_machines, df_sp = load_base_data()

# Khởi tạo session_state
if 'cart' not in st.session_state: st.session_state.cart = []
if 'page_view' not in st.session_state: st.session_state.page_view = "New"
if 'shipment_cost' not in st.session_state: st.session_state.shipment_cost = 0
if 'editing_mode' not in st.session_state: st.session_state.editing_mode = False
if 'edit_header' not in st.session_state: st.session_state.edit_header = {}
if 'original_snapshot' not in st.session_state: st.session_state.original_snapshot = None

# --- 3. HÀM PRINT PDF (Sửa lỗi 'GSheetsServiceAccountClient') ---
def print_to_sample_sheet(header, cart_data, shipment, vat_total):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Cách truy cập client chuẩn để tránh lỗi attribute 'client'
        client = conn._conn.client 
        sh = client.open_by_url(SHEET_URL)
        ws = sh.worksheet("Offer Sample")

        # Ghi Header theo Mapping (Dựa trên ảnh image_457521.png)
        ws.update_acell('I7', header['Offer_No'])
        ws.update_acell('I5', header['Offer_Date'])
        ws.update_acell('I10', header['Customer_Name'])
        ws.update_acell('I11', header['Customer_No'])
        ws.update_acell('B12', header['Contact_Person']) # Ghi vào cột B,C gộp
        ws.update_acell('I12', header['Machine_Number'])

        # Xóa hàng cũ (A18:V50)
        ws.batch_clear(["A18:V50"])

        # Chuẩn bị dữ liệu rows để update 1 lần (tăng tốc độ)
        rows_to_update = []
        for idx, row in enumerate(cart_data):
            rows_to_update.append([
                idx + 1,            # A: No
                row["Part Number"], # B: Part Number
                row["Part Name"],   # C: Part Name
                row["Qty"],         # D: Qty
                row["Unit"],        # E: Unit
                "", "",             # F, G (Bỏ qua)
                row["Unit Price"],  # G (Mapping: G-18)
                row["% Discount"],  # H: % Discount
                "",                 # I: Skip
                row["Amount"],      # J: Amount
                "", "", "", "", "", "", "", "", "", "", # K->U
                row["VAT"]          # V: VAT
            ])

        if rows_to_update:
            ws.update(f"A18:V{18 + len(rows_to_update) - 1}", rows_to_update)

        # Ghi phí vận chuyển và thuế
        ws.update_acell('J26', shipment)
        ws.update_acell('J28', vat_total)

        st.success("Đã xuất dữ liệu sang 'Offer Sample' thành công!")
    except Exception as e:
        st.error(f"Lỗi khi Print: {e}")

# --- 4. CALLBACK EDIT QUOTATION ---
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
                    "Part Number": str(r["Part_Number"]), "Part Name": str(r["Part_Name"]),
                    "Qty": int(r["Qty"]), "Unit": str(r["Unit"]), "VAT": int(r["VAT_Rate"]),
                    "Unit Price": int(r["Unit_Price"]), "% Discount": float(r["Discount_Percent"])
                })
            st.session_state.cart = new_cart
            st.session_state.shipment_cost = int(first_row["Shipment_Cost"])
            st.session_state.original_snapshot = {"cart": json.dumps(new_cart, sort_keys=True), "shipment": int(first_row["Shipment_Cost"])}
            st.session_state.editing_mode = True
            st.session_state.page_view = "New"
    except Exception as e: st.error(f"Lỗi load Edit: {e}")

# --- 5. GIAO DIỆN CHÍNH ---
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
        # (Phần nhập liệu Header giữ nguyên hoàn toàn như cũ của bạn)
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
                for code in [c.strip() for c in search_input.split(';')]:
                    match = df_sp[df_sp.iloc[:, 1].astype(str).str.strip() == code]
                    if not match.empty:
                        item = match.iloc[0]
                        st.session_state.cart.append({"Part Number": str(item.iloc[1]), "Part Name": str(item.iloc[4]), "Qty": 1, "Unit": str(item.iloc[7]), "VAT": 8, "Unit Price": int(float(item.iloc[18])) if not pd.isna(item.iloc[18]) else 0, "% Discount": 0})
                st.rerun()
        
        if col_btn2.button("Delete Cart", use_container_width=True):
            st.session_state.cart = []; st.session_state.shipment_cost = 0; st.rerun()

        if st.session_state.cart:
            df_c = pd.DataFrame(st.session_state.cart)
            df_c["Amount"] = (df_c["Qty"] * df_c["Unit Price"] * (1 - df_c["% Discount"] / 100)).astype(int)
            df_c.insert(0, "No", range(1, len(df_c) + 1))
            edited_df = st.data_editor(df_c, hide_index=True, use_container_width=True)

            # --- SUMMARY TABLE (KHÔI PHỤC) ---
            st.markdown("---")
            col_sum1, col_sum2 = st.columns([6, 4])
            with col_sum2:
                total_amount = int(edited_df["Amount"].sum())
                shipment = st.number_input("Shipment Cost:", value=int(st.session_state.shipment_cost))
                st.session_state.shipment_cost = shipment
                total_vat = int((edited_df["VAT"] * edited_df["Amount"] / 100).sum())
                st.table(pd.DataFrame({"Description": ["Total Amount", "Shipment Cost", "Sub-Total", "VAT Total", "Grand Total"],
                                       "Value": [total_amount, shipment, total_amount+shipment, total_vat, total_amount+shipment+total_vat]}).style.format({"Value": "{:,.0f}"}))

            # --- SAVE & PRINT BUTTONS (KHÔI PHỤC) ---
            def save_final(status=""):
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    # Logic so sánh thay đổi để chốt ngày (giữ nguyên logic cũ của bạn)
                    has_chg = False
                    if st.session_state.editing_mode and st.session_state.original_snapshot:
                        if json.dumps(st.session_state.cart, sort_keys=True) != st.session_state.original_snapshot["cart"] or int(shipment) != st.session_state.original_snapshot["shipment"]:
                            has_chg = True
                    f_date = str(datetime.now().date()) if has_chg else str(off_date)
                    
                    rows = []
                    for _, r in edited_df.iterrows():
                        rows.append({"Offer_No": offer_no, "Offer_Date": f_date, "Customer_Name": selected_name, "Customer_No": c_no, "Tax_Code": f"'{t_code_display}", "Address": addr, "Contact_Person": contact_person, "Officer": officer, "Machine_Number": machine_no, "Ordinal_Number": r["No"], "Part_Number": r["Part Number"], "Part_Name": r["Part Name"], "Qty": r["Qty"], "Unit": r["Unit"], "VAT_Rate": r["VAT"], "Unit_Price": r["Unit Price"], "Discount_Percent": r["% Discount"], "Amount": r["Amount"], "Total_Amount": total_amount, "Shipment_Cost": shipment, "Sub_Total": total_amount+shipment, "VAT_Total": total_vat, "Grand_Total": total_amount+shipment+total_vat, "Status": status})
                    
                    exist = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details", ttl=0)
                    upd = pd.concat([exist[exist["Offer_No"].astype(str) != str(offer_no)], pd.DataFrame(rows)], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Offer_Details", data=upd)
                    st.success("Saved!"); st.session_state.cart = []; st.session_state.editing_mode = False; st.rerun()
                except Exception as e: st.error(f"Lỗi Save: {e}")

            col_f1, col_f2, col_f3, _ = st.columns([1.5, 1.5, 2, 5])
            if col_f1.button("Save Quotation", type="primary", use_container_width=True): save_final("")
            if col_f2.button("Print PDF", use_container_width=True):
                h_data = {"Offer_No": offer_no, "Offer_Date": str(off_date), "Customer_Name": selected_name, "Customer_No": c_no, "Contact_Person": contact_person, "Machine_Number": machine_no}
                print_to_sample_sheet(h_data, edited_df.to_dict('records'), shipment, total_vat)
            if st.session_state.editing_mode and col_f3.button("Confirmed Quotation", use_container_width=True):
                save_final("confirmed")

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
