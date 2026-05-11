import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(layout="wide", page_title="Spare Part Quotation System")

# URL Google Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8/edit#gid=903775380"

# --- 2. HÀM LOAD DỮ LIỆU ---
@st.cache_data(ttl=300) # Tăng thời gian cache lên 5 phút để tránh lỗi Quota
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

# Khởi tạo trạng thái hệ thống
if 'cart' not in st.session_state: st.session_state.cart = []
if 'page_view' not in st.session_state: st.session_state.page_view = "New"
if 'search_error' not in st.session_state: st.session_state.search_error = ""
if 'shipment_cost' not in st.session_state: st.session_state.shipment_cost = 0
if 'editing_mode' not in st.session_state: st.session_state.editing_mode = False
if 'edit_header' not in st.session_state: st.session_state.edit_header = {}

# --- 3. HÀM XỬ LÝ LOAD ĐỂ EDIT (GIẢI QUYẾT LỖI 429 & DOUBLE CLICK) ---
def handle_edit_logic(offer_no_to_load):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Đọc trực tiếp không qua cache để lấy dữ liệu mới nhất
        all_offers = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details", ttl=0)
        edit_df = all_offers[all_offers["Offer_No"].astype(str) == str(offer_no_to_load)]
        
        if not edit_df.empty:
            first_row = edit_df.iloc[0]
            
            # Gọt dấu nháy đơn ở Tax_Code nếu có
            raw_tax = str(first_row["Tax_Code"])
            clean_tax = raw_tax[1:] if raw_tax.startswith("'") else raw_tax

            st.session_state.edit_header = {
                "Customer_Name": first_row["Customer_Name"],
                "Contact_Person": first_row["Contact_Person"],
                "Officer": first_row["Officer"],
                "Machine_Number": first_row["Machine_Number"],
                "Offer_Date": first_row["Offer_Date"],
                "Offer_No": first_row["Offer_No"],
                "Clean_Tax": clean_tax
            }
            
            new_cart = []
            for _, r in edit_df.iterrows():
                new_cart.append({
                    "Part Number": str(r["Part_Number"]),
                    "Part Name": str(r["Part_Name"]),
                    "Qty": int(r["Qty"]),
                    "Unit": str(r["Unit"]),
                    "VAT": int(r["VAT_Rate"]),
                    "Unit Price": int(r["Unit_Price"]),
                    "% Discount": float(r["Discount_Percent"])
                })
            st.session_state.cart = new_cart
            st.session_state.shipment_cost = int(first_row["Shipment_Cost"])
            st.session_state.editing_mode = True
            st.session_state.search_error = ""
        else:
            st.error("Không tìm thấy dữ liệu cho Offer No này.")
    except Exception as e:
        st.error(f"Lỗi khi load báo giá: {e}")

# --- 4. SIDE MENU ---
with st.sidebar:
    st.header("MENU")
    option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh App", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 5. CHỨC NĂNG CHÍNH ---
if df_mst is not None and option == "Spare Part Quotation":
    col_b1, col_b2, _ = st.columns([2, 2, 5])
    if col_b1.button("New Spare Part Offer", use_container_width=True): 
        st.session_state.page_view = "New"
        st.session_state.editing_mode = False
        st.session_state.cart = []
        st.session_state.edit_header = {}
        st.rerun()

    if col_b2.button("Order Management", use_container_width=True): 
        st.session_state.page_view = "Manage"

    if st.session_state.page_view == "New":
        st.markdown(f"### {'EDIT' if st.session_state.editing_mode else 'NEW'} Spare Part Offer")
        
        # --- OFFER HEADER ---
        names = df_mst.iloc[:, 2].dropna().unique().tolist()
        default_name = st.session_state.edit_header.get("Customer_Name", names[0])
        selected_name = st.selectbox("Customer Name:", options=names, index=names.index(default_name) if default_name in names else 0)
        
        cust_row = df_mst[df_mst.iloc[:, 2] == selected_name].iloc[0]
        c_no = str(cust_row.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=c_no, disabled=True)
        
        # Hiển thị Tax Code (ưu tiên Tax đã gọt nếu đang ở chế độ Edit)
        if st.session_state.editing_mode and "Clean_Tax" in st.session_state.edit_header:
            t_code_display = st.session_state.edit_header["Clean_Tax"]
        else:
            t_val = cust_row.iloc[5]
            t_code_display = str(int(float(t_val))).zfill(10) if not pd.isna(t_val) else ""
        
        st.text_input("Tax Code:", value=t_code_display, disabled=True)
        
        addr = str(cust_row.iloc[4]) if not pd.isna(cust_row.iloc[4]) else ""
        st.text_area("Address:", value=addr, height=70, disabled=True)
        
        f_contact = df_contact[df_contact.iloc[:, 1].astype(str).str.contains(c_no)]
        contact_list = f_contact.iloc[:, 7].dropna().tolist() if not f_contact.empty else ["N/A"]
        default_contact = st.session_state.edit_header.get("Contact_Person", contact_list[0] if contact_list else "N/A")
        contact_person = st.selectbox("Contact Person:", options=contact_list, index=contact_list.index(default_contact) if default_contact in contact_list else 0)
        
        staff_list = df_staff.iloc[:, 1].dropna().tolist()
        default_officer = st.session_state.edit_header.get("Officer", staff_list[0] if staff_list else "")
        officer = st.selectbox("Officer:", options=staff_list, index=staff_list.index(default_officer) if default_officer in staff_list else 0)
        
        f_machines = df_machines[df_machines.iloc[:, 1].astype(str).str.contains(c_no)]
        machine_list = f_machines.iloc[:, 14].dropna().tolist() if not f_machines.empty else ["N/A"]
        default_machine = st.session_state.edit_header.get("Machine_Number", machine_list[0] if machine_list else "N/A")
        machine_no = st.selectbox("Machine Number:", options=machine_list, index=machine_list.index(default_machine) if default_machine in machine_list else 0)
        
        default_date = st.session_state.edit_header.get("Offer_Date", datetime.now())
        if isinstance(default_date, str):
            try: default_date = datetime.strptime(default_date, '%Y-%m-%d')
            except: default_date = datetime.now()
        off_date = st.date_input("Offer Date:", value=default_date)
        
        default_off_no = st.session_state.edit_header.get("Offer_No", f"{off_date.year}-{off_date.month:02d}-0001")
        offer_no = st.text_input("Offer No:", value=default_off_no)

        st.markdown("---")
        st.subheader("Offer Descriptions")
        search_input = st.text_input("Search Part Number:", placeholder="2024956492;2031956280")
        
        if st.session_state.search_error: st.error(st.session_state.search_error)

        col_act1, col_act2, _ = st.columns([1.5, 1.5, 6])
        if col_act1.button("Add to Cart", type="primary", use_container_width=True):
            if search_input:
                codes = [c.strip() for c in search_input.split(';')]
                not_found = []
                for code in codes:
                    match = df_sp[df_sp.iloc[:, 1].astype(str).str.strip() == code]
                    if not match.empty:
                        item = match.iloc[0]
                        raw_vat = item.iloc[12]
                        try: display_vat = int(float(raw_vat) * 100) if float(raw_vat) < 1 else int(float(raw_vat))
                        except: display_vat = 0
                        st.session_state.cart.append({
                            "Part Number": str(item.iloc[1]), "Part Name": str(item.iloc[4]),
                            "Qty": 1, "Unit": str(item.iloc[7]), "VAT": display_vat,
                            "Unit Price": int(float(item.iloc[18])) if not pd.isna(item.iloc[18]) else 0, "% Discount": 0
                        })
                    else: not_found.append(code)
                st.session_state.search_error = f"Part Number {', '.join(not_found)} not found" if not_found else ""
                st.rerun()

        if col_act2.button("Delete Cart", use_container_width=True):
            st.session_state.cart = []; st.session_state.search_error = ""; st.session_state.shipment_cost = 0; st.rerun()

        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            df_cart["Amount"] = (df_cart["Qty"] * df_cart["Unit Price"] * (1 - df_cart["% Discount"] / 100)).astype(int)
            df_cart.insert(0, "No", range(1, len(df_cart) + 1))
            df_cart["Xóa dòng"] = False

            edited_df = st.data_editor(
                df_cart,
                column_config={
                    "VAT": st.column_config.NumberColumn(format="%d", disabled=True), 
                    "Unit Price": st.column_config.NumberColumn(format="%,d", disabled=True),
                    "Amount": st.column_config.NumberColumn(format="%,d", disabled=True),
                    "Xóa dòng": st.column_config.CheckboxColumn()
                },
                hide_index=True, use_container_width=True, key="editor"
            )

            if not edited_df.equals(df_cart):
                st.session_state.cart = edited_df[edited_df["Xóa dòng"] == False].drop(columns=["No", "Amount", "Xóa dòng"]).to_dict('records')
                st.rerun()

            st.markdown("---")
            col_sum1, col_sum2 = st.columns([6, 4])
            with col_sum2:
                total_amount = int(df_cart["Amount"].sum())
                total_vat = int((df_cart["VAT"] * df_cart["Unit Price"] * df_cart["Qty"] / 100).sum())
                shipment = st.number_input("Shipment Cost:", min_value=0, value=int(st.session_state.shipment_cost))
                st.session_state.shipment_cost = shipment
                sub_total = total_amount + shipment
                grand_total = sub_total + total_vat
                st.table(pd.DataFrame({
                    "Description": ["Total Amount", "Shipment Cost", "Sub-Total", "VAT Total", "Grand Total"],
                    "Value": [total_amount, shipment, sub_total, total_vat, grand_total]
                }).style.format({"Value": "{:,.0f}"}))

            def save_process(status_text=""):
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    new_rows = []
                    tax_save = f"'{t_code_display}"
                    for idx, row in edited_df[edited_df["Xóa dòng"] == False].iterrows():
                        new_rows.append({
                            "Offer_No": str(offer_no).strip(), "Offer_Date": str(off_date),
                            "Customer_Name": selected_name, "Customer_No": str(c_no), "Tax_Code": tax_save,
                            "Address": addr, "Contact_Person": contact_person, "Officer": officer,
                            "Machine_Number": machine_no, "Ordinal_Number": row["No"],
                            "Part_Number": row["Part Number"], "Part_Name": row["Part Name"],
                            "Qty": row["Qty"], "Unit": row["Unit"], "VAT_Rate": row["VAT"],
                            "Unit_Price": row["Unit Price"], "Discount_Percent": row["% Discount"],
                            "Amount": row["Amount"], "Total_Amount": total_amount, "Shipment_Cost": shipment,
                            "Sub_Total": sub_total, "VAT_Total": total_vat, "Grand_Total": grand_total, "Status": status_text
                        })
                    
                    df_new = pd.DataFrame(new_rows)
                    existing = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details", ttl=0)
                    
                    if existing is not None and not existing.empty:
                        if "Status" not in existing.columns: existing["Status"] = ""
                        updated_df = pd.concat([existing[existing["Offer_No"].astype(str) != str(offer_no).strip()], df_new], ignore_index=True)
                    else: updated_df = df_new

                    conn.update(spreadsheet=SHEET_URL, worksheet="Offer_Details", data=updated_df)
                    st.success(f"Quotation {offer_no} saved!"); st.session_state.editing_mode = False
                    st.session_state.cart = []; st.session_state.edit_header = {}; st.rerun()
                except Exception as e: st.error(f"Error: {e}")

            col_save1, col_save2, col_save3, _ = st.columns([1.5, 1.5, 2, 5])
            if col_save1.button("Save Quotation", type="primary", use_container_width=True): save_process("")
            if st.session_state.editing_mode and col_save3.button("Confirmed Quotation", use_container_width=True): save_process("confirmed")
            if col_save2.button("Print PDF", use_container_width=True): st.info("Coming Soon")

        # --- PHẦN EDIT QUOTATION (DƯỚI SUMMARY) ---
        st.markdown("---")
        st.subheader("Search & Edit Saved Quotation")
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # Dùng ttl=10 để list Offer_No không bị cũ quá lâu nhưng không gây lỗi 429
            offer_data = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details", ttl=10)
            if offer_data is not None and not offer_data.empty:
                saved_list = sorted(offer_data["Offer_No"].astype(str).unique().tolist(), reverse=True)
                target_no = st.selectbox("Select Offer No:", options=saved_list)
                
                # Nút bấm Edit đã được tối ưu logic
                if st.button("Edit Quotation", use_container_width=True):
                    handle_edit_logic(target_no)
                    st.rerun()
        except: st.write("Đang tải danh sách báo giá...")

    elif st.session_state.page_view == "Manage":
        st.info("Order Management Page")
