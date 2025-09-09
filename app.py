import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ===== ĐĂNG KÝ FONT ARIAL =====
pdfmetrics.registerFont(TTFont("Arial", "fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "fonts/arialbd.ttf"))
# pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
# pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))

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
TIEN_PHONG_CO_DINH = st.sidebar.number_input("💵 Tiền phòng cố định", min_value=0, value=2100000, step=100000)
GIA_DIEN = st.sidebar.number_input("⚡ Giá điện (1 kWh)", min_value=0, value=3500, step=500)
GIA_NUOC = st.sidebar.number_input("🚰 Giá nước (1 m³)", min_value=0, value=20000, step=1000)
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
            "Tiền phòng": TIEN_PHONG_CO_DINH,
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
    for col in ["Tiền phòng", "Đơn giá điện", "Đơn giá nước",
                "Tiền điện", "Tiền nước", "Tiền rác", "Tổng tiền"]:
        df_display[col] = df_display[col].apply(format_currency)

    st.header("📊 Bảng tổng hợp tiền phòng")
    df_display = df_display.set_index("Phòng")
    st.dataframe(df_display)

    tong_tien_all = df["Tổng tiền"].sum()
    st.subheader(f"💰 Tổng thu tất cả phòng: {format_currency(tong_tien_all)}")

    # ===== XUẤT PDF =====
    if st.button("🧾 Xuất Hóa Đơn"):
        thermal_width = 58 * mm
        thermal_height = 100 * mm
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=(thermal_width, thermal_height),
            leftMargin=5 * mm,
            rightMargin=5 * mm,
            topMargin=5 * mm,
            bottomMargin=5 * mm
        )
        elements = []

        # Style setup
        styles = getSampleStyleSheet()
        styles["Normal"].fontName = "Arial"
        styles["Normal"].fontSize = 10
        styles["Normal"].spaceAfter = 2
        styles.add(ParagraphStyle(name="BillTitle", fontName="Arial-Bold", fontSize=12, alignment=1, spaceAfter=6))
        styles.add(ParagraphStyle(name="TotalBold", fontName="Arial-Bold", fontSize=12, alignment=1, spaceAfter=6))
        styles.add(ParagraphStyle(name="TotalNum", fontName="Arial-Bold", fontSize=16, alignment=1, spaceAfter=6))


        for idx, row in df.iterrows():
            # Tiêu đề
            elements.append(Paragraph(f"<b>PHIẾU THU TIỀN PHÒNG {row['Phòng'].upper()}</b>", styles["BillTitle"]))
            elements.append(Spacer(1, 6))

            # Nội dung từng dòng
            elements.append(Paragraph(f"Tiền phòng: {format_currency(row['Tiền phòng'])}đ", styles["Normal"]))
            elements.append(Spacer(1, 6))

            elements.append(Paragraph(f"Điện cũ: {row['Số điện cũ']}", styles["Normal"]))
            elements.append(Paragraph(f"Điện mới: {row['Số điện mới']}", styles["Normal"]))
            elements.append(Paragraph(f"Tiêu thụ: {row['Số điện sử dụng (kWh)']} kWh", styles["Normal"]))
            elements.append(Paragraph(f"Tiền điện: {format_currency(row['Tiền điện'])}đ", styles["Normal"]))
            elements.append(Spacer(1, 6))

            elements.append(Paragraph(f"Nước cũ: {row['Số nước cũ']}", styles["Normal"]))
            elements.append(Paragraph(f"Nước mới: {row['Số nước mới']}", styles["Normal"]))
            elements.append(Paragraph(f"Tiêu thụ: {row['Số nước sử dụng (m³)']} m³", styles["Normal"]))
            elements.append(Paragraph(f"Tiền nước: {format_currency(row['Tiền nước'])}đ", styles["Normal"]))
            elements.append(Spacer(1, 6))

            elements.append(Paragraph(f"Tiền rác: {format_currency(row['Tiền rác'])}đ", styles["Normal"]))
            elements.append(Spacer(1, 6))

            # elements.append(Paragraph(f"<b>TỔNG CỘNG: {format_currency(row['Tổng tiền'])}</b> đ", styles["Normal"]))
            elements.append(Paragraph(f"<b>TỔNG CỘNG:</b>", styles["TotalBold"]))
            elements.append(Paragraph(f"{format_currency(row['Tổng tiền'])}đ", styles["TotalNum"]))
            elements.append(Spacer(1, 6))

            # Trang mới cho mỗi phòng
            if idx < len(df) - 1:
                elements.append(PageBreak())

        doc.build(elements)
        buffer.seek(0)

        st.download_button(
            label="⬇️ Tải file PDF",
            data=buffer,
            file_name=f"phieu_thu_tien_nha_tro_{datetime.now().strftime('%m-%Y')}.pdf",
            mime="application/pdf"
        )
