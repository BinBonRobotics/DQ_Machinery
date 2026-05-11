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
        
        c_no = str(cust_row.iloc[1]).split('.')[0]
        st.text_input("Customer No:", value=c_no, disabled=True)
        
        # Tax Code hiển thị 10 chữ số
        t_val = cust_row.iloc[5]
        if pd.isna(t_val):
            t_code_display = ""
        else:
            try:
                t_code_display = str(int(float(t_val))).zfill(10)
            except:
                t_code_display = str(t_val).split('.')[0].zfill(10)
        
        st.text_input("Tax Code:", value=t_code_display, disabled=True)
        
        addr = str(cust_row.iloc[4]) if not pd.isna(cust_row.iloc[4]) else ""
        st.text_area("Address:", value=addr, height=70, disabled=True)
        
        f_contact = df_contact[df_contact.iloc[:, 1].astype(str).str.contains(c_no)]
        contact_list = f_contact.iloc[:, 7].dropna().tolist() if not f_contact.empty else ["N/A"]
        contact_person = st.selectbox("Contact Person:", options=contact_list)
        
        officer = st.selectbox("Officer:", options=df_staff.iloc[:, 1].dropna().tolist())
        
        f_machines = df_machines[df_machines.iloc[:, 1].astype(str).str.contains(c_no)]
        machine_list = f_machines.iloc[:, 14].dropna().tolist() if not f_machines.empty else ["N/A"]
        machine_no = st.selectbox("Machine Number:", options=machine_list)
        
        off_date = st.date_input("Offer Date:", value=datetime.now())
        offer_no = st.text_input("Offer No:", value=f"{off_date.year}-{off_date.month:02d}-0001")

        st.markdown("---")
        st.subheader("Offer Descriptions")

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
                            "Part Name": str(item.iloc[4]),
                            "Qty": 1,
                            "Unit": str(item.iloc[7]),
                            "VAT": display_vat,
                            "Unit Price": int(float(item.iloc[18])) if not pd.isna(item.iloc[18]) else 0,
                            "% Discount": 0
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

        # --- BẢNG GIỎ HÀNG ---
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
                new_cart = edited_df[edited_df["Xóa dòng"] == False].drop(columns=["No", "Amount", "Xóa dòng"]).to_dict('records')
                st.session_state.cart = new_cart
                st.rerun()

            # --- TỔNG KẾT ---
            st.markdown("---")
            col_sum1, col_sum2 = st.columns([6, 4])
            with col_sum2:
                total_amount = int(df_cart["Amount"].sum())
                total_vat = int((df_cart["VAT"] * df_cart["Unit Price"] * df_cart["Qty"] / 100).sum())
                shipment = st.number_input("Shipment Cost:", min_value=0, value=int(st.session_state.shipment_cost))
                st.session_state.shipment_cost = shipment
                sub_total = total_amount + shipment
                grand_total = sub_total + total_vat

                df_summary = pd.DataFrame({
                    "Description": ["Total Amount", "Shipment Cost", "Sub-Total", "VAT Total", "Grand Total"],
                    "Value": [total_amount, shipment, sub_total, total_vat, grand_total]
                })
                st.table(df_summary.style.format({"Value": "{:,.0f}"}))

            # --- LƯU DỮ LIỆU ---
            col_save1, col_save2, _ = st.columns([1.5, 1.5, 7])
            if col_save1.button("Save Quotation", type="primary", use_container_width=True):
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    new_rows = []
                    for idx, row in edited_df[edited_df["Xóa dòng"] == False].iterrows():
                        new_rows.append({
                            "Offer_No": str(offer_no),
                            "Offer_Date": str(off_date),
                            "Customer_Name": selected_name,
                            "Customer_No": str(c_no),
                            "Tax_Code": t_code_display, # Đã loại bỏ dấu '
                            "Address": addr,
                            "Contact_Person": contact_person,
                            "Officer": officer,
                            "Machine_Number": machine_no,
                            "Ordinal_Number": row["No"],
                            "Part_Number": row["Part Number"],
                            "Part_Name": row["Part Name"],
                            "Qty": row["Qty"],
                            "Unit": row["Unit"],
                            "VAT_Rate": row["VAT"],
                            "Unit_Price": row["Unit Price"],
                            "Discount_Percent": row["% Discount"],
                            "Amount": row["Amount"],
                            "Total_Amount": total_amount,
                            "Shipment_Cost": shipment,
                            "Sub_Total": sub_total,
                            "VAT_Total": total_vat,
                            "Grand_Total": grand_total
                        })
                    
                    df_to_save = pd.DataFrame(new_rows)
                    
                    # Đảm bảo Tax_Code lưu dưới dạng string để giữ số 0
                    df_to_save["Tax_Code"] = df_to_save["Tax_Code"].astype(str)

                    try:
                        existing_data = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details")
                        if "Tax_Code" in existing_data.columns:
                            existing_data["Tax_Code"] = existing_data["Tax_Code"].astype(str)
                        updated_df = pd.concat([existing_data, df_to_save], ignore_index=True)
                    except:
                        updated_df = df_to_save

                    conn.update(spreadsheet=SHEET_URL, worksheet="Offer_Details", data=updated_df)
                    st.success(f"Quotation {offer_no} saved successfully!")
                    
                    # RESET GIỎ HÀNG SAU KHI LƯU
                    st.session_state.cart = []
                    st.session_state.shipment_cost = 0
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")

            if col_save2.button("Print PDF", use_container_width=True):
                st.info("Feature Coming Soon")

    elif st.session_state.page_view == "Manage":
        st.info("Order Management Page")
