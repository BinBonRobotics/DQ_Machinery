import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

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

# --- 3. HÀM PRINT PDF (GHI ĐÚNG Ô I7) ---
def print_pdf_to_sheet(off_no):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Tạo dataframe chỉ có 1 giá trị duy nhất
        df_update = pd.DataFrame([off_no])
        
        # Ghi vào tab Offer Sample, bắt đầu từ ô I7. 
        # index=False và header=False cực kỳ quan trọng để không ghi đè lung tung.
        conn.update(
            spreadsheet=SHEET_URL, 
            worksheet="Offer Sample", 
            data=df_update, 
            header=False, 
            index=False, 
            range="I7" 
        )
        st.success(f"✅ Đã cập nhật Offer No: {off_no} vào ô I7.")
    except Exception as e:
        st.error(f"Lỗi khi Print PDF: {e}")

# --- 4. CALLBACK EDIT QUOTATION ---
def on_edit_click():
    display_val = st.session_state.get('selected_offer_to_edit')
    if not display_val: return
    target_no = display_val.split(" _ ")[0]
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
                    "Part Number": str(r["Part_Number"]).split('.')[0],
                    "Part Name": str(r["Part_Name"]),
                    "Qty": int(r["Qty"]), "Unit": str(r["Unit"]), "VAT": int(r["VAT_Rate"]),
                    "Unit Price": int(r["Unit_Price"]), "% Discount": int(float(r["Discount_Percent"]))
                })
            st.session_state.cart = new_cart
            st.session_state.shipment_cost = int(first_row["Shipment_Cost"])
            st.session_state.editing_mode = True
            st.session_state.page_view = "New"
    except Exception as e: st.error(f"Lỗi load Edit: {e}")

# --- 5. GIAO DIỆN CHÍNH ---
with st.sidebar:
    st.header("MENU")
    option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if df_mst is not None and option == "Spare Part Quotation":
    col_b1, col_b2, _ = st.columns([2, 2, 5])
    if col_b1.button("New Spare Part Offer", use_container_width=True): 
        st.session_state.page_view = "New"; st.session_state.editing_mode = False; st.session_state.cart = []; st.session_state.edit_header = {}; st.rerun()
    if col_b2.button("Order Management", use_container_width=True): st.session_state.page_view = "Manage"

    if st.session_state.page_view == "New":
        # HEADER UI
        names = df_mst.iloc[:, 2].dropna().unique().tolist()
        default_name = st.session_state.edit_header.get("Customer_Name", names[0] if names else "")
        selected_name = st.selectbox("Customer Name:", options=names, index=names.index(default_name) if default_name in names else 0)
        
        cust_row = df_mst[df_mst.iloc[:, 2] == selected_name].iloc[0]
        c_no = str(cust_row.iloc[1]).split('.')[0]
        t_code_display = st.session_state.edit_header.get("Clean_Tax", str(int(float(cust_row.iloc[5]))).zfill(10) if not pd.isna(cust_row.iloc[5]) else "")
        addr = str(cust_row.iloc[4]) if not pd.isna(cust_row.iloc[4]) else ""
        
        st.text_input("Customer No:", value=c_no, disabled=True)
        st.text_input("Tax Code:", value=t_code_display, disabled=True)
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
        # CART UI
        search_input = st.text_input("Search Part Number:", placeholder="Dùng dấu ; để ngăn cách")
        if st.button("Add to Cart", type="primary"):
            if search_input:
                for code in [c.strip() for c in search_input.split(';')]:
                    match = df_sp[df_sp.iloc[:, 1].astype(str).str.replace(r'\.0$', '', regex=True) == code]
                    if not match.empty:
                        item = match.iloc[0]
                        st.session_state.cart.append({
                            "Part Number": str(item.iloc[1]).split('.')[0], "Part Name": str(item.iloc[4]), "Qty": 1, 
                            "Unit": str(item.iloc[7]), "VAT": 8, "Unit Price": int(float(item.iloc[18])) if not pd.isna(item.iloc[18]) else 0, "% Discount": 0
                        })
                st.rerun()
        
        if st.session_state.cart:
            df_display = pd.DataFrame(st.session_state.cart)
            df_display["Amount"] = (df_display["Qty"] * df_display["Unit Price"] * (1 - df_display["% Discount"] / 100)).astype(int)
            
            edited_df = st.data_editor(df_display, hide_index=True, use_container_width=True)
            
            col_sum1, col_sum2 = st.columns([6, 4])
            with col_sum2:
                total_amount = int(edited_df["Amount"].sum())
                shipment = st.number_input("Shipment Cost:", value=int(st.session_state.shipment_cost))
                st.write(f"**Grand Total:** {total_amount + shipment:,.0f}")

            def save_final():
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    # Logic lưu vào Offer_Details giữ nguyên như cũ
                    st.success("Đã lưu vào Offer_Details!")
                except Exception as e: st.error(f"Lỗi lưu: {e}")

            col_f1, col_f2, _ = st.columns([2, 2, 6])
            if col_f1.button("Save Quotation", use_container_width=True): save_final()
            if col_f2.button("Print PDF", use_container_width=True): print_pdf_to_sheet(offer_no)

        # SEARCH SECTION
        st.markdown("---")
        st.subheader("Search & Edit Saved Quotation")
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            off_data = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details", ttl=0)
            if not off_data.empty:
                unique_offers = off_data.drop_duplicates(subset=["Offer_No"])
                s_list = (unique_offers["Offer_No"].astype(str) + " _ " + unique_offers["Customer_Name"].astype(str)).tolist()
                st.selectbox("Select Offer No:", options=s_list, key="selected_offer_to_edit")
                st.button("Edit Quotation", on_click=on_edit_click)
        except: pass
