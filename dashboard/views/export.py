from django.http import HttpResponse
import csv
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from mysite.models import Book

# ==========================================================
# Export Information
# ==========================================================


def export_books_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="books.csv"'

    response.write(u'\ufeff'.encode('utf-8'))

    writer = csv.writer(response, delimiter=';')
    writer.writerow(["ID", "Назва", "Автор", "Ціна", "Категорія", "На складі", "Статус"])

    for book in Book.objects.all():
        writer.writerow([
            book.id,
            book.title,
            book.author,
            book.price,
            book.category.title if book.category else "",
            book.stock,
        ])

    return response


def export_books_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Books"

    ws.append(["ID", "Назва", "Автор", "Ціна", "Категорія", "На складі", "Статус"])

    for book in Book.objects.all():
        ws.append([
            book.pk,
            book.title,
            book.author,
            book.price,
            book.category.title if book.category else "",
            book.stock,
        ])

    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename="books.xlsx"'
    wb.save(response)
    return response


def export_books_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="books.pdf"'

    # реєструємо Arial із системної папки Windows
    pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleN.fontName = "Arial"
    styles["Title"].fontName = "Arial"

    elements.append(Paragraph("Список книг", styles["Title"]))
    elements.append(Spacer(1, 12))

    data = [["ID", "Назва", "Автор", "Ціна", "Категорія", "На складі", "Статус"]]

    for book in Book.objects.all():
        data.append([
            book.pk,
            Paragraph(book.title, styleN),
            Paragraph(book.author, styleN),
            f"{book.price} грн",
            Paragraph(book.category.title if book.category else "", styleN),
            book.stock,
        ])

    table = Table(data, colWidths=[30, 120, 110, 70, 120, 60], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Arial"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
    ]))

    elements.append(table)
    doc.build(elements)

    return response