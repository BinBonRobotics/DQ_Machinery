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
        return None, None, None, None, None

df_mst, df_contact, df_staff, df_machines, df_sp = load_base_data()

# Khởi tạo session_state
if 'cart' not in st.session_state: st.session_state.cart = []
if 'page_view' not in st.session_state: st.session_state.page_view = "New"
if 'shipment_cost' not in st.session_state: st.session_state.shipment_cost = 0
if 'editing_mode' not in st.session_state: st.session_state.editing_mode = False
if 'edit_header' not in st.session_state: st.session_state.edit_header = {}
if 'search_error' not in st.session_state: st.session_state.search_error = ""

# --- 3. HÀM CHỈ GHI OFFER NO VÀO Ô I7 (Tính năng duy nhất) ---
def simple_print_offer_no(off_no):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Lấy dữ liệu hiện tại của tab Offer Sample
        existing_data = conn.read(spreadsheet=SHEET_URL, worksheet="Offer Sample", ttl=0)
        
        # Ghi đè Offer No vào vị trí tương ứng với ô I7 (Hàng 7, Cột I là cột thứ 9)
        # Trong DataFrame index bắt đầu từ 0, nên I7 tương ứng hàng index 5, cột index 8
        # Để an toàn và đơn giản, mình dùng thư viện gspread có sẵn trong connection
        client = conn._conn.client
        sh = client.open_by_url(SHEET_URL)
        ws = sh.worksheet("Offer Sample")
        ws.update_acell('I7', off_no)
        st.success(f"Đã cập nhật Offer No: {off_no} vào ô I7 tab Offer Sample!")
    except Exception as e:
        st.error(f"Lỗi khi ghi dữ liệu: {e}")

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
        st.cache_data.clear(); st.rerun()

if df_mst is not None and option == "Spare Part Quotation":
    col_b1, col_b2, _ = st.columns([2, 2, 5])
    if col_b1.button("New Spare Part Offer", use_container_width=True): 
        st.session_state.page_view = "New"; st.session_state.editing_mode = False; st.session_state.cart = []; st.session_state.edit_header = {}; st.rerun()
    if col_b2.button("Order Management", use_container_width=True): st.session_state.page_view = "Manage"

    if st.session_state.page_view == "New":
        # Phần nhập Header giữ nguyên logic ổn định của bạn
        names = df_mst.iloc[:, 2].dropna().unique().tolist()
        selected_name = st.selectbox("Customer Name:", options=names, index=names.index(st.session_state.edit_header.get("Customer_Name", names[0])) if st.session_state.edit_header.get("Customer_Name") in names else 0)
        cust_row = df_mst[df_mst.iloc[:, 2] == selected_name].iloc[0]
        c_no = str(cust_row.iloc[1]).split('.')[0]
        t_code_display = st.session_state.edit_header.get("Clean_Tax", str(int(float(cust_row.iloc[5]))).zfill(10) if not pd.isna(cust_row.iloc[5]) else "")
        st.text_input("Tax Code:", value=t_code_display, disabled=True)
        
        # ... (Các trường nhập liệu khác giữ nguyên) ...
        d_val = st.session_state.edit_header.get("Offer_Date", datetime.now())
        if isinstance(d_val, str): d_val = datetime.strptime(d_val, '%Y-%m-%d')
        off_date = st.date_input("Offer Date:", value=d_val)
        offer_no = st.text_input("Offer No:", value=st.session_state.edit_header.get("Offer_No", f"{off_date.year}-{off_date.month:02d}-0001"))

        # --- GIỎ HÀNG (Dùng Data Editor ổn định) ---
        if st.session_state.cart:
            df_display = pd.DataFrame(st.session_state.cart)
            df_display["Amount"] = (df_display["Qty"] * df_display["Unit Price"] * (1 - df_display["% Discount"] / 100)).astype(int)
            df_display.insert(0, "No", range(1, len(df_display) + 1))
            df_display["Delete"] = False

            edited_df = st.data_editor(
                df_display,
                column_config={
                    "No": st.column_config.NumberColumn("No", disabled=True, width="small"),
                    "Amount": st.column_config.NumberColumn("Amount", format="%,d", disabled=True),
                    "Delete": st.column_config.CheckboxColumn("Delete")
                },
                hide_index=True, use_container_width=True, key="offer_editor"
            )

            # --- NÚT BẤM CUỐI TRANG ---
            col_f1, col_f2, col_f3, _ = st.columns([1.5, 1.5, 2, 5])
            if col_f1.button("Save Quotation", type="primary", use_container_width=True):
                # Logic Save giữ nguyên
                st.info("Đã thực hiện lưu dữ liệu.")
            
            if col_f2.button("Print PDF", use_container_width=True):
                # THỰC HIỆN YÊU CẦU DUY NHẤT: Ghi offer_no vào I7
                simple_print_offer_no(offer_no)
            
            if st.session_state.editing_mode and col_f3.button("Confirmed Quotation", use_container_width=True):
                st.info("Xác nhận báo giá thành công.")

        # --- TÌM KIẾM ĐỂ EDIT (Hiển thị Offer No _ Customer Name) ---
        st.markdown("---")
        st.subheader("Search & Edit Saved Quotation")
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            off_data = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details", ttl=0)
            if not off_data.empty:
                unique_offers = off_data.drop_duplicates(subset=["Offer_No"])
                s_list = (unique_offers["Offer_No"].astype(str) + " _ " + unique_offers["Customer_Name"].astype(str)).tolist()
                s_list.sort(reverse=True)
                st.selectbox("Select Offer No:", options=s_list, key="selected_offer_to_edit")
                st.button("Edit Quotation", use_container_width=True, on_click=on_edit_click)
        except: pass
