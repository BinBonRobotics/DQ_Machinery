import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime

# --- CẤU HÌNH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

def clean_code(val):
    if pd.isna(val) or val == "": return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(val)).strip().upper()

def format_vnd(value):
    try:
        return f"{int(round(float(value))):,}"
    except:
        return "0"

@st.cache_data(ttl=2)
def load_all_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_sp = conn.read(spreadsheet=SHEET_URL, worksheet="SP List")
    df_mst = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_MST")
    df_con = conn.read(spreadsheet=SHEET_URL, worksheet="Customer_Contact")
    df_mac = conn.read(spreadsheet=SHEET_URL, worksheet="List of machines")
    df_h_stored = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Header")
    df_d_stored = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details")
    return [df_sp, df_mst, df_con, df_mac, df_h_stored, df_d_stored]

def update_sheet(worksheet_name, dataframe):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=dataframe)

def main():
    st.set_page_config(page_title="D&Q Management", layout="wide")
    
    # 1. SIDEBAR
    with st.sidebar:
        st.header("⚙️ Hệ thống")
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.write("---")
        menu_main = st.radio("Menu chính:", ["Báo Giá Phụ Tùng", "Báo Giá Dịch Vụ"])

    if menu_main == "Báo Giá Dịch Vụ":
        st.title("🛠️ Báo Giá Dịch Vụ (Soon)")
        return

    data = load_all_data()
    df_sp, df_mst, df_con, df_mac, df_h_stored, df_d_stored = data

    # 2. NAVIGATION BUTTONS
    if 'tab' not in st.session_state: st.session_state.tab = "create"
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ Tạo báo giá", use_container_width=True, type="primary" if st.session_state.tab=="create" else "secondary"):
            st.session_state.tab = "create"
    with c2:
        if st.button("📋 Order Management", use_container_width=True, type="primary" if st.session_state.tab=="manage" else "secondary"):
            st.session_state.tab = "manage"

    # 3. NỘI DUNG TẠO BÁO GIÁ
    if st.session_state.tab == "create":
        if 'cart' not in st.session_state: st.session_state.cart = []
        
        col_l, col_r = st.columns(2)
        with col_l:
            cust_name = st.selectbox("🎯 Khách hàng:", options=sorted(df_mst['Customer name'].dropna().unique()))
            row_m = df_mst[df_mst['Customer name'] == cust_name]
            c_no = str(row_m.iloc[0]['Customer no']) if not row_m.empty else ""
            m_thue = str(row_m.iloc[0]['Mã số thuế']) if not row_m.empty else ""
            st.markdown(f"**Cust No:** `{c_no}` | **MST:** `{m_thue}`")
            
            m_list = df_mac[df_mac['Customers'] == cust_name]['Machine No.'].dropna().unique()
            mac_no = st.selectbox("🤖 Machine Number:", options=list(m_list) if len(m_list)>0 else ["N/A"])

        with col_r:
            contact_list = df_con[df_con['Customer name'] == cust_name]['Customer contact'].dropna().unique()
            contact = st.selectbox("👤 Contact Person:", options=list(contact_list) if len(contact_list)>0 else ["N/A"])
            addr = row_m.iloc[0]['Address'] if not row_m.empty else "-"
            st.text_input("📍 Địa chỉ:", value=addr, disabled=True)
            off_date = st.date_input("📅 Offer Date:", value=datetime.now())
            off_no = st.text_input("🆔 Offer No:", value=f"OFF-{datetime.now().strftime('%Y%m%d%H%M')}")

        st.divider()
        
        # TÌM PART
        s_col, _ = st.columns([2, 2])
        with s_col:
            search_input = st.text_input("🔍 Nhập Part Number:")
            if st.button("🛒 Thêm vào giỏ hàng", use_container_width=True):
                if search_input:
                    df_sp['clean'] = df_sp['Part number'].apply(clean_code)
                    match = df_sp[df_sp['clean'] == clean_code(search_input)]
                    if not match.empty:
                        item = match.iloc[0]
                        st.session_state.cart.append({
                            "Part_Number": str(item['Part number']),
                            "Part_Name": str(item['Part name']),
                            "Qty": 1, "Unit": str(item['Unit']), "VAT": 8,
                            "Unit_Price": float(item['Giá bán'] or 0), "%Dist": 0, "Xoá": False
                        })
                    else:
                        st.error("❌ Không tìm thấy Part Number!")

        # BẢNG CHI TIẾT
        if st.session_state.cart:
            st.subheader("📋 Danh sách chi tiết")
            df_cart = pd.DataFrame(st.session_state.cart)
            df_cart.insert(0, "No", range(1, len(df_cart) + 1))
            
            # Tính Amount hiển thị
            df_cart['Amount'] = df_cart['Unit_Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)

            edited_df = st.data_editor(
                df_cart, use_container_width=True, hide_index=True,
                column_config={
                    "No": st.column_config.NumberColumn(disabled=True),
                    "Part_Number": st.column_config.TextColumn(disabled=True),
                    "Part_Name": st.column_config.TextColumn(disabled=True),
                    "Unit": st.column_config.TextColumn(disabled=True),
                    "VAT": st.column_config.NumberColumn(disabled=True, format="%d"),
                    "Unit_Price": st.column_config.NumberColumn("Unit Price", disabled=True, format="%,.0f"),
                    "Amount": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
                    "Qty": st.column_config.NumberColumn(min_value=1),
                    "%Dist": st.column_config.NumberColumn(min_value=0, max_value=100)
                }
            )

            # Xử lý nút xóa và cập nhật session_state (Fix lỗi TypeError)
            if not edited_df.equals(df_cart):
                st.session_state.cart = edited_df[edited_df['Xoá'] == False].drop(columns=['No', 'Amount']).to_dict('records')
                st.rerun()

            # TỔNG KẾT
            st.divider()
            sum_l, sum_r = st.columns(2)
            with sum_l:
                ship_cost = st.number_input("🚚 Shipment Cost (VND):", value=0, step=1000)
                if st.button("🗑️ Xoá hết hàng"):
                    st.session_state.cart = []
                    st.rerun()
            
            with sum_r:
                total_amt = edited_df['Amount'].sum()
                sub_total = total_amt + ship_cost
                vat_val = sub_total * 0.08
                grand_total = sub_total + vat_val
                
                sum_df = pd.DataFrame({
                    "Nội dung": ["Total Amount", "Shipment Cost", "Sub-Total", "VAT (8%)", "GRAND TOTAL"],
                    "Số tiền (VND)": [format_vnd(total_amt), format_vnd(ship_cost), format_vnd(sub_total), format_vnd(vat_val), format_vnd(grand_total)]
                })
                st.table(sum_df)

            if st.button("💾 LƯU BÁO GIÁ", use_container_width=True, type="primary"):
                # Lưu Header
                new_h = pd.DataFrame([{"Offer_No": off_no, "Date": off_date, "Customer": cust_name, "Grand_Total": grand_total}])
                update_sheet("Offer_Header", pd.concat([df_h_stored, new_h]))
                # Lưu Detail
                det_to_save = edited_df.drop(columns=['No', 'Amount', 'Xoá'])
                det_to_save['Offer_No'] = off_no
                update_sheet("Offer_Details", pd.concat([df_d_stored, det_to_save]))
                
                st.success("Đã lưu thành công!")
                st.session_state.cart = []
                st.rerun()

    # 4. ORDER MANAGEMENT
    else:
        st.title("📂 Order Management")
        sub = st.tabs(["Quotation", "Offers_Tracking", "SP_Report"])
        with sub[0]:
            st.dataframe(df_h_stored, use_container_width=True)
        with sub[1]: st.write("Coming soon...")
        with sub[2]: st.write("Coming soon...")

if __name__ == "__main__":
    main()
