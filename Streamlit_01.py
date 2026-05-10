import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime

# --- 1. HÀM TRỢ GIÚP ---
def clean_code(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).split('.')[0].strip()
    return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

def format_vnd(amount):
    return f"{amount:,.0f} VND"

# --- 2. KẾT NỐI & TẢI DỮ LIỆU ---
@st.cache_data(ttl=60)
def load_all_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
        
        # Đọc tất cả các worksheet cần thiết
        df_sp = conn.read(spreadsheet=url, worksheet="SP List")
        df_mst = conn.read(spreadsheet=url, worksheet="Customer_MST")
        df_con = conn.read(spreadsheet=url, worksheet="Customer_Contact")
        df_mac = conn.read(spreadsheet=url, worksheet="List of machines")
        df_staff = conn.read(spreadsheet=url, worksheet="Staff")
        
        return df_sp, df_mst, df_con, df_mac, df_staff
    except Exception as e:
        st.error(f"❌ Lỗi kết nối dữ liệu: {e}")
        return [None] * 5

# --- 3. HÀM LƯU BÁO GIÁ (GHI VÀO GSHEETS) ---
def save_quotation(header_data, details_df):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
        
        # 1. Lưu vào Offer_Header
        df_header_old = conn.read(spreadsheet=url, worksheet="Offer_Header")
        df_header_new = pd.concat([df_header_old, pd.DataFrame([header_data])], ignore_index=True)
        conn.update(spreadsheet=url, worksheet="Offer_Header", data=df_header_new)
        
        # 2. Lưu vào Offer_Details
        df_details_old = conn.read(spreadsheet=url, worksheet="Offer_Details")
        # Chuẩn bị dữ liệu chi tiết với ID báo giá chung
        details_df['Offer_No'] = header_data['Offer_No']
        df_details_new = pd.concat([df_details_old, details_df], ignore_index=True)
        conn.update(spreadsheet=url, worksheet="Offer_Details", data=df_details_new)
        
        return True
    except Exception as e:
        st.error(f"❌ Lỗi khi lưu: {e}")
        return False

# --- 4. GIAO DIỆN CHÍNH ---
def main():
    st.set_page_config(page_title="D&Q Machinery System", layout="wide", page_icon="⚙️")
    
    # Load data
    df_sp, df_mst, df_con, df_mac, df_staff = load_all_data()
    if df_mst is None: 
        st.warning("Không thể tải dữ liệu. Vui lòng kiểm tra kết nối Google Sheets.")
        return

    # Khởi tạo Session State
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'sub_action' not in st.session_state: st.session_state.sub_action = "create"
    if 'ship_cost' not in st.session_state: st.session_state.ship_cost = 0.0
    if 'last_not_found' not in st.session_state: st.session_state.last_not_found = []

    # --- SIDEBAR ---
    st.sidebar.image("https://www.homag.com/fileadmin/user_upload/Logo/HOMAG_Logo_Blue_RGB.png", width=200) # Ví dụ logo
    st.sidebar.title("⚙️ HỆ THỐNG QUẢN LÝ")
    ty_gia = st.sidebar.number_input("Tỷ giá Euro (VND):", value=31000, step=100)
    
    if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    menu = st.sidebar.radio("📂 Danh mục:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data", "📊 Báo cáo Doanh số"])

    if menu == "📄 Báo Giá Phụ Tùng":
        # Nút điều hướng nhanh
        col_btn1, col_btn2, _ = st.columns([1.5, 2, 3])
        if col_btn1.button("➕ Tạo Báo Giá Mới", use_container_width=True, type="primary" if st.session_state.sub_action=="create" else "secondary"):
            st.session_state.sub_action = "create"
        if col_btn2.button("🔍 Quản Lý Đơn Hàng", use_container_width=True, type="primary" if st.session_state.sub_action=="search" else "secondary"):
            st.session_state.sub_action = "search"

        st.divider()

        if st.session_state.sub_action == "create":
            # --- PHẦN THÔNG TIN KHÁCH HÀNG ---
            with st.expander("ℹ️ Thông tin khách hàng & Báo giá", expanded=True):
                r1c1, r1c2 = st.columns(2)
                with r1c1:
                    cust_options = sorted(df_mst['Customer name'].dropna().unique())
                    cust_name = st.selectbox("🎯 Chọn Khách hàng:", options=cust_options)
                    row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
                    # Xử lý lấy Customer No linh hoạt theo tên cột
                    c_no_col = 'Customer no' if 'Customer no' in row_mst else 'Customer\nno'
                    c_no = str(row_mst.get(c_no_col, '')).split('.')[0]
                    st.info(f"**Mã khách:** {c_no} | **MST:** {row_mst.get('Tax_Code', row_mst.get('Mã số thuế', '-'))}")
                
                with r1c2:
                    # Lọc người liên hệ dựa trên mã khách
                    f_conts = df_con[df_con.iloc[:, 1].astype(str).str.contains(clean_code(c_no))] if not df_con.empty else pd.DataFrame()
                    list_conts = f_conts['Customer contact'].dropna().unique().tolist() if not f_conts.empty else ["N/A"]
                    contact_person = st.selectbox("👤 Người liên hệ:", options=list_conts)
                    st.caption(f"📍 Địa chỉ: {row_mst.get('Địa chỉ', '-')}")

                r2c1, r2c2, r2c3, r2c4 = st.columns(4)
                with r2c1:
                    f_macs = df_mac[df_mac.iloc[:, 1].astype(str).str.contains(clean_code(c_no))] if not df_mac.empty else pd.DataFrame()
                    list_macs = f_macs['Machine No.'].dropna().unique().tolist() if not f_macs.empty else ["N/A"]
                    machine_no = st.selectbox("🤖 Mã số máy:", options=list_macs)
                with r2c2:
                    list_staff = df_staff['Name'].tolist() if not df_staff.empty else ["Admin"]
                    staff_name = st.selectbox("✍️ Người lập:", options=list_staff)
                with r2c3:
                    offer_date = st.date_input("📅 Ngày báo giá:", value=datetime.now())
                with r2c4:
                    offer_no = st.text_input("🆔 Số báo giá:", value=f"QT-{offer_date.strftime('%y%m%d')}-01")

            # --- PHẦN TÌM KIẾM PHỤ TÙNG ---
            st.subheader("🔍 Thêm phụ tùng vào báo giá")
            input_search = st.text_input("Nhập Part Number (Dùng dấu ';' để nhập nhiều mã):", placeholder="Ví dụ: 3608080970; 4007010482")
            
            if st.button("🛒 Thêm vào danh sách", type="primary"):
                if input_search:
                    codes = [clean_code(c) for c in input_search.split(';') if c.strip()]
                    df_sp['CLEAN_PN'] = df_sp['Part number'].apply(clean_code)
                    not_found = []
                    for code in codes:
                        match = df_sp[df_sp['CLEAN_PN'] == code]
                        if not match.empty:
                            item = match.iloc[0]
                            st.session_state.cart.append({
                                "Part Number": item['Part number'],
                                "Part name": item['Part name'],
                                "Qty": 1,
                                "Unit": item['Unit'],
                                "VAT": 8.0,
                                "Unit Price": float(item.get('Giá bán', 0)),
                                "%Dist": 0.0,
                                "Xoá": False
                            })
                        else:
                            not_found.append(code)
                    st.session_state.last_not_found = not_found
                    st.rerun()

            if st.session_state.last_not_found:
                st.error(f"⚠️ Không tìm thấy mã: {', '.join(st.session_state.last_not_found)}")

            # --- BẢNG CHI TIẾT GIỎ HÀNG ---
            if st.session_state.cart:
                df_cart = pd.DataFrame(st.session_state.cart)
                df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)
                
                edited_df = st.data_editor(
                    df_cart,
                    column_config={
                        "Part Number": st.column_config.TextColumn(disabled=True),
                        "Part name": st.column_config.TextColumn(disabled=True),
                        "Unit Price": st.column_config.NumberColumn(format="%,d"),
                        "Qty": st.column_config.NumberColumn(min_value=1),
                        "%Dist": st.column_config.NumberColumn(format="%d%%"),
                        "Amount": st.column_config.NumberColumn(format="%,d", disabled=True),
                    },
                    use_container_width=True, hide_index=True
                )

                # Cập nhật lại giỏ hàng nếu có thay đổi trên bảng
                if not edited_df.equals(df_cart):
                    new_cart = []
                    for i, row in edited_df.iterrows():
                        if not row['Xoá']:
                            new_cart.append(row.to_dict())
                    st.session_state.cart = new_cart
                    st.rerun()

                # --- TỔNG KẾT & LƯU ---
                st.divider()
                total_parts = edited_df['Amount'].sum()
                
                c1, c2 = st.columns([2,1])
                with c2:
                    st.session_state.ship_cost = st.number_input("Phí vận chuyển (VND):", value=st.session_state.ship_cost)
                    sub_total = total_parts + st.session_state.ship_cost
                    vat_amt = sub_total * 0.08
                    grand_total = sub_total + vat_amt
                    
                    st.markdown(f"**Tổng tiền hàng:** {total_parts:,.0f} VND")
                    st.markdown(f"**VAT (8%):** {vat_amt:,.0f} VND")
                    st.subheader(f"TỔNG CỘNG: {grand_total:,.0f} VND")

                if st.button("💾 XÁC NHẬN & LƯU BÁO GIÁ", use_container_width=True, type="primary"):
                    # Chuẩn bị dữ liệu Header
                    h_data = {
                        "Offer_No": offer_no, "Offer_Date": str(offer_date),
                        "Customer_Name": cust_name, "Cust_No": c_no,
                        "Address": row_mst.get('Địa chỉ', '-'),
                        "Contact_Person": contact_person, "Machine_No": machine_no,
                        "Staff": staff_name, "Total_Amount": total_parts,
                        "Shipment_Cost": st.session_state.ship_cost,
                        "VAT_Amount": vat_amt, "Grand_Total": grand_total, "Status": "Draft"
                    }
                    # Chuẩn bị dữ liệu Details
                    d_df = edited_df[["Part Number", "Part name", "Qty", "Unit", "Unit Price", "VAT", "%Dist"]].copy()
                    
                    if save_quotation(h_data, d_df):
                        st.success("✅ Đã lưu báo giá thành công lên Google Sheets!")
                        st.session_state.cart = [] # Reset giỏ hàng
                        st.balloons()
                    else:
                        st.error("❌ Lưu thất bại. Vui lòng kiểm tra lại quyền truy cập Sheets.")

        elif st.session_state.sub_action == "search":
            st.info("Tính năng đang phát triển: Xem lịch sử báo giá từ sheet Offer_Header")

    elif menu == "🗂️ Master Data":
        st.subheader("Dữ liệu Phụ tùng (SP List)")
        st.dataframe(df_sp, use_container_width=True)

if __name__ == "__main__":
    main()
