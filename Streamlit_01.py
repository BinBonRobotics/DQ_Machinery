import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime

# --- CẤU HÌNH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

def clean_code(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).split('.')[0].strip()
    return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

@st.cache_data(ttl=60)
def load_all_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_sp = conn.read(spreadsheet=SHEET_URL, worksheet="SP List")
        df_mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST")
        df_con = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact")
        df_mac = conn.read(spreadsheet=SHEET_URL, worksheet="List of machines")
        df_staff = conn.read(spreadsheet=SHEET_URL, worksheet="Staff")
        # Load thêm 2 tab lưu trữ
        df_h_stored = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Header")
        df_d_stored = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details")
        return df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored
    except Exception as e:
        st.error(f"❌ Lỗi kết nối dữ liệu: {e}")
        return [None] * 7

def save_quotation(header_data, details_df):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # 1. Xử lý Header
        df_h = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Header").dropna(how='all')
        if header_data['Offer_No'] in df_h['Offer_No'].astype(str).values:
            df_h = df_h[df_h['Offer_No'].astype(str) != str(header_data['Offer_No'])]
        df_h = pd.concat([df_h, pd.DataFrame([header_data])], ignore_index=True)
        
        # 2. Xử lý Details
        df_d = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details").dropna(how='all')
        if header_data['Offer_No'] in df_d['Offer_No'].astype(str).values:
            df_d = df_d[df_d['Offer_No'].astype(str) != str(header_data['Offer_No'])]
        df_d = pd.concat([df_d, details_df], ignore_index=True)
        
        # 3. Ghi ngược lại Sheets
        conn.update(spreadsheet=SHEET_URL, worksheet="Offer_Header", data=df_h)
        conn.update(spreadsheet=SHEET_URL, worksheet="Offer_Details", data=df_d)
        return True
    except Exception as e:
        st.error(f"Lỗi khi lưu: {e}")
        return False

def main():
    st.set_page_config(page_title="D&Q Machinery", layout="wide")
    data = load_all_data()
    if data[0] is None: return
    df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored = data

    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'sub_action' not in st.session_state: st.session_state.sub_action = "create"
    if 'ship_cost' not in st.session_state: st.session_state.ship_cost = 0.0

    # --- 1. SIDEBAR ---
    st.sidebar.title("⚙️ Cấu hình")
    ty_gia = st.sidebar.number_input("Tỷ giá Euro (VND):", value=31000, step=100)
    if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.sidebar.radio("📂 Danh mục:", ["📄 Báo Giá Phụ Tùng"])

    # --- 2. ĐIỀU HƯỚNG ---
    col_btn1, col_btn2, _ = st.columns([1.5, 2, 3])
    if col_btn1.button("➕ Tạo Báo Giá", use_container_width=True, type="primary" if st.session_state.sub_action=="create" else "secondary"):
        st.session_state.sub_action = "create"
    if col_btn2.button("🔍 Order Management", use_container_width=True, type="primary" if st.session_state.sub_action=="search" else "secondary"):
        st.session_state.sub_action = "search"
    st.divider()

    # --- 3. TRANG TẠO BÁO GIÁ ---
    if st.session_state.sub_action == "create":
        # Row 1: Thông tin khách hàng
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            cust_name = st.selectbox("🎯 Khách hàng:", options=sorted(df_mst['Customer name'].dropna().unique()))
            row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
            c_no = str(row_mst.get('Customer no', row_mst.get('Customer\nno', ''))).split('.')[0]
            mst_val = row_mst.get('Mã số thuế', '-')
            st.info(f"**Cust No:** {c_no} | **MST:** {mst_val}")
        with r1c2:
            f_conts = df_con[df_con.iloc[:, 1].astype(str).str.contains(clean_code(c_no))] if df_con is not None else pd.DataFrame()
            list_conts = f_conts.iloc[:, 7].dropna().unique().tolist() if not f_conts.empty else []
            contact_person = st.selectbox("👤 Contact Person:", options=list_conts if list_conts else ["N/A"])
            addr_val = str(row_mst.get('Địa chỉ', '-'))
            st.markdown(f"📍 **Địa chỉ:** {addr_val}")

        # Row 2: Máy móc & Số báo giá
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        with r2c1:
            f_macs = df_mac[df_mac.iloc[:, 1].astype(str).str.contains(clean_code(c_no))] if df_mac is not None else pd.DataFrame()
            list_macs = f_macs.iloc[:, 14].dropna().unique().tolist() if not f_macs.empty else []
            machine_no = st.selectbox("🤖 Machine Number:", options=list_macs if list_macs else ["N/A"])
        with r2c2:
            list_staff = df_staff['Name'].dropna().unique().tolist() if 'Name' in df_staff.columns else ["Admin"]
            staff_name = st.selectbox("✍️ Người lập:", options=list_staff)
        with r2c3:
            offer_date = st.date_input("📅 Offer Date:", value=datetime.now())
        with r2c4:
            offer_no = st.text_input("🆔 Offer No:", value=f"{offer_date.year}-{offer_date.month:02d}-0001")

        st.subheader("🔍 Tìm Part Number")
        input_search = st.text_input("Nhập mã (cách nhau bởi dấu ;):")
        if st.button("🛒 Thêm vào giỏ hàng", type="primary") and input_search:
            codes = [clean_code(c) for c in input_search.split(';') if c.strip()]
            df_sp['CLEAN_PN'] = df_sp['Part number'].apply(clean_code)
            for code in codes:
                match = df_sp[df_sp['CLEAN_PN'] == code]
                if not match.empty:
                    item = match.iloc[0]
                    st.session_state.cart.append({
                        "Part Number": item['Part number'], "Part Name": item['Part name'],
                        "Qty": 1, "Unit": item['Unit'], "VAT": 8,
                        "Unit Price": float(item.get('Giá bán', 0)), "%Dist": 0.0, "Xoá": False
                    })
            st.rerun()

        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            df_cart.insert(0, 'No', range(1, len(df_cart) + 1))
            df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)
            
            edited_df = st.data_editor(df_cart, column_config={
                "No": st.column_config.NumberColumn(disabled=True),
                "Part Number": st.column_config.TextColumn(disabled=True),
                "Part Name": st.column_config.TextColumn(disabled=True),
                "Unit": st.column_config.TextColumn(disabled=True),
                "VAT": st.column_config.NumberColumn(format="%d", disabled=True),
                "Unit Price": st.column_config.NumberColumn(format="%,d", disabled=True),
                "Amount": st.column_config.NumberColumn(format="%,d", disabled=True),
                "Xoá": st.column_config.CheckboxColumn()
            }, use_container_width=True, hide_index=True)

            if st.button("🗑️ Xoá hết hàng"):
                st.session_state.cart = []; st.rerun()

            # Tính toán tổng
            total_amt = edited_df['Amount'].sum()
            ship_val = st.number_input("Shipment Cost (VND):", value=float(st.session_state.ship_cost))
            st.session_state.ship_cost = ship_val
            sub_total = total_amt + ship_val
            vat_amt = sub_total * 0.08
            grand_total = sub_total + vat_amt

            st.table(pd.DataFrame({
                "Nội dung": ["Total Amount", "Shipment Cost", "Sub-Total", "VAT (8%)", "Grand Total"],
                "Số tiền": [f"{total_amt:,.0f}", f"{ship_val:,.0f}", f"{sub_total:,.0f}", f"{vat_amt:,.0f}", f"{grand_total:,.0f}"]
            }))

            if st.button("💾 Lưu Báo Giá", use_container_width=True, type="primary"):
                h_data = {
                    "Offer_No": offer_no, "Offer_Date": offer_date.strftime("%Y-%m-%d"),
                    "Customer_Name": cust_name, "Cust_No": c_no, "VAT_Code": mst_val,
                    "Address": addr_val, "Contact_Person": contact_person, "Machine_No": machine_no,
                    "Staff": staff_name, "Total_Amount": total_amt, "Shipment_Cost": ship_val,
                    "VAT_Amount": vat_amt, "Grand_Total": grand_total
                }
                d_df = edited_df[["Part Number", "Part Name", "Qty", "Unit", "Unit Price", "VAT", "%Dist", "Amount"]].copy()
                d_df.columns = ["Part_Number", "Part_Name", "Qty", "Unit", "Unit_Price", "VAT_Rate", "Discount_Percent", "Amount"]
                d_df.insert(0, "Offer_No", offer_no)
                
                if save_quotation(h_data, d_df):
                    st.success(f"✅ Đã lưu/cập nhật báo giá {offer_no} thành công!")
                    st.cache_data.clear()

    # --- 4. ORDER MANAGEMENT ---
    elif st.session_state.sub_action == "search":
        tab_q, tab_t, tab_r = st.tabs(["📄 Quotations", "🚚 Offers_Tracking", "📊 SP_Report"])
        with tab_q:
            st.subheader("Danh sách báo giá đã lưu")
            if not df_h_stored.empty:
                st.dataframe(df_h_stored, use_container_width=True, hide_index=True)
                sel_offer = st.selectbox("Chọn Offer No để xem chi tiết:", options=df_h_stored['Offer_No'].unique())
                if sel_offer:
                    details = df_d_stored[df_d_stored['Offer_No'].astype(str) == str(sel_offer)]
                    st.table(details)
            else:
                st.info("Chưa có báo giá nào được lưu.")

if __name__ == "__main__":
    main()
