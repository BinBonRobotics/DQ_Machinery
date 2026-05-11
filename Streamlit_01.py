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
if 'search_error' not in st.session_state: st.session_state.search_error = ""
if 'shipment_cost' not in st.session_state: st.session_state.shipment_cost = 0
if 'editing_mode' not in st.session_state: st.session_state.editing_mode = False
if 'edit_header' not in st.session_state: st.session_state.edit_header = {}
if 'original_snapshot' not in st.session_state: st.session_state.original_snapshot = None

# --- 3. CALLBACK EDIT ---
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
    except Exception as e: st.error(f"Lỗi: {e}")

# --- 4. HÀM PRINT PDF (ĐỔ DỮ LIỆU VÀO TAB OFFER SAMPLE) ---
def print_to_sample_sheet(header_data, cart_df, totals):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Sử dụng thư viện gspread trực tiếp từ connection để ghi ô cụ thể
        client = conn._instance.client
        sh = client.open_by_url(SHEET_URL)
        ws = sh.worksheet("Offer Sample")

        # 1. Ghi Header theo Mapping
        ws.update_acell('I7', header_data['Offer_No'])
        ws.update_acell('I5', header_data['Offer_Date'])
        ws.update_acell('I10', header_data['Customer_Name'])
        ws.update_acell('I11', header_data['Customer_No'])
        ws.update_acell('B12', header_data['Contact_Person']) # Column B,C-12
        ws.update_acell('I12', header_data['Machine_Number'])
        
        # 2. Xóa dữ liệu hàng hóa cũ (Clear từ dòng 18 đến 50 để sạch mẫu)
        # Chỉ xóa dữ liệu nội dung, giữ nguyên format nếu có thể
        ws.batch_clear(["A18:V50"])

        # 3. Ghi danh sách hàng hóa (Bắt đầu từ hàng 18)
        items_to_print = []
        for idx, row in cart_df.iterrows():
            items_to_print.append([
                row["No"],              # Col A: No
                row["Part Number"],     # Col B: Part Number
                row["Part Name"],       # Col C: Part Name
                row["Qty"],             # Col D: Qty
                row["Unit"],            # Col E: Unit
                "", "",                 # Col F, G (Skip)
                row["Unit Price"],      # Col G (Mapping ghi G-18)
                row["% Discount"],      # Col H (Mapping ghi H-18)
                "",                     # Col I (Skip)
                row["Amount"],          # Col J (Mapping ghi J-18)
                "", "", "", "", "", "", "", "", "", "", # K->U
                row["VAT"]              # Col V (Mapping ghi V-18)
            ])
        
        # Cập nhật hàng loạt để nhanh hơn
        if items_to_print:
            ws.update(f"A18:V{18 + len(items_to_print) - 1}", items_to_print)

        # 4. Ghi các ô tổng hợp
        ws.update_acell('J26', totals['shipment'])
        ws.update_acell('J28', totals['vat_total'])
        
        st.success("Dữ liệu đã được đổ vào tab 'Offer Sample'. Bạn có thể kiểm tra và in PDF từ Google Sheets!")
    except Exception as e:
        st.error(f"Lỗi khi in: {e}")

# --- 5. MAIN APP ---
if df_mst is not None and option == "Spare Part Quotation":
    col_b1, col_b2, _ = st.columns([2, 2, 5])
    if col_b1.button("New Spare Part Offer", use_container_width=True): 
        st.session_state.page_view = "New"; st.session_state.editing_mode = False; st.session_state.cart = []; st.rerun()

    if st.session_state.page_view == "New":
        # ... (Giữ nguyên phần UI chọn khách hàng, nhập liệu) ...
        # [Đoạn code giao diện khách hàng và giỏ hàng giữ nguyên như cũ]
        # Giả định các biến selected_name, c_no, off_date, offer_no đã được định nghĩa ở UI
        
        # ... (Phần bảng giỏ hàng edited_df) ...
        
        if st.session_state.cart:
            # Tính toán các giá trị tổng
            total_amount = int(df_cart["Amount"].sum())
            total_vat = int((df_cart["VAT"] * df_cart["Unit Price"] * df_cart["Qty"] / 100).sum())
            shipment = st.session_state.shipment_cost
            
            # Hàm Save (Giữ nguyên logic của bạn)
            def save_process(status_text=""):
                # ... (Code save cũ của bạn) ...
                pass

            # NÚT ĐIỀU KHIỂN
            col_save1, col_save2, col_save3, _ = st.columns([1.5, 1.5, 2, 5])
            
            if col_save1.button("Save Quotation", type="primary", use_container_width=True):
                save_process("")
            
            if col_save2.button("Print PDF", use_container_width=True):
                h_data = {
                    "Offer_No": offer_no, "Offer_Date": str(off_date),
                    "Customer_Name": selected_name, "Customer_No": c_no,
                    "Contact_Person": contact_person, "Machine_Number": machine_no
                }
                t_data = {'shipment': shipment, 'vat_total': total_vat}
                print_to_sample_sheet(h_data, edited_df, t_data)

            if st.session_state.editing_mode and col_save3.button("Confirmed Quotation", use_container_width=True):
                save_process("confirmed")
