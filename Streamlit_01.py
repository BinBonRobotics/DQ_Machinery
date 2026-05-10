import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime

# --- CẤU HÌNH ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"

@st.cache_data(ttl=2)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_sp = conn.read(spreadsheet=SHEET_URL, worksheet="SP List")
    df_h = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Header")
    df_d = conn.read(spreadsheet=SHEET_URL, worksheet="Offer_Details")
    # Clean data
    for df in [df_h, df_d]:
        if 'Offer_No' in df.columns: df['Offer_No'] = df['Offer_No'].astype(str).str.strip()
    return df_sp, df_h, df_d

def update_sheet(ws_name, df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(spreadsheet=SHEET_URL, worksheet=ws_name, data=df)

def main():
    st.set_page_config(page_title="D&Q Management", layout="wide")
    
    # Load data an toàn
    try:
        df_sp, df_h, df_d = load_data()
    except:
        st.error("Lỗi kết nối Sheets"); return

    tab1, tab2 = st.tabs(["➕ Tạo Báo Giá Mới", "📋 Quản Lý & Chỉnh Sửa"])

    # --- TAB 1: CHỈ ĐỂ TẠO MỚI ---
    with tab1:
        st.subheader("Tạo báo giá mới")
        # (Giữ logic tạo mới đơn giản ở đây nếu cần, hoặc tập trung vào Tab 2 trước)
        st.info("Sử dụng Tab 'Quản Lý' để xem hoặc sửa các báo giá đã có.")

    # --- TAB 2: QUẢN LÝ & SỬA TRỰC TIẾP ---
    with tab2:
        st.subheader("Danh sách Báo giá")
        st.dataframe(df_h[['Offer_No', 'Customer_Name', 'Grand_Total']], use_container_width=True)
        
        target_off = st.selectbox("Chọn Offer No để chỉnh sửa nội dung:", [""] + list(df_h['Offer_No'].unique()))
        
        if target_off:
            st.divider()
            st.warning(f"Đang chỉnh sửa chi tiết cho: {target_off}")
            
            # Lấy data chi tiết của Offer đó
            current_details = df_d[df_d['Offer_No'] == target_off].copy()
            
            # Chuẩn hóa số liệu
            for col in ['Qty', 'Unit_Price', 'VAT_Rate', 'Discount_Percent']:
                current_details[col] = pd.to_numeric(current_details[col], errors='coerce').fillna(0.0)
            
            # Tính lại Amount để hiển thị
            current_details['Amount'] = current_details['Unit_Price'] * current_details['Qty'] * (1 - current_details['Discount_Percent']/100)

            # Công cụ sửa:
            c1, c2 = st.columns(2)
            with c1:
                new_pn = st.text_input("🔍 Thêm Part Number mới vào Offer này:")
                if st.button("➕ Thêm vào danh sách"):
                    match = df_sp[df_sp['Part number'].astype(str) == new_pn]
                    if not match.empty:
                        item = match.iloc[0]
                        new_row = pd.DataFrame([{
                            "Offer_No": target_off, "Part_Number": item['Part number'],
                            "Part_Name": item['Part name'], "Qty": 1.0, "Unit": item['Unit'],
                            "Unit_Price": float(pd.to_numeric(item['Giá bán'], errors='coerce') or 0),
                            "VAT_Rate": 8.0, "Discount_Percent": 0.0, "Amount": 0.0
                        }])
                        df_d = pd.concat([df_d, new_row], ignore_index=True)
                        update_sheet("Offer_Details", df_d)
                        st.success("Đã thêm!"); st.cache_data.clear(); st.rerun()
                    else: st.error("Mã không tồn tại")

            # Bảng chỉnh sửa trực tiếp (Data Editor)
            st.write("📝 Chỉnh sửa số lượng/giá trực tiếp trên bảng:")
            edited_d = st.data_editor(
                current_details, 
                num_rows="dynamic", # Cho phép nhấn nút (+) hoặc (Delete) của Streamlit
                use_container_width=True,
                key="editor_tab2",
                column_config={
                    "Amount": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
                    "Unit_Price": st.column_config.NumberColumn(format="%,.0f")
                }
            )

            if st.button("💾 XÁC NHẬN CẬP NHẬT TẤT CẢ", type="primary", use_container_width=True):
                try:
                    # 1. Tính toán lại tổng tiền cho Header
                    edited_d['Amount'] = edited_d['Unit_Price'] * edited_d['Qty'] * (1 - edited_d['Discount_Percent']/100)
                    total_goods = edited_d['Amount'].sum()
                    
                    # Lấy thông tin header cũ
                    h_row = df_h[df_h['Offer_No'] == target_off].iloc[0].copy()
                    ship = float(h_row['Shipment_Cost'])
                    vat_amt = (total_goods + ship) * 0.08
                    grand = total_goods + ship + vat_amt
                    
                    # Cập nhật Header dataframe
                    df_h.loc[df_h['Offer_No'] == target_off, ['Total_Amount', 'VAT_Amount', 'Grand_Total']] = [total_goods, vat_amt, grand]
                    
                    # 2. Cập nhật Details (Xóa cũ ghi mới cho Offer này)
                    df_d_new = pd.concat([df_d[df_d['Offer_No'] != target_off], edited_d], ignore_index=True)
                    # Ép kiểu trước khi lưu
                    df_d_new = df_d_new.drop(columns=['Amount'], errors='ignore') 
                    
                    # 3. Ghi đè lên Sheets
                    update_sheet("Offer_Header", df_h)
                    update_sheet("Offer_Details", df_d_new)
                    
                    st.success("✅ Đã cập nhật thành công!")
                    st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi lưu: {e}")

if __name__ == "__main__":
    main()
