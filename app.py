from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import streamlit as st
import pandas as pd
import re
from datetime import datetime
import io
import os

# ===== ĐĂNG KÝ FONT ARIAL =====
pdfmetrics.registerFont(TTFont("Arial", "fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "fonts/arialbd.ttf"))

# ===== FORMAT TIỀN =====
def format_currency(value):
    return f"{value:,.0f}".replace(",", ".")

# ===== SẮP XẾP TÊN PHÒNG =====
def sort_phong_key(phong):
    match_obj = re.match(r"(\d+)([A-Za-z]*)", str(phong))
    if match_obj:
        so = int(match_obj.group(1))
        chu = match_obj.group(2)
        return (so, chu)
    return (phong, "")

# ===== SESSION =====
if "ds_phong" not in st.session_state:
    st.session_state["ds_phong"] = []

st.title("🏠 Quản lý tiền phòng trọ")

# ===== GIÁ CỐ ĐỊNH =====
st.sidebar.header("⚙️ Cài đặt giá")
TIEN_PHONG_CO_DINH = st.sidebar.number_input("💵 Tiền phòng cố định", min_value=0, value=2100000, step=50000)
GIA_DIEN = st.sidebar.number_input("⚡ Giá điện (1 kWh)", min_value=0, value=3000, step=100)
GIA_NUOC = st.sidebar.number_input("🚰 Giá nước (1 m³)", min_value=0, value=15000, step=500)
TIEN_RAC = st.sidebar.number_input("🗑️ Tiền rác", min_value=0, value=10000, step=1000)

# ===== NHẬP DỮ LIỆU =====
st.header("➕ Nhập thông tin phòng")

ten_phong = st.text_input("Tên phòng (tự do nhập chữ/số)")

dien_cu = st.number_input("Chỉ số điện cũ", min_value=0, step=1)
dien_moi_input = st.number_input("Chỉ số điện mới", min_value=0, step=1)
dien_moi_thuc = dien_moi_input if dien_moi_input >= dien_cu else dien_moi_input + 1000
so_dien = max(0, dien_moi_thuc - dien_cu)
tien_dien = so_dien * GIA_DIEN

nuoc_cu = st.number_input("Chỉ số nước cũ", min_value=0, step=1)
nuoc_moi_input = st.number_input("Chỉ số nước mới", min_value=0, step=1)
nuoc_moi_thuc = nuoc_moi_input if nuoc_moi_input >= nuoc_cu else nuoc_moi_input + 1000
so_nuoc = max(0, nuoc_moi_thuc - nuoc_cu)
tien_nuoc = so_nuoc * GIA_NUOC

tong = TIEN_PHONG_CO_DINH + tien_dien + tien_nuoc + TIEN_RAC

if st.button("💾 Lưu phòng"):
    if ten_phong.strip() == "":
        st.warning("⚠️ Bạn phải nhập tên phòng trước khi lưu!")
    else:
        record = {
            "Phòng": ten_phong,
            "Đơn giá phòng": TIEN_PHONG_CO_DINH,
            "Đơn giá điện": GIA_DIEN,
            "Số điện cũ": dien_cu,
            "Số điện mới": dien_moi_input,
            "Số điện sử dụng (kWh)": so_dien,
            "Tiền điện": tien_dien,
            "Đơn giá nước": GIA_NUOC,
            "Số nước cũ": nuoc_cu,
            "Số nước mới": nuoc_moi_input,
            "Số nước sử dụng (m³)": so_nuoc,
            "Tiền nước": tien_nuoc,
            "Tiền phòng": TIEN_PHONG_CO_DINH,
            "Tiền rác": TIEN_RAC,
            "Tổng tiền": tong
        }

        found = False
        for i, p in enumerate(st.session_state["ds_phong"]):
            if p["Phòng"].lower() == ten_phong.lower():
                st.session_state["ds_phong"][i] = record
                found = True
                st.info(f"✏️ Đã cập nhật lại thông tin phòng {ten_phong}")
                break

        if not found:
            st.session_state["ds_phong"].append(record)
            st.success(f"✅ Đã lưu phòng {ten_phong}")

# ===== HIỂN THỊ DANH SÁCH =====
if st.session_state["ds_phong"]:
    df = pd.DataFrame(st.session_state["ds_phong"])
    df["__sort_key__"] = df["Phòng"].map(sort_phong_key)
    df = df.sort_values("__sort_key__").drop(columns="__sort_key__").reset_index(drop=True)

    df_display = df.copy()
    for col in ["Đơn giá phòng", "Đơn giá điện", "Đơn giá nước",
                "Tiền phòng", "Tiền điện", "Tiền nước", "Tiền rác", "Tổng tiền"]:
        df_display[col] = df_display[col].apply(format_currency)

    st.header("📊 Bảng tổng hợp tiền phòng")
    st.dataframe(df_display)

    tong_tien_all = df["Tổng tiền"].sum()
    st.subheader(f"💰 Tổng thu tất cả phòng: {format_currency(tong_tien_all)}")

    # ===== XUẤT PDF =====
    if st.button("🧾 Xuất PDF Hóa đơn"):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="Arial", fontName="Arial-Bold", fontSize=12))
        styles.add(ParagraphStyle(name="ArialTitle", fontName="Arial", fontSize=16, alignment=1))

        for _, row in df.iterrows():
            elements.append(Paragraph(f"TIỀN PHÒNG {row['Phòng']}", styles["ArialTitle"]))
            elements.append(Spacer(1, 12))

            data = [
                ["Nội dung", "Số cũ", "Số mới", "Tiêu thụ", "Đơn giá", "Thành tiền"],
                ["Tiền phòng", "-", "-", "-", format_currency(row["Đơn giá phòng"]), format_currency(row["Tiền phòng"])],
                ["Điện (kWh)", row["Số điện cũ"], row["Số điện mới"], row["Số điện sử dụng (kWh)"], 
                 format_currency(row["Đơn giá điện"]), format_currency(row["Tiền điện"])],
                ["Nước (m³)", row["Số nước cũ"], row["Số nước mới"], row["Số nước sử dụng (m³)"], 
                 format_currency(row["Đơn giá nước"]), format_currency(row["Tiền nước"])],
                ["Rác", "-", "-", "-", "-", format_currency(row["Tiền rác"])],
                ["TỔNG CỘNG", "", "", "", "", format_currency(row["Tổng tiền"])]
            ]

            table = Table(data, colWidths=[90, 60, 60, 60, 80, 100])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 0), (-1, -1), "Arial"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 24))

        doc.build(elements)
        buffer.seek(0)

        st.download_button(
            label="⬇️ Tải file PDF",
            data=buffer,
            file_name=f"hoa_don_phong_{datetime.now().strftime('%m-%Y')}.pdf",
            mime="application/pdf"
        )
