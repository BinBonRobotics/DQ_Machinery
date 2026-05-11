import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import json

# --- 1. CẤU HÌNH TRANG (Giữ nguyên) ---
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
        return None, None, None, None, None

df_mst, df_contact, df_staff, df_machines, df_sp = load_base_data()

# Khởi tạo session_state (Giữ nguyên)
if 'cart' not in st.session_state: st.session_state.cart = []
if 'page_view' not in st.session_state: st.session_state.page_view = "New"
if 'shipment_cost' not in st.session_state: st.session_state.shipment_cost = 0
if 'editing_mode' not in st.session_state: st.session_state.editing_mode = False
if 'edit_header' not in st.session_state: st.session_state.edit_header = {}

# --- 3. HÀM PRINT PDF ĐÃ FIX TRIỆT ĐỂ LỖI _CONNECTOR ---
def safe_print_pdf(off_no):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Tạo DataFrame chứa duy nhất 1 giá trị là offer_no
        # Để ghi vào ô I7, ta sẽ chỉ định phạm vi (range) là I7 trong lệnh update
        df_update = pd.DataFrame([[off_no]])
        
        conn.update(
            spreadsheet=SHEET_URL,
            worksheet="Offer Sample",
            data=df_update,
            range="I7"  # Chỉ định ghi đúng vào vị trí I7
        )
        st.success(f"✅ Đã ghi Offer No: {off_no} vào ô I7 tab Offer Sample!")
    except Exception as e:
        st.error(f"❌ Lỗi ghi dữ liệu: {e}")
        st.info("Mẹo: Nếu lỗi Quota (429), hãy đợi 30 giây rồi nhấn lại.")

# --- 4. GIAO DIỆN VÀ LOGIC (Giữ nguyên cấu trúc chuẩn của bạn) ---
# ... (Giữ nguyên phần Sidebar và logic chọn khách hàng của bạn) ...

if df_mst is not None and st.session_state.page_view == "New":
    # Giả sử các biến header của bạn đã được định nghĩa bên trên (offer_no, selected_name...)
    # ... (Giữ nguyên phần hiển thị thông tin khách hàng) ...

    # Giả sử đây là phần hiển thị giỏ hàng và các nút bấm cuối trang của bạn
    if st.session_state.cart:
        # ... (Giữ nguyên phần st.data_editor và Summary Table) ...

        col_f1, col_f2, col_f3, _ = st.columns([1.5, 1.5, 2, 5])
        
        # Nút Save (Giữ nguyên code của bạn)
        if col_f1.button("Save Quotation", type="primary", use_container_width=True):
            pass # Thay bằng hàm save_final của bạn
            
        # Nút Print PDF - ĐÃ FIX
        if col_f2.button("Print PDF", use_container_width=True):
            # Gọi hàm safe_print_pdf với biến offer_no lấy từ text_input bên trên
            # Đảm bảo biến offer_no đã được định nghĩa ở phần Header
            safe_print_pdf(st.session_state.get('offer_no_input', offer_no))
            
        # Nút Confirm (Giữ nguyên code của bạn)
        if st.session_state.editing_mode and col_f3.button("Confirmed Quotation", use_container_width=True):
            pass # Thay bằng hàm save_final("confirmed") của bạn

# --- 5. SEARCH & EDIT (Giữ nguyên) ---
# ... (Giữ nguyên phần cuối code của bạn) ...
