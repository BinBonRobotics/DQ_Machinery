def print_pdf_feature(quotation_data, parts_list):
    """
    quotation_data: Dictionary chứa thông tin chung (Offer No, Customer Name,...)
    parts_list: List các dictionary, mỗi dict là một dòng sản phẩm
    """
    # 1. Giữ nguyên mapping cũ đã chạy ổn định
    # mapping_info = { ... } 
    # (Giả sử bạn đã có code kết nối đến sheet qua GSheetsConnection)
    sheet = client.open("Test_Streamlit").worksheet("Offer Sample")

    # 2. Xử lý đưa dữ liệu sản phẩm vào từ hàng 18
    START_ROW = 18
    num_parts = len(parts_list)
    
    # Kiểm tra số lượng hàng hiện tại để chèn thêm nếu cần
    # Giả sử bảng mẫu có khoảng 10 hàng trống (đến hàng 27 như trong ảnh)
    # Chúng ta sẽ chèn thêm hàng trước khi điền dữ liệu để đảm bảo format
    if num_parts > 1:
        # Chèn thêm (num_parts - 1) hàng từ hàng 19 trở đi để giữ format hàng 18
        sheet.insert_rows(START_ROW + 1, number_of_rows=num_parts - 1, inheritance_strategy='INNER')

    # Chuẩn bị dữ liệu để update hàng loạt (Batch Update) cho hiệu năng cao
    rows_to_update = []
    for i, part in enumerate(parts_list):
        # Mapping cột theo image_ff7f96.png:
        # A: No, B: Part Number, C: Part Name, D: Qty, E: Unit, 
        # F: VAT, G: Unit Price, H: % Discount, J: Amount
        row = [
            part.get('No', i+1),              # Cột A
            part.get('Part Number', ''),     # Cột B
            part.get('Part Name', ''),       # Cột C
            part.get('Qty', 0),              # Cột D
            part.get('Unit', 'pc'),          # Cột E
            part.get('VAT', 0),              # Cột F
            part.get('Unit Price', 0),       # Cột G
            part.get('Discount', 0),         # Cột H
            '',                               # Cột I (Trống theo mapping)
            part.get('Amount', 0)            # Cột J
        ]
        rows_to_update.append(row)

    # Thực hiện ghi dữ liệu xuống Sheet bắt đầu từ A18 đến J...
    range_label = f'A{START_ROW}:J{START_ROW + num_parts - 1}'
    sheet.update(range_name=range_label, values=rows_to_update)

    # 3. Sau khi điền data xong thì thực hiện lệnh Print PDF hiện tại của bạn
    # ... (Giữ nguyên code export PDF cũ)
