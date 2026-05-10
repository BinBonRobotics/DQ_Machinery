import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime

# 1. Hàm làm sạch mã Part Number
def clean_code(val):
if pd.isna(val) or val == "": return ""
s = str(val).split('.')[0].strip()
return re.sub(r'[^a-zA-Z0-9]', '', s).upper()

@st.cache_data(ttl=60)
def load_all_data():
try:
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1gtvdEdotdJIti4s8gvHxgv0Q6jl0fAhuxhym9uuCQt8"
df_sp = conn.read(spreadsheet=url, worksheet="SP List")
df_mst = conn.read(spreadsheet=url, worksheet="Customer_MST")
df_con = conn.read(spreadsheet=url, worksheet="Customer_Contact")
df_mac = conn.read(spreadsheet=url, worksheet="List of machines")
df_staff = conn.read(spreadsheet=url, worksheet="Staff")
return df_sp, df_mst, df_con, df_mac, df_staff
except Exception as e:
st.error(f"❌ Lỗi kết nối dữ liệu: {e}")
return [None] * 5

def main():
st.set_page_config(page_title="D&Q Machinery", layout="wide")
df_sp, df_mst, df_con, df_mac, df_staff = load_all_data()
if df_mst is None: return

# Khởi tạo Session State
if 'cart' not in st.session_state: st.session_state.cart = []
if 'sub_action' not in st.session_state: st.session_state.sub_action = "create"
if 'ship_cost' not in st.session_state: st.session_state.ship_cost = 0.0
if 'last_not_found' not in st.session_state: st.session_state.last_not_found = []

# --- 1. SIDEBAR ---
st.sidebar.title("⚙️ Cấu hình")
ty_gia = st.sidebar.number_input("Tỷ giá Euro (VND):", value=31000, step=100)
if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
st.cache_data.clear()
st.rerun()

menu_selection = st.sidebar.radio("📂 Danh mục chính:", ["📄 Báo Giá Phụ Tùng", "🗂️ Master Data"])

if menu_selection == "📄 Báo Giá Phụ Tùng":
# --- 2. NÚT ĐIỀU HƯỚNG ---
col_btn1, col_btn2, _ = st.columns([1.5, 2, 3])
if col_btn1.button("➕ Tạo Báo Giá", use_container_width=True, type="primary" if st.session_state.sub_action=="create" else "secondary"):
st.session_state.sub_action = "create"
if col_btn2.button("🔍 Order Management", use_container_width=True, type="primary" if st.session_state.sub_action=="search" else "secondary"):
st.session_state.sub_action = "search"

st.divider()

# --- 3. TRANG TẠO BÁO GIÁ ---
if st.session_state.sub_action == "create":
# --- 3_1 & 3_8: THÔNG TIN HEADER ---
r1c1, r1c2 = st.columns(2)
with r1c1:
cust_options = sorted(df_mst['Customer name'].dropna().unique())
cust_name = st.selectbox("🎯 Khách hàng:", options=cust_options)
row_mst = df_mst[df_mst['Customer name'] == cust_name].iloc[0]
c_no = str(row_mst.get('Customer no', row_mst.get('Customer\nno', ''))).split('.')[0]
st.info(f"Cust No: {c_no} | MST: {row_mst.get('Mã số thuế', '-')}")
with r1c2:
f_conts = df_con[df_con.iloc[:, 1].astype(str).str.contains(clean_code(c_no))] if df_con is not None else pd.DataFrame()
list_conts = f_conts.iloc[:, 7].dropna().unique().tolist() if not f_conts.empty else []
st.selectbox("👤 Contact Person:", options=list_conts if list_conts else ["N/A"])
st.markdown(f"📍 Địa chỉ: {str(row_mst.get('Địa chỉ', '-'))}")

r2c1, r2c2, r2c3, r2c4 = st.columns(4)
with r2c1:
f_macs = df_mac[df_mac.iloc[:, 1].astype(str).str.contains(clean_code(c_no))] if df_mac is not None else pd.DataFrame()
list_macs = f_macs.iloc[:, 14].dropna().unique().tolist() if not f_macs.empty else []
st.selectbox("🤖 Machine Number:", options=list_macs if list_macs else ["N/A"])
with r2c2:
list_staff = df_staff['Name'].dropna().unique().tolist() if (df_staff is not None and 'Name' in df_staff.columns) else ["Admin"]
st.selectbox("✍️ Người lập:", options=list_staff)
with r2c3:
offer_date = st.date_input("📅 Offer Date:", value=datetime.now())
with r2c4:
offer_no_suggest = f"{offer_date.year}-{offer_date.month:02d}-0001"
st.text_input("🆔 Offer No:", value=offer_no_suggest)

st.divider()

# --- 3_2 & 3_3: TÌM PART NUMBER & NÚT BẤM ---
st.subheader("🔍 Tìm Part Number")
input_search = st.text_input("Nhập mã (cách nhau bởi dấu ;):", placeholder="3608080970; 4007010482")

# Nút thêm vào giỏ hàng cố định phía dưới ô nhập
add_btn = st.button("🛒 Thêm vào giỏ hàng", type="primary")

if st.session_state.last_not_found:
st.error(f"❌ Không tìm thấy Part Number: {', '.join(st.session_state.last_not_found)}")

if add_btn and input_search:
codes = [clean_code(c) for c in input_search.split(';') if c.strip()]
df_sp['CLEAN_PN'] = df_sp['Part number'].apply(clean_code)
current_not_found = []

for code in codes:
match = df_sp[df_sp['CLEAN_PN'] == code]
if not match.empty:
item = match.iloc[0]
st.session_state.cart.append({
"Part Number": item['Part number'], "Part name": item['Part name'],
"Qty": 1, "Unit": item['Unit'], "VAT": 8,
"Unit Price": float(item.get('Giá bán', 0)), "%Dist": 0.0, "Xoá": False
})
else:
current_not_found.append(code)

st.session_state.last_not_found = current_not_found
st.rerun()

# --- 3_4: TABLE DANH SÁCH CHI TIẾT ---
if st.session_state.cart:
st.markdown("### 📋 Danh sách chi tiết")
df_cart = pd.DataFrame(st.session_state.cart)
df_cart.insert(0, 'No.', range(1, len(df_cart) + 1))
df_cart['Amount'] = df_cart['Unit Price'] * df_cart['Qty'] * (1 - df_cart['%Dist']/100)

display_cols = ["No.", "Part Number", "Part name", "Qty", "Unit", "VAT", "Unit Price", "%Dist", "Amount", "Xoá"]

edited_df = st.data_editor(
df_cart[display_cols],
column_config={
"No.": st.column_config.NumberColumn(disabled=True),
"Part Number": st.column_config.TextColumn(disabled=True),
"Part name": st.column_config.TextColumn(disabled=True),
"Unit": st.column_config.TextColumn(disabled=True),
"VAT": st.column_config.NumberColumn("VAT", format="%d", disabled=True),
"Unit Price": st.column_config.NumberColumn(format="%,d", disabled=True),
"Amount": st.column_config.NumberColumn(format="%,d", disabled=True),
"Qty": st.column_config.NumberColumn(width=60, min_value=1),
"%Dist": st.column_config.NumberColumn(width=80, format="%d%%"),
"Xoá": st.column_config.CheckboxColumn("Xoá", width=50)
},
use_container_width=True, hide_index=True, key="cart_editor"
)

# Nút Xoá hết hàng (B_1: Thêm lại tính năng)
if st.button("🗑️ Xoá hết hàng", type="secondary"):
st.session_state.cart = []
st.session_state.last_not_found = []
st.rerun()

if not edited_df.equals(df_cart[display_cols]):
new_cart = []
for i, row in edited_df.iterrows():
if not row['Xoá']:
item = st.session_state.cart[i].copy()
item['Qty'] = row['Qty']; item['%Dist'] = row['%Dist']
new_cart.append(item)
st.session_state.cart = new_cart
st.session_state.last_not_found = []
st.rerun()

# --- 3_5: TỔNG KẾT BÁO GIÁ ---
st.divider()
total_amt = df_cart['Amount'].sum()

_, col_calc = st.columns([2, 1.5])
with col_calc:
st.markdown("#### Tổng kết báo giá")
ship_val = st.number_input("Nhập Shipment Cost (VND):", value=float(st.session_state.ship_cost), step=1000.0, format="%.0f")
if ship_val != st.session_state.ship_cost:
st.session_state.ship_cost = ship_val; st.rerun()

sub_total = total_amt + st.session_state.ship_cost
vat_calc = sub_total * 0.08
grand_total = sub_total + vat_calc

summary_data = {
"Nội dung": ["Total Amount", "Shipment Cost", "Sub-Total", "VAT (8%)", "GRAND TOTAL"],
"Số tiền (VND)": [f"{total_amt:,.0f}", f"{st.session_state.ship_cost:,.0f}",
f"{sub_total:,.0f}", f"{vat_calc:,.0f}", f"{grand_total:,.0f}"]
}
st.table(pd.DataFrame(summary_data))

# --- 3_7: NÚT LƯU BÁO GIÁ ---
st.button("💾 Lưu Báo Giá", use_container_width=True, type="primary")

# --- 4: ORDER MANAGEMENT ---
elif st.session_state.sub_action == "search":
st.subheader("🔍 Order Management")
tab_q, tab_t, tab_r = st.tabs(["📄 Quotations", "🚚 Offers_Tracking", "📊 SP_Report"])
with tab_q: st.info("Lưu trữ báo giá")
with tab_t: st.info("Theo dõi đơn hàng")
with tab_r: st.info("Báo cáo")

elif menu_selection == "🗂️ Master Data":
st.dataframe(df_sp, use_container_width=True)

if name == "main":
main()
