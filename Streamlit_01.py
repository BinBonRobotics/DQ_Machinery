import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime

# --- 1. CẤU HÌNH & KẾT NỐI ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

def clean_code(val):
    if pd.isna(val) or val == "": return ""
    # Loại bỏ khoảng trắng và ký tự đặc biệt để so sánh chính xác
    return re.sub(r'[^a-zA-Z0-9]', '', str(val)).strip().upper()

def format_vnd(value):
    try:
        return f"{int(round(float(value))):,}"
    except:
        return "0"

@st.cache_data(ttl=2)
def load_all_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_sp = conn.read(spreadsheet=SHEET_URL, worksheet="SP List")
        df_mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST")
        df_con = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact")
        df_mac = conn.read(spreadsheet=SHEET_URL, worksheet="List of machines")
        df_staff = conn.read(spreadsheet=SHEET_URL, worksheet="Staff")
        df_h_stored = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Header")
        df_d_stored = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details")
        
        # Đồng bộ Offer_No về dạng chuỗi
        for df in [df_h_stored, df_d_stored]:
            if df is not None and 'Offer_No' in df.columns:
                df['Offer_No'] = df['Offer_No'].astype(str).str.strip()
        return [df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored]
    except Exception as e:
        st.error(f"Lỗi kết nối dữ liệu: {e}")
        return [None] * 7

def update_sheet(worksheet_name, dataframe):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=dataframe)

def main():
    st.set_page_config(page_title="D&Q Machinery Management", layout="wide")
    
    # --- 1. SIDEBAR (Phần giữ nguyên) ---
    with st.sidebar:
        st.header("⚙️ Hệ thống")
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.write("---")
        menu_main = st.radio("Menu chính:", ["Báo Giá Phụ Tùng", "Báo Giá Dịch Vụ"])

    data_list = load_all_data()
    if data_list[0] is None: return
    df_sp, df_mst, df_con, df_mac, df_staff, df_h_stored, df_d_stored = data_list

    if menu_main == "Báo Giá Dịch Vụ":
        st.title("🛠️ Báo Giá Dịch Vụ")
        st.info("Tính năng đang phát triển...")
        return

    # --- 2. TAB BÁO GIÁ PHỤ TÙNG (Hai button thẳng hàng) ---
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "Tạo báo giá"

    c_nav1, c_nav2 = st.columns(2)
    with c_nav1:
        if st.button("➕ Tạo báo giá", use_container_width=True, type="primary" if st.session_state.current_tab == "Tạo báo giá" else "secondary"):
            st.session_state.current_tab = "Tạo báo giá"
            st.rerun()
    with c_nav2:
        if st.button("📋 Order Management", use_container_width=True, type="primary" if st.session_state.current_tab == "Order Management" else "secondary"):
            st.session_state.current_tab = "Order Management"
            st.rerun()

    st.write("---")

    # --- 3. CLICK BUTTON: TẠO BÁO GIÁ ---
    if st.session_state.current_tab == "Tạo báo giá":
        if 'cart' not in st.session_state: st.session_state.cart = []

        col_left, col_right = st.columns(2)
        
        # --- Bên tay trái ---
        with col_left:
            cust_list = sorted(df_mst['Customer name'].dropna().unique())
            cust_name = st.selectbox("🎯 Khách hàng:", options=cust_list)
            
            # Hiển thị Cust No và MST
            row_mst = df_mst[df_mst['Customer name'] == cust_name]
            cust_no = ""
            mst = ""
            if not row_mst.empty:
                cust_no = str(row_mst.iloc[0].get('Customer no', '')).split('.')[0]
                mst = row_mst.iloc[0].get('Mã số thuế', '-')
            st.write(f"**Cust No:** `{cust_no}` | **MST:** `{mst}`")
            
            mac_list = df_mac[df_mac['Customers'] == cust_name]['Machine No.'].dropna().unique()
            machine_no = st.selectbox("🤖 Machine Number:", options=list(mac_list) if len(mac_list)>0 else ["N/A"])

        # --- Bên tay phải ---
        with col_right:
            con_list = df_con[df_con['Customer name'] == cust_name]['Customer contact'].dropna().unique()
            contact_person = st.selectbox("👤 Contact Person:", options=list(con_list) if len(con_list)>0 else ["N/A"])
            
            # Lấy địa chỉ từ MST list
            address = row_mst.iloc[0].get('Address', '-') if not row_mst.empty else "-"
            st.text_input("📍 Địa chỉ:", value=address, disabled=True)
            
            off_date = st.date_input("📅 Offer Date:", value=datetime.now())
            off_no = st.text_input("🆔 Offer No:", value=f"OFF-{datetime.now().strftime('%Y%m%d%H%M')}")

        st.divider()

        # --- TÌM PART NUMBER & THÊM VÀO GIỎ ---
        col_search, _ = st.columns([2, 2])
        with col_search:
            search_pn = st.text_input("🔍 Nhập Part Number:")
            if st.button("🛒 Thêm vào giỏ hàng", use_container_width=True):
                if search_pn:
                    # Clean code cả 2 bên để tìm kiếm chính xác (Sửa lỗi mục B)
                    df_sp['clean_pn'] = df_sp['Part number'].apply(clean_code)
                    match = df_sp[df_sp['clean_pn'] == clean_code(search_pn)]
                    
                    if not match.empty:
                        item = match.iloc[0]
                        st.session_state.cart.append({
                            "Part_Number": str(item['Part number']),
                            "Part_Name": str(item['Part name']),
                            "Qty": 1.0,
                            "Unit": str(item['Unit']),
                            "VAT": 8,
                            "Unit Price": float(pd.to_numeric(item['Giá bán'], errors='coerce') or 0),
                            "%Dist": 0.0,
                            "Xoá": False
                        })
                        st.rerun()
                    else:
                        st.error("⚠️ Không tìm thấy Part Number trong hệ thống!")

        # --- BẢNG DANH SÁCH CHI TIẾT ---
        if st.session_state.cart:
            st.subheader("📋 Danh sách chi tiết")
            df_cart = pd.DataFrame(st.session_state.cart)
            df_cart.insert(0, "No", range(1, len(df_cart) + 1))
            
            # Tính Amount
            df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)
            
            # Cấu hình cột
            edited_df = st.data_editor(
                df_cart,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "No": st.column_config.NumberColumn(disabled=True),
                    "Part_Number": st.column_config.TextColumn(disabled=True),
                    "Part_Name": st.column_config.TextColumn(disabled=True),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(disabled=True, format="%d"),
                    "Unit Price": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
                    "Amount": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
                    "Qty": st.column_config.NumberColumn(min_value=0.1, step=0.1),
                    "%Dist": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=0.5),
                    "Xoá": st.column_config.CheckboxColumn()
                }
            )

            # Xử lý cập nhật Qty/%Dist hoặc Xoá dòng
            if not edited_df.equals(df_cart):
                # Nếu tích vào Xoá, lọc bỏ dòng đó
                st.session_state.cart = edited_df[~edited_df['Xoá']].drop(columns=['No', 'Amount']).to_dict('records')
                st.rerun()

            # --- TỔNG KẾT BÁO GIÁ (Table Table) ---
            st.divider()
            c_sum1, c_sum2 = st.columns([2, 2])
            with c_sum1:
                ship_cost_input = st.number_input("🚚 Nhập Shipment Cost (VND):", value=0, step=1000)
                if st.button("🗑️ Xoá hết hàng", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()

            with c_sum2:
                total_amt = edited_df['Amount'].sum()
                sub_total = total_amt + ship_cost_input
                vat_amt = sub_total * 0.08
                grand_total = sub_total + vat_amt

                summary_data = pd.DataFrame({
                    "Hạng mục": ["Total amount", "Shipment Cost", "Sub-Total", "VAT (8%)", "Grand Total"],
                    "Giá trị (VND)": [format_vnd(total_amt), format_vnd(ship_cost_input), format_vnd(sub_total), format_vnd(vat_amt), format_vnd(grand_total)]
                })
                st.table(summary_data)

            # --- LƯU BÁO GIÁ ---
            if st.button("💾 LƯU BÁO GIÁ", use_container_width=True, type="primary"):
                # Header Data
                new_h = pd.DataFrame([{
                    "Offer_No": off_no, "Date": off_date.strftime('%Y-%m-%d'), "Customer_Name": cust_name,
                    "Total_Amount": total_amt, "Shipment_Cost": ship_cost_input, "VAT_Amount": vat_amt,
                    "Grand_Total": grand_total, "Status": "Draft"
                }])
                # Details Data
                final_details = edited_df[~edited_df['Xoá']].drop(columns=['No', 'Amount', 'Xoá']).copy()
                final_details['Offer_No'] = off_no
                
                update_sheet("Offer_Header", pd.concat([df_h_stored, new_h], ignore_index=True))
                update_sheet("Offer_Details", pd.concat([df_d_stored, final_details], ignore_index=True))
                
                st.success(f"✅ Đã lưu báo giá {off_no} thành công!")
                st.session_state.cart = []
                st.cache_data.clear()
                st.rerun()

    # --- 4. ORDER MANAGEMENT ---
    elif st.session_state.current_tab == "Order Management":
        sub_tab = st.radio("Chế độ:", ["Quotation", "Offers_Tracking", "SP_Report"], horizontal=True)
        
        if sub_tab == "Quotation":
            st.subheader("📑 Danh sách báo giá đã lưu")
            st.dataframe(df_h_stored, use_container_width=True, hide_index=True)
            # Giữ nguyên code Edit như các phiên bản trước bạn đã ổn định
        else:
            st.info("🚧 Tính năng Coming Soon")

if __name__ == "__main__":
    main()
