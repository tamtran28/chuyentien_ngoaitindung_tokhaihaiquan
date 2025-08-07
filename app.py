import streamlit as st
import pandas as pd
import io
from datetime import datetime

# --- HÀM XỬ LÝ LOGIC CHÍNH ---
# Đóng gói logic của bạn vào một hàm để code sạch sẽ và dễ quản lý
def process_tkhq_data(df, ngay_kiem_toan):
    """
    Hàm này nhận vào DataFrame thô và ngày kiểm toán,
    thực hiện tất cả các bước xử lý và trả về DataFrame kết quả.
    """
    # 2. Chuyển định dạng cột ngày tháng
    df['DECLARATION_DUE_DATE'] = pd.to_datetime(df['DECLARATION_DUE_DATE'], errors='coerce')
    df['DECLARATION_RECEIVED_DATE'] = pd.to_datetime(df['DECLARATION_RECEIVED_DATE'], errors='coerce')

    # 3. (1) Không nhập ngày đến hạn TKHQ
    df['KHÔNG NHẬP NGÀY ĐẾN HẠN TKHQ'] = df['DECLARATION_DUE_DATE'].isna().map(lambda x: 'X' if x else '')

    # 4. (2) Số ngày quá hạn TKHQ
    # Chỉ tính nếu chưa có ngày nhận TKHQ và quá hạn > 0
    df['SỐ NGÀY QUÁ HẠN TKHQ'] = df.apply(
        lambda row: (ngay_kiem_toan - row['DECLARATION_DUE_DATE']).days
        if pd.notnull(row['DECLARATION_DUE_DATE']) and pd.isnull(row['DECLARATION_RECEIVED_DATE']) and (ngay_kiem_toan - row['DECLARATION_DUE_DATE']).days > 0
        else '',
        axis=1
    )

    # 5. (3) Quá hạn nhưng chưa nhập TKHQ
    # Chuyển cột sang dạng số để xử lý an toàn
    so_ngay_qua_han_numeric = pd.to_numeric(df['SỐ NGÀY QUÁ HẠN TKHQ'], errors='coerce')
    df['QUÁ HẠN CHƯA NHẬP TKHQ'] = so_ngay_qua_han_numeric.apply(lambda x: 'X' if pd.notnull(x) and x > 0 else '')

    # 6. (4) Quá hạn > 90 ngày nhưng chưa nhập TKHQ
    df['QUÁ HẠN > 90 NGÀY CHƯA NHẬP TKHQ'] = so_ngay_qua_han_numeric.apply(lambda x: 'X' if pd.notnull(x) and x > 90 else '')

    # 7. (5) Có phát sinh gia hạn TKHQ
    def check_gia_han(row):
        # Kiểm tra sự tồn tại của cột trước khi truy cập
        if 'AUDIT_DATE2' in row and pd.notnull(row['AUDIT_DATE2']):
            return 'X'
        if 'DECLARATION_REF_NO' in row and isinstance(row['DECLARATION_REF_NO'], str):
            text = row['DECLARATION_REF_NO'].lower().replace(" ", "")
            if 'giahan' in text:
                return 'X'
        return ''

    df['CÓ PHÁT SINH GIA HẠN TKHQ'] = df.apply(check_gia_han, axis=1)

    return df

# --- GIAO DIỆN NGƯỜI DÙNG STREAMLIT ---

st.set_page_config(layout="wide")
st.title("Ứng dụng Phân tích Tờ khai Hải quan (TKHQ)")

# --- Thanh bên (Sidebar) cho các phần cài đặt và tải file ---
with st.sidebar:
    st.header("Cài đặt và Tải file")

    # Widget để người dùng tải file lên
    uploaded_file = st.file_uploader(
        "Chọn file Excel cần phân tích",
        type=['xlsx']
    )

    # Widget để người dùng chọn ngày kiểm toán
    audit_date = st.date_input(
        "Chọn ngày kiểm toán",
        # Dựa trên ngày trong script gốc của bạn
        value=datetime(2025, 5, 31)
    )

# --- Khu vực xử lý chính ---
if uploaded_file is not None:
    st.info(f"Đã tải lên file: **{uploaded_file.name}**")
    
    # Nút để bắt đầu xử lý
    if st.button("Bắt đầu xử lý", type="primary"):
        with st.spinner("Đang đọc và xử lý dữ liệu... Vui lòng chờ."):
            try:
                # Đọc dữ liệu từ file đã tải lên
                df_raw = pd.read_excel(uploaded_file)
                
                # Chuyển đổi ngày kiểm toán từ widget thành dạng pandas datetime
                ngay_kiem_toan_pd = pd.to_datetime(audit_date)
                
                # Gọi hàm xử lý
                df_processed = process_tkhq_data(df_raw, ngay_kiem_toan_pd)
                
                st.success("Xử lý hoàn tất!")
                
                # Hiển thị kết quả
                st.subheader("Kết quả phân tích")
                st.dataframe(df_processed)
                
                # --- Chức năng tải xuống file Excel ---
                # Tạo một buffer trong bộ nhớ
                output_buffer = io.BytesIO()
                with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                    df_processed.to_excel(writer, index=False, sheet_name='ket_qua_TKHQ')
                
                st.download_button(
                    label="📥 Tải xuống kết quả Excel",
                    data=output_buffer.getvalue(),
                    file_name=f"ket_qua_TKHQ_{audit_date.strftime('%d%m%Y')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except Exception as e:
                st.error(f"Đã có lỗi xảy ra trong quá trình xử lý: {e}")

else:
    st.info("Vui lòng tải lên một file Excel để bắt đầu.")
