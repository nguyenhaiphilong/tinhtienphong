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
from reportlab.platypus import KeepTogether

# ===== ĐĂNG KÝ FONT ARIAL =====
pdfmetrics.registerFont(TTFont("Arial", "fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "fonts/arialbd.ttf"))

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
    return f"{v:,.0f}đ".replace(",", ".")

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
        "TIEN_THEM": 300000,
    }

st.title("🏠 Quản lý tiền phòng trọ")

# ---------- Sidebar: cấu hình ----------
st.sidebar.header("⚙️ Cấu hình giá")
st.session_state["config"]["TIEN_PHONG"] = st.sidebar.number_input(
    "💵 Tiền phòng cố định", min_value=0, step=100000, value=st.session_state["config"]["TIEN_PHONG"]
)
st.session_state["config"]["GIA_DIEN"] = st.sidebar.number_input(
    "🔌 Giá điện (đ/kWh)", min_value=0, step=100, value=st.session_state["config"]["GIA_DIEN"]
)
st.session_state["config"]["GIA_NUOC"] = st.sidebar.number_input(
    "🚰 Giá nước (đ/m³)", min_value=0, step=10000, value=st.session_state["config"]["GIA_NUOC"]
)
st.session_state["config"]["TIEN_RAC"] = st.sidebar.number_input(
    "🗑️ Tiền rác", min_value=0, step=10000, value=st.session_state["config"]["TIEN_RAC"]
)
st.session_state["config"]["TIEN_THEM"] = st.sidebar.number_input(
    "➕ Tiền thêm (phụ phí)", min_value=0, step=100000, value=st.session_state["config"]["TIEN_THEM"]
)

# ---------- Nhập dữ liệu phòng ----------
st.header("➕ Nhập thông tin phòng")

ten_phong = st.text_input("Tên phòng")

dien_cu = st.number_input("Chỉ số điện cũ", min_value=0, step=1)
nuoc_cu = st.number_input("Chỉ số nước cũ", min_value=0, step=1)
dien_moi_input = st.number_input("Chỉ số điện mới", min_value=0, step=1)
# xử lý quay vòng: cộng 1000 nếu mới < cũ
dien_moi_thuc = dien_moi_input if dien_moi_input >= dien_cu else dien_moi_input + 1000
so_dien = max(0, dien_moi_thuc - dien_cu)
tien_dien = so_dien * st.session_state["config"]["GIA_DIEN"]

nuoc_moi_input = st.number_input("Chỉ số nước mới", min_value=0, step=1)
nuoc_moi_thuc = nuoc_moi_input if nuoc_moi_input >= nuoc_cu else nuoc_moi_input + 1000
so_nuoc = max(0, nuoc_moi_thuc - nuoc_cu)
tien_nuoc = so_nuoc * st.session_state["config"]["GIA_NUOC"]
co_tien_them = st.checkbox(f"Có thêm phụ phí")
tien_them = st.session_state["config"]["TIEN_THEM"] if co_tien_them else 0

tong = st.session_state["config"]["TIEN_PHONG"] + tien_dien + tien_nuoc + st.session_state["config"]["TIEN_RAC"] + tien_them

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
            "Tiền thêm": tien_them,
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
    df_sorted = build_sort_rank(df)
    df_display = df_sorted.copy()
    money_cols = ["Tiền phòng", "Đơn giá điện", "Tiền điện", "Đơn giá nước", "Tiền nước", "Tiền rác", "Tiền thêm",  "Tổng tiền"]
    for col in money_cols:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(format_currency)

    st.header("📊 Bảng tổng hợp tiền phòng (đã sắp xếp theo quy tắc)")
    st.dataframe(df_display.drop(columns=['__num','__suf','__rank'], errors='ignore'))

    # tổng
    tong_tien_all = df_sorted["Tổng tiền"].sum()
    st.subheader(f"💰 Tổng thu tất cả phòng: {format_currency(tong_tien_all)}")

    # ----- Xuất PDF cho tất cả phòng -----
    if st.button("🧾 Xuất Hóa Đơn (Tất cả các phòng)"):
        pdf_buffer = io.BytesIO()
        thermal_width = 58 * mm
        thermal_height = 107 * mm
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=(thermal_width, thermal_height),
            leftMargin=5 * mm,
            rightMargin=5 * mm,
            topMargin=2 * mm,
            bottomMargin=5 * mm
        )
        elements = []

        # Style setup
        styles = getSampleStyleSheet()
        styles["Normal"].fontName = "Arial"
        styles["Normal"].fontSize = 10
        styles["Normal"].spaceAfter = 0
        styles.add(ParagraphStyle(name="Date", fontName="Arial", fontSize=11, alignment=1, spaceAfter=8))
        styles.add(ParagraphStyle(name="BillTitle", fontName="Arial-Bold", fontSize=13, alignment=1, spaceAfter=8))
        styles.add(ParagraphStyle(name="TotalBold", fontName="Arial-Bold", fontSize=12, alignment=1, spaceAfter=8))
        styles.add(ParagraphStyle(name="TotalNum", fontName="Arial-Bold", fontSize=16, alignment=1, spaceAfter=8))

        # duyệt theo df_sorted để đảm bảo thứ tự đúng
        for idx, row in df_sorted.iterrows():
            # Tiêu đề
            elements.append(Paragraph(f"<b>PHIẾU THU TIỀN PHÒNG {row['Phòng'].upper()}</b>", styles["BillTitle"]))
            elements.append(Spacer(1, 6))

            # Nội dung từng dòng
            elements.append(Paragraph(f"Ngày: {datetime.now().strftime('%d/%m/%Y')}", styles["Date"]))
            elements.append(Spacer(1, 6))

            # Bảng chi tiết
            data = [
                ["Tên DV", "T.thụ", "T.Tiền"],
                ["T.Phòng", "", format_currency(row["Tiền phòng"])],
                ["Điện", f"{row['Số điện sử dụng (kWh)']}x{format_currency(row['Đơn giá điện'])}", format_currency(row["Tiền điện"])],
                ["Nước", f"{row['Số nước sử dụng (m³)']}x{format_currency(row['Đơn giá nước'])}", format_currency(row["Tiền nước"])],
                ["Rác", "", format_currency(row["Tiền rác"])],
            ]
            if row.get("Tiền thêm", 0) > 0:
                data.append(["Phụ phí", "", format_currency(row["Tiền thêm"])])
            
            table = Table( data, colWidths=[17*mm, 19*mm, 22*mm])
            
            table.setStyle(TableStyle([
                ("FONTNAME", (0,0), (-1,-1), "Arial"),
                ("FONTSIZE", (0,0), (-1,-1), 9.8),
                ("ALIGN", (0,0), (0,-1), "LEFT"),
                ("ALIGN", (1,0), (1,-1), "CENTER"),
                ("ALIGN", (2,0), (2,-1), "RIGHT"),
                ("LINEBELOW", (0,0), (-1,0), 0.5, colors.black),
                ("LINEAFTER", (0,0), (0,-1), 0.25, colors.black),
                ("LINEAFTER", (1,0), (1,-1), 0.25, colors.black),
                ]))
            
            elements.append(table)
            elements.append(Spacer(1, 6))
            
            elements.append(Paragraph(f"<b>TỔNG CỘNG:</b>", styles["TotalBold"]))
            elements.append(Paragraph(f"{format_currency(row['Tổng tiền'])}", styles["TotalNum"]))
            elements.append(Spacer(1, 6))

            data1 = [
                ["", "Cũ", "Mới"],
                ["Điện", f"{row['Số điện cũ']}", f"{row['Số điện mới']}"],
                ["Nước", f"{row['Số nước cũ']}", f"{row['Số nước mới']}"]
            ]
            table1 = Table( data1, colWidths=[15*mm, 17*mm, 18*mm])
            table1.setStyle(TableStyle([
                ("FONTNAME", (0,0), (-1,-1), "Arial"),
                ("FONTSIZE", (0,0), (-1,-1), 10),
                ("ALIGN", (0,0), (0,-1), "LEFT"),
                ("ALIGN", (1,0), (1,-1), "CENTER"),
                ("ALIGN", (2,0), (2,-1), "RIGHT"),
                ("LINEBELOW", (0,0), (-1,0), 0.5, colors.black),
            ]))
            elements.append(KeepTogether(table1))
            elements.append(Spacer(1, 6))
            
            # Trang mới cho mỗi phòng
            if idx < len(df_sorted) - 1:
                elements.append(PageBreak())

        doc.build(elements)
        pdf_buffer.seek(0)
        st.download_button(
            "⬇️ Tải Hóa Đơn",
            pdf_buffer,
            f"Tien_tro_thang_{datetime.now().strftime('%m-%Y')}.pdf",
            "application/pdf"
        )
    # ----- Xuất PDF tổng hợp tiền phòng -----
    if st.button("🧾 Xuất tổng hợp tiền phòng"):
        pdf_buffer1 = io.BytesIO()
        thermal_width = 58 * mm
        thermal_height = 107 * mm
        doc1 = SimpleDocTemplate(
            pdf_buffer1,
            pagesize=(thermal_width, thermal_height),
            leftMargin=5 * mm,
            rightMargin=5 * mm,
            topMargin=2 * mm,
            bottomMargin=5 * mm
        )
        elements1 = []
        styles = getSampleStyleSheet()
        styles["Normal"].fontName = "Arial"
        styles["Normal"].fontSize = 10
        styles["Normal"].spaceAfter = 0
        styles.add(ParagraphStyle(name="Mytitle", fontName="Arial-Bold", fontSize=13, alignment=1, spaceAfter=8))
        elements1.append(Paragraph(f"DANH SÁCH TIỀN PHÒNG - {datetime.now().strftime('%m/%Y')}", styles["Mytitle"]))
        elements1.append(Spacer(1, 12))
        data_summary = [["Phòng", "Tiền phòng", "Ghi chú"]]
        for idx, row in df_sorted.iterrows():
            data_summary.append([
                row["Phòng"],
                format_currency(row["Tổng tiền"]),
                " "  # Ghi chú để trống
            ])
        table_sum = Table( data_summary, colWidths=[15*mm, 25*mm, 18*mm])
        table_sum.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,-1), "Arial"),
            ("FONTSIZE", (0,0), (-1,-1), 11),
            ("ALIGN", (0,0), (0,-1), "CENTER"),
            ("ALIGN", (1,1), (1,-1), "RIGHT"),
            ("ALIGN", (2,1), (2,-1), "LEFT"),
            ("LINEBELOW", (0,0), (-1,0), 0.5, colors.black),
            ("INNERGRID", (0,0), (-1,-1), 0.25, colors.grey),
            ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ]))
        elements1.append(table_sum)
        elements1.append(Spacer(1, 12))
        doc1.build(elements1)
        pdf_buffer1.seek(0)
        st.download_button(
            "⬇️ Tải PDF Danh sách",
            pdf_buffer1,
            f"Bang_tong_tien_thang_{datetime.now().strftime('%m-%Y')}.pdf",
            "application/pdf"
        )
        

# ----- Xuất Excel -----
if st.button("📥 Xuất Excel quản lí"):
    if not st.session_state["ds_phong"]:
        st.warning("⚠️ Chưa có dữ liệu phòng, không thể xuất Excel!")
    else:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            # ---- Sheet 1: Điện nước ----
            df_sheet1 = pd.DataFrame({
                "Phòng": df_sorted["Phòng"],
                "Điện - Cũ": df_sorted["Số điện cũ"],
                "Điện - Mới": df_sorted["Số điện mới"],
                "Điện - Tiêu thụ": df_sorted["Số điện sử dụng (kWh)"],
                "Nước - Cũ": df_sorted["Số nước cũ"],
                "Nước - Mới": df_sorted["Số nước mới"],
                "Nước - Tiêu thụ": df_sorted["Số nước sử dụng (m³)"],
            })
            df_sheet1.to_excel(writer, index=False, sheet_name="Quản lí điện - nước")

            # ---- Sheet 2: Quản lí tiền phòng ----
            df_sheet2 = pd.DataFrame({
                "Phòng": df_sorted["Phòng"],
                "Tiền phòng": df_sorted["Tổng tiền"].apply(format_currency),
                "Ghi chú": ["" for _ in range(len(df_sorted))],
            })
            df_sheet2.to_excel(writer, index=False, sheet_name="Quản lí tiền phòng")

        excel_buffer.seek(0)
        st.download_button(
            "⬇️ Tải Excel",
            excel_buffer,
            f"Quan_li_phong_tro_thang_{datetime.now().strftime('%m-%Y')}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
