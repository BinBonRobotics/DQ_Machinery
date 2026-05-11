import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import gspread # Thêm thư viện này để ghi ô cụ thể

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(layout="wide", page_title="Spare Part Quotation System")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8/edit#gid=903775380"

# --- 2. HÀM LOAD DỮ LIỆU (Giữ nguyên) ---
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

# --- 3. HÀM PRINT PDF ĐÃ SỬA LỖI (SỬ DỤNG GSPREAD) ---
def fixed_action_print_pdf(header_info, cart_items, shipment, vat_total):
    try:
        # Sử dụng connection hiện có để lấy thông tin xác thực
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Cách lấy client an toàn nhất hiện nay
        client = conn._instance._connector._client
        sh = client.open_by_url(SHEET_URL)
        ws = sh.worksheet("Offer Sample")
        
        # 1. Xóa vùng dữ liệu cũ (A18:J50)
        ws.batch_clear(["A18:J50", "V18:V50"])

        # 2. Ghi Header (Theo đúng ảnh yêu cầu của bạn)
        updates = [
            {'range': 'I7', 'values': [[header_info['Offer_No']]]},
            {'range': 'I5', 'values': [[header_info['Offer_Date']]]},
            {'range': 'I10', 'values': [[header_info['Customer_Name']]]},
            {'range': 'I11', 'values': [[header_info['Customer_No']]]},
            {'range': 'I12', 'values': [[header_info['Machine_Number']]]},
            {'range': 'B12', 'values': [[header_info['Contact_Person']]]},
            {'range': 'J26', 'values': [[shipment]]},
            {'range': 'J28', 'values': [[vat_total]]}
        ]
        
        # 3. Chuẩn bị bảng hàng hóa
        rows_goods = []
        rows_vat = []
        for i, item in enumerate(cart_items, 1):
            amount = int(item['Qty'] * item['Unit Price'] * (1 - item['% Discount'] / 100))
            # Cấu trúc: No(A), PartNo(B), PartName(C), Qty(D), Unit(E), [F trống], Price(G), %Disc(H), [I trống], Amount(J)
            rows_goods.append([
                i, item['Part Number'], item['Part Name'], item['Qty'], item['Unit'], 
                "", item['Unit Price'], item['% Discount'], "", amount
            ])
            rows_vat.append([item['VAT']]) # Cột V

        # Thực hiện update hàng loạt để tránh lỗi Quota 429
        if rows_goods:
            updates.append({'range': f'A18:J{17 + len(rows_goods)}', 'values': rows_goods})
            updates.append({'range': f'V18:V{17 + len(rows_vat)}', 'values': rows_vat})
            
        ws.batch_update(updates)
        st.success("✅ Đã ghi dữ liệu vào tab 'Offer Sample' thành công!")
        
    except Exception as e:
        # Nếu vẫn lỗi do phân quyền thư viện mới, dùng phương án dự phòng đơn giản nhất
        st.error(f"Lỗi: {e}. Thử lại hoặc kiểm tra quyền ghi của tài khoản Service Account.")

# --- 4. CÁC HÀM PHỤ TRỢ (Giữ nguyên tính năng cũ) ---
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
                "Customer_Name": first_row["Customer_Name"], "Contact_Person": first_row["Contact_Person"],
                "Officer": first_row["Officer"], "Machine_Number": first_row["Machine_Number"],
                "Offer_Date": str(first_row["Offer_Date"]), "Offer_No": first_row["Offer_No"],
                "Clean_Tax": str(first_row["Tax_Code"]).replace("'", "")
            }
            new_cart = []
            for _, r in edit_df.iterrows():
                new_cart.append({
                    "Part Number": str(r["Part_Number"]).split('.')[0], "Part Name": str(r["Part_Name"]),
                    "Qty": int(r["Qty"]), "Unit": str(r["Unit"]), "VAT": int(r["VAT_Rate"]),
                    "Unit Price": int(r["Unit_Price"]), "% Discount": int(float(r["Discount_Percent"]))
                })
            st.session_state.cart = new_cart
            st.session_state.shipment_cost = int(first_row["Shipment_Cost"])
            st.session_state.editing_mode = True
            st.session_state.page_view = "New"
    except Exception as e: st.error(f"Lỗi load Edit: {e}")

# --- 5. GIAO DIỆN ---
with st.sidebar:
    st.header("MENU")
    option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if df_mst is not None and option == "Spare Part Quotation":
    col_b1, col_b2, _ = st.columns([2, 2, 5])
    if col_b1.button("New Spare Part Offer", use_container_width=True): 
        st.session_state.page_view = "New"; st.session_state.editing_mode = False; st.session_state.cart = []; st.rerun()
    if col_b2.button("Order Management", use_container_width=True): st.session_state.page_view = "Manage"

    if st.session_state.page_view == "New":
        # (Phần Header: Customer Name, No, Tax Code... Giữ nguyên code cũ của bạn tại đây)
        # Giả sử các biến đã được gán: selected_name, c_no, t_code_display, contact_person, machine_no, off_date, offer_no...
        
        # --- PHẦN CART & NÚT BẤM ---
        # (Giữ nguyên code hiển thị Table và tính toán Total của bạn)
        
        # ĐOẠN CODE NÚT PRINT PDF MỚI:
        col_f1, col_f2, col_f3, _ = st.columns([1.5, 1.5, 2, 5])
        
        if col_f2.button("Print PDF", use_container_width=True):
            if not st.session_state.cart:
                st.warning("Giỏ hàng trống!")
            else:
                header_data = {
                    "Offer_No": offer_no, 
                    "Offer_Date": str(off_date), 
                    "Customer_Name": selected_name,
                    "Customer_No": c_no, 
                    "Contact_Person": contact_person, 
                    "Machine_Number": machine_no
                }
                # Tính toán lại VAT Total để truyền vào hàm
                total_amount = sum(int(i['Qty'] * i['Unit Price'] * (1 - i['% Discount'] / 100)) for i in st.session_state.cart)
                calc_vat = sum(int((i['VAT'] * (i['Qty'] * i['Unit Price'] * (1 - i['% Discount'] / 100))) / 100) for i in st.session_state.cart)
                
                fixed_action_print_pdf(header_data, st.session_state.cart, st.session_state.shipment_cost, calc_vat)

# (Các phần còn lại của code cũ giữ nguyên)
