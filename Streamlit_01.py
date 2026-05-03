import pandas as pd

def calculate_pricing(df, exchange_rate):
    """
    df: DataFrame chứa các cột 'Giá Net Euro' và 'Hệ số'
    exchange_rate: Tỷ giá từ Euro sang VND
    """
    
    # 1. Chuyển đổi Giá Net Euro sang Giá Net VND
    df['Giá Net VND'] = df['Giá Net Euro'] * exchange_rate
    
    # 2. Tính Giá bán (Giá Net VND * Hệ số)
    # Giả sử Hệ số này bao gồm cả các chi phí và Markup
    df['Giá bán'] = df['Giá Net VND'] * df['Hệ số']
    
    # 3. Tính Lợi nhuận (Profit) = Giá bán - Giá Net VND
    df['Profit (Lợi nhuận)'] = df['Giá bán'] - df['Giá Net VND']
    
    # 4. Tính Biên lợi nhuận (Margin) = Profit / Giá bán
    df['Margin (Biên lợi nhuận)'] = (df['Profit (Lợi nhuận)'] / df['Giá bán']).apply(lambda x: f"{x:.2%}")
    
    return df

# --- VÍ DỤ ÁP DỤNG ---
data = {
    'Giá Net Euro': [100, 250, 50],
    'Hệ số': [1.5, 1.8, 2.0]
}

df_pricing = pd.DataFrame(data)
ti_gia_euro = 27500  # Ví dụ tỷ giá hiện tại

result = calculate_pricing(df_pricing, ti_gia_euro)

# Hiển thị kết quả theo đúng thứ tự cột bạn yêu cầu
cols = ['Giá Net Euro', 'Giá Net VND', 'Hệ số', 'Giá bán', 'Profit (Lợi nhuận)', 'Margin (Biên lợi nhuận)']
print(result[cols])
