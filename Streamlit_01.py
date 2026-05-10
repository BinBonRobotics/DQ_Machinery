import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(layout="wide", page_title="Spare Part Quotation System")

# URL Google Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8/edit#gid=903775380"

# --- 2. HÀM LOAD DỮ LIỆU ---
@st.cache_data(ttl=60)
def load_data():
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

df_mst, df_contact, df_staff, df_machines, df_sp = load_data()

# Khởi tạo trạng thái
if 'cart' not in st.session_state: st.session_state.cart = []
if 'page_view' not in st.session_state: st.session_state.page_view = "New"
if 'search_error' not in st.session_state: st.session_state.search_error = ""
if 'shipment_cost' not in st.session_state: st.session_state.shipment_cost = 0

# --- 3. SIDE MENU ---
with st.sidebar:
    st.header("MENU")
    option = st.radio("Lựa chọn:", ["Spare Part Quotation", "Service Quotation"])
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 4. CHỨC NĂNG CHÍNH ---
if df_mst is not None and option == "Spare Part Quotation":
    col_b1, col_b2, _ = st.columns([2, 2, 5])
    if col_b1.button("New Spare Part Offer", use_container_width=True): st.session_state.page_view = "New"
    if col_b2.button("Order Management", use_container_width=True): st.session_state.page_view = "Manage"

    if st.session_state.page_view == "New":
        st.markdown("### New Spare Part Offer")
        
        # --- OFFER HEADER ---
        names = df_mst.iloc[:, 2].dropna().unique().tolist()
        selected_name = st.selectbox("Customer Name:", options=names)
        cust_row = df_mst[df_mst.iloc[:, 2] == selected_name].iloc[0]
        
        # Customer No
        c_no = str(cust_row.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=c_no, disabled=True)
        
        # --- FIX TAX CODE: Hiển thị đúng định dạng chuỗi số ---
        t_val = cust_row.iloc[5]
        if pd.isna(t_val):
            t_code_display = ""
        else:
            # Chuyển sang string và loại bỏ phần thập phân .0 nếu có
            t_code_display = "{:.0f}".format(t_val) if isinstance(t_val, (int, float)) else str(t_val)
        st.text_input("Tax Code:", value=t_code_display, disabled=True)
        
        st.text_area("Address:", value=str(cust_row.iloc[4]) if not pd.isna(cust_row.iloc[4]) else "", height=70, disabled=True)
        
        f_contact = df_contact[df_contact.iloc[:, 1].astype(str).str.contains(c_no)]
        contact_list = f_contact.iloc[:, 7].dropna().tolist() if not f_contact.empty else ["N/A"]
        st.selectbox("Contact Person:", options=contact_list)
        
        st.selectbox("Officer:", options=df_staff.iloc[:, 1].dropna().tolist())
        
        f_machines = df_machines[df_machines.iloc[:, 1].astype(str).str.contains(c_no)]
        machine_list = f_machines.iloc[:, 14].dropna().tolist() if not f_machines.empty else ["N/A"]
        st.selectbox("Machine Number:", options=machine_list)
        
        off_date = st.date_input("Offer Date:", value=datetime.now())
        st.text_input("Offer No:", value=f"{off_date.year}-{off_date.month:02d}-0001")

        st.markdown("---")
        st.subheader("Offer Descriptions")

        # --- Ô TÌM KIẾM ---
        search_input = st.text_input("Search Part Number:", placeholder="2024956492;2031956280")
        
        if st.session_state.search_error:
            st.error(st.session_state.search_error)

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
                        try:
                            display_vat = int(float(raw_vat) * 100) if float(raw_vat) < 1 else int(float(raw_vat))
                        except: display_vat = 0
                        
                        st.session_state.cart.append({
                            "Part Number": str(item.iloc[1]),
                            "Part Nname": str(item.iloc[4]),
                            "Qty": 1,
                            "Unit": str(item.iloc[7]),
                            "VAT": display_vat,
                            "Unit Price": int(float(item.iloc[18])) if not pd.isna(item.iloc[18]) else 0,
                            "% Distcount": 0
                        })
                    else:
                        not_found.append(code)
                
                st.session_state.search_error = f"Part Number {', '.join(not_found)} is not available" if not_found else ""
                st.rerun()

        if col_act2.button("Delete Cart", use_container_width=True):
            st.session_state.cart = []
            st.session_state.search_error = ""
            st.session_state.shipment_cost = 0
            st.rerun()

        # --- BẢNG DANH SÁCH LINH KIỆN ---
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            # Tính Amount và ép kiểu Int để hiện dấu phẩy chuẩn
            df_cart["Amount"] = (df_cart["Qty"] * df_cart["Unit Price"] * (1 - df_cart["% Distcount"] / 100)).astype(int)
            df_cart["Unit Price"] = df_cart["Unit Price"].astype(int)
            
            df_cart.insert(0, "No", range(1, len(df_cart) + 1))
            df_cart["Xóa dòng"] = False

            # Dùng format="%d" kết hợp với kiểu dữ liệu int sẽ tự động có dấu phẩy phân cách
            edited_df = st.data_editor(
                df_cart,
                column_config={
                    "No": st.column_config.NumberColumn(disabled=True),
                    "Part Number": st.column_config.TextColumn(disabled=True),
                    "Part Nname": st.column_config.TextColumn(disabled=True),
                    "Qty": st.column_config.NumberColumn(min_value=1),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(format="%d", disabled=True), 
                    "Unit Price": st.column_config.NumberColumn(format="%d", disabled=True),
                    "% Distcount": st.column_config.NumberColumn(min_value=0, max_value=100, format="%d%%"),
                    "Amount": st.column_config.NumberColumn(format="%d", disabled=True),
                    "Xóa dòng": st.column_config.CheckboxColumn()
                },
                hide_index=True,
                use_container_width=True,
                key="editor"
            )

            if not edited_df.equals(df_cart):
                new_cart = edited_df[edited_df["Xóa dòng"] == False].drop(columns=["No", "Amount", "Xóa dòng"]).to_dict('records')
                st.session_state.cart = new_cart
                st.rerun()

            # --- TỔNG KẾT CHI PHÍ ---
            st.markdown("---")
            col_sum1, col_sum2 = st.columns([6, 4])
            
            with col_sum2:
                total_amount = int(df_cart["Amount"].sum())
                total_vat = int((df_cart["VAT"] * df_cart["Unit Price"] * df_cart["Qty"] / 100).sum())
                
                shipment = st.number_input("Shipment Cost:", min_value=0, value=int(st.session_state.shipment_cost), step=1000, format="%d")
                st.session_state.shipment_cost = shipment
                
                sub_total = total_amount + shipment
                grand_total = sub_total + total_vat

                summary_data = {
                    "Description": ["Total Amount", "Shipment Cost", "Sub-Total", "VAT", "Grand Total"],
                    "Value": [total_amount, shipment, sub_total, total_vat, grand_total]
                }
                df_summary = pd.DataFrame(summary_data)
                # Format hiển thị bảng tổng kết có dấu phẩy
                st.table(df_summary.style.format({"Value": "{:,.0f}"}))

    elif st.session_state.page_view == "Manage":
        st.info("Trang Order Management")
