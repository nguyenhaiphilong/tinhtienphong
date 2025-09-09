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

# ------------------ Helpers ------------------
def parse_room(name):
    s = str(name).strip()
    m = re.match(r"^(\d+)\s*([A-Za-z]*)$", s)
    if m:
        num = int(m.group(1))
        suf = (m.group(2) or "").upper()
        return num, suf
    return 9999, s

def format_currency(value):
    try:
        v = float(value)
    except:
        return str(value)
    return f"{v:,.0f} đ".replace(",", ".")

def build_sort_rank(df):
    # parse num & suffix
    df['__num'] = df['Phòng'].apply(lambda x: parse_room(x)[0])
    df['__suf'] = df['Phòng'].apply(lambda x: parse_room(x)[1])
    # lấy danh sách suffix có (không tính '')
    suffixes = sorted(list(set([s for s in df['__suf'].unique() if s != ""])))
    # rank map: '' -> 0, suffixes in alphabetical order -> 1,2,3...
    rank_map = {"": 0}
    for i, s in enumerate(suffixes):
        rank_map[s] = i + 1
    df['__rank'] = df['__suf'].map(lambda x: rank_map.get(x, 9999))
    # sort theo rank rồi theo số
    df_sorted = df.sort_values(['__rank', '__num']).reset_index(drop=True)
    return df_sorted

# ------------------ Session ------------------
if "ds_phong" not in st.session_state:
    st.session_state["ds_phong"] = []

if "config" not in st.session_state:
    st.session_state["config"] = {
        "TIEN_PHONG": 2100000,
        "GIA_DIEN": 3500,
        "GIA_NUOC": 20000,
        "TIEN_RAC": 10000,
    }

st.title("🏠 Quản lý tiền phòng trọ")

# ---------- Sidebar: cấu hình ----------
st.sidebar.header("⚙️ Cấu hình giá")
st.session_state["config"]["TIEN_PHONG"] = st.sidebar.number_input(
    "💵 Tiền phòng cố định", min_value=0, step=1000, value=st.session_state["config"]["TIEN_PHONG"]
)
st.session_state["config"]["GIA_DIEN"] = st.sidebar.number_input(
    "🔌 Giá điện (đ/kWh)", min_value=0, step=100, value=st.session_state["config"]["GIA_DIEN"]
)
st.session_state["config"]["GIA_NUOC"] = st.sidebar.number_input(
    "🚰 Giá nước (đ/m³)", min_value=0, step=1000, value=st.session_state["config"]["GIA_NUOC"]
)
st.session_state["config"]["TIEN_RAC"] = st.sidebar.number_input(
    "🗑️ Tiền rác", min_value=0, step=1000, value=st.session_state["config"]["TIEN_RAC"]
)

# ---------- Nhập dữ liệu phòng ----------
st.header("➕ Nhập thông tin phòng")

ten_phong = st.text_input("Tên phòng")

dien_cu = st.number_input("Chỉ số điện cũ", min_value=0, step=1)
dien_moi_input = st.number_input("Chỉ số điện mới", min_value=0, step=1)
# xử lý quay vòng: cộng 1000 nếu mới < cũ
dien_moi_thuc = dien_moi_input if dien_moi_input >= dien_cu else dien_moi_input + 1000
so_dien = max(0, dien_moi_thuc - dien_cu)
tien_dien = so_dien * st.session_state["config"]["GIA_DIEN"]

nuoc_cu = st.number_input("Chỉ số nước cũ", min_value=0, step=1)
nuoc_moi_input = st.number_input("Chỉ số nước mới", min_value=0, step=1)
nuoc_moi_thuc = nuoc_moi_input if nuoc_moi_input >= nuoc_cu else nuoc_moi_input + 1000
so_nuoc = max(0, nuoc_moi_thuc - nuoc_cu)
tien_nuoc = so_nuoc * st.session_state["config"]["GIA_NUOC"]

tong = st.session_state["config"]["TIEN_PHONG"] + tien_dien + tien_nuoc + st.session_state["config"]["TIEN_RAC"]

if st.button("💾 Lưu phòng"):
    if ten_phong.strip() == "":
        st.warning("⚠️ Bạn phải nhập tên phòng trước khi lưu!")
    else:
        record = {
            "Phòng": ten_phong.strip(),
            "Tiền phòng": st.session_state["config"]["TIEN_PHONG"],
            "Đơn giá điện": st.session_state["config"]["GIA_DIEN"],
            "Số điện cũ": dien_cu,
            "Số điện mới": dien_moi_input,
            "Số điện sử dụng (kWh)": so_dien,
            "Tiền điện": tien_dien,
            "Đơn giá nước": st.session_state["config"]["GIA_NUOC"],
            "Số nước cũ": nuoc_cu,
            "Số nước mới": nuoc_moi_input,
            "Số nước sử dụng (m³)": so_nuoc,
            "Tiền nước": tien_nuoc,
            "Tiền rác": st.session_state["config"]["TIEN_RAC"],
            "Tổng tiền": tong
        }
        # cập nhật nếu trùng tên (ghi đè) hoặc thêm mới
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

# ---------- Hiển thị & xuất ----------
if st.session_state["ds_phong"]:
    df = pd.DataFrame(st.session_state["ds_phong"])

    # tạo cột số & suffix và rank theo nhóm (sắp xếp theo yêu cầu)
    df_sorted = build_sort_rank(df)

    # chuẩn bị hiển thị (format tiền)
    df_display = df_sorted.copy()
    money_cols = ["Tiền phòng", "Đơn giá điện", "Tiền điện", "Đơn giá nước", "Tiền nước", "Tiền rác", "Tổng tiền"]
    for col in money_cols:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(format_currency)

    st.header("📊 Bảng tổng hợp tiền phòng (đã sắp xếp theo quy tắc)")
    st.dataframe(df_display.drop(columns=['__num','__suf','__rank'], errors='ignore'))

    # tổng
    tong_tien_all = df_sorted["Tổng tiền"].sum()
    st.subheader(f"💰 Tổng thu tất cả phòng: {format_currency(tong_tien_all)}")

    # ----- Xuất PDF cho tất cả phòng -----
    if st.button("🧾 Xuất PDF (tất cả phòng)"):
        pdf_buffer = io.BytesIO()
        thermal_width = 58 * mm
        thermal_height = 100 * mm
        doc = SimpleDocTemplate(
            pdf_buffer,
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

        # duyệt theo df_sorted để đảm bảo thứ tự đúng
        for idx, row in df_sorted.iterrows():
            # Tiêu đề
            elements.append(Paragraph(f"<b>PHIẾU THU TIỀN PHÒNG {row['Phòng'].upper()}</b>", styles["BillTitle"]))
            elements.append(Spacer(1, 6))

            # Nội dung từng dòng
            elements.append(Paragraph(f"Tiền phòng: {format_currency(row['Tiền phòng'])}", styles["Normal"]))
            elements.append(Spacer(1, 6))

            elements.append(Paragraph(f"Điện cũ: {row['Số điện cũ']}", styles["Normal"]))
            elements.append(Paragraph(f"Điện mới: {row['Số điện mới']}", styles["Normal"]))
            elements.append(Paragraph(f"Tiêu thụ: {row['Số điện sử dụng (kWh)']} kWh", styles["Normal"]))
            elements.append(Paragraph(f"Tiền điện: {format_currency(row['Tiền điện'])}", styles["Normal"]))
            elements.append(Spacer(1, 6))

            elements.append(Paragraph(f"Nước cũ: {row['Số nước cũ']}", styles["Normal"]))
            elements.append(Paragraph(f"Nước mới: {row['Số nước mới']}", styles["Normal"]))
            elements.append(Paragraph(f"Tiêu thụ: {row['Số nước sử dụng (m³)']} m³", styles["Normal"]))
            elements.append(Paragraph(f"Tiền nước: {format_currency(row['Tiền nước'])}", styles["Normal"]))
            elements.append(Spacer(1, 6))

            elements.append(Paragraph(f"Tiền rác: {format_currency(row['Tiền rác'])}", styles["Normal"]))
            elements.append(Spacer(1, 6))

            elements.append(Paragraph(f"<b>TỔNG CỘNG:</b>", styles["TotalBold"]))
            elements.append(Paragraph(f"{format_currency(row['Tổng tiền'])}", styles["TotalNum"]))
            elements.append(Spacer(1, 6))

            # Trang mới cho mỗi phòng
            if idx < len(df_sorted) - 1:
                elements.append(PageBreak())

        doc.build(elements)
        pdf_buffer.seek(0)
        st.download_button(
            "⬇️ Tải PDF (tất cả phòng)",
            pdf_buffer,
            f"Tien_tro_thang_{datetime.now().strftime('%m-%Y')}.pdf",
            "application/pdf"
        )
