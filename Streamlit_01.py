import streamlit as st
import pandas as pd

# 1. Để file Excel cùng thư mục với file .py của bạn
# 2. Sử dụng cách load này để tránh lỗi đường dẫn
FILE_PATH = "Test_Streamlit (5).xlsx"

@st.cache_data
def load_all_data(file):
    try:
        data = {
            "staff": pd.read_excel(file, sheet_name="Staff"),
            "customers": pd.read_excel(file, sheet_name="Customer_MST"),
            "contacts": pd.read_excel(file, sheet_name="Customer_Contact"),
            "products": pd.read_excel(file, sheet_name="SP_List"),
            "stock": pd.read_excel(file, sheet_name="Stock list"),
            "machines": pd.read_excel(file, sheet_name="List_of_ machines")
        }
        return data
    except Exception as e:
        st.error(f"Lỗi khi đọc file: {e}")
        return None

all_df = load_all_data(FILE_PATH)

if all_df:
    st.success("Đã kết nối dữ liệu thành công!")
    # Tiếp tục các xử lý khác với all_df["products"], all_df["staff"],...
