from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.http import HttpResponseNotFound, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
import csv
import openpyxl
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from mysite.forms import LoginForm
from mysite.mixins import AutoTemplateNameMixin
from mysite.models import Book
from orders.models import Order
from .forms import BookForm, OrderForm


# ==========================================================
# Перевірка доступу до dashboard
# ==========================================================

def is_admin_user(user):
    return (
            user.is_authenticated
            and (
                    user.is_superuser
                    or user.groups.filter(
                name__in=[
                    "ProductManager",
                    "OrderManager"
                ]
            ).exists()
            )
    )


admin_required = user_passes_test(
    is_admin_user,
    login_url='mysite:login'
)


# ==========================================================
# Авторизація в dashboard
# ==========================================================

class AdminLoginView(AutoTemplateNameMixin, View):
    def get(self, request):
        # якщо не увійшов
        if not request.user.is_authenticated:
            return HttpResponseNotFound("<h1>404 Not Found</h1>")
        # якщо вже увійшов
        if request.user.is_authenticated:
            # є доступ → dashboard
            if is_admin_user(request.user):
                return redirect('dashboard:home')

            # немає доступу
            messages.error(
                request,
                "У вас немає доступу до адмін-панелі"
            )

            return redirect('mysite:index')

        form = LoginForm()

        return render(
            request,
            self.template_name,
            {
                'form': form
            }
        )

    def post(self, request):

        form = LoginForm(request.POST)

        if form.is_valid():

            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(
                request,
                username=username,
                password=password
            )

            if user is not None:

                # перевірка доступу
                if is_admin_user(user):
                    login(
                        request,
                        user
                    )

                    return redirect(
                        reverse_lazy(
                            'dashboard:home'
                        )
                    )

                messages.error(
                    request,
                    "У вас немає прав доступу до адмін-панелі"
                )

                return redirect(
                    reverse_lazy(
                        'mysite:index'
                    )
                )

            messages.error(
                request,
                "Невірний логін або пароль"
            )

        return render(
            request,
            self.template_name,
            {
                'form': form
            }
        )


# ==========================================================
# Dashboard
# ==========================================================

@login_required
@admin_required
def dashboard_home(request):
    user = request.user
    roles = []

    # суперкористувач бачить все
    if user.is_superuser:
        roles = ["orders", "products"]
    else:
        if user.groups.filter(name="OrderManager").exists():
            roles.append("orders")
        if user.groups.filter(name="ProductManager").exists():
            roles.append("products")

    return render(
        request,
        "dashboard/home.html",
        {"roles": roles}
    )



# ==========================================================
# Products
# ==========================================================

@login_required
@admin_required
@permission_required(
    'products.view_product',
    raise_exception=True
)
def product_list(request):
    user = request.user
    roles = []

    # суперкористувач бачить все
    if user.is_superuser:
        roles = ["orders", "products"]
    else:
        if user.groups.filter(name="OrderManager").exists():
            roles.append("orders")
        if user.groups.filter(name="ProductManager").exists():
            roles.append("products")

    books = Book.objects.all()
    return render(
        request,
        "dashboard/product_list.html",
        {"products": books, "roles": roles}
    )



def product_create(request):
    if request.method == "POST":
        form = BookForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("dashboard:products")
    else:
        form = BookForm()
    return render(request, "dashboard/product_form.html", {"form": form})


def product_update(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            form.save()
            return redirect("dashboard:products")
    else:
        form = BookForm(instance=book)
    return render(request, "dashboard/product_form.html", {"form": form})


def product_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        book.delete()
        return redirect("dashboard:products")
    return render(request, "dashboard/product_confirm_delete.html", {"book": book})


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
            book.id,
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
            book.id,
            Paragraph(book.title, styleN),
            Paragraph(book.author, styleN),
            f"{book.price} грн",
            Paragraph(book.category.title if book.category else "", styleN),
            book.stock,
        ])

    table = Table(data, colWidths=[30, 120, 110, 70, 120, 60], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Arial"),
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("BOTTOMPADDING", (0,0), (-1,0), 12),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,1), (-1,-1), colors.beige),
    ]))

    elements.append(table)
    doc.build(elements)

    return response

# ==========================================================
# Orders
# ==========================================================

@login_required
@admin_required
@permission_required(
    'orders.view_order',
    raise_exception=True
)
def order_list(request):
    orders = Order.objects.all().order_by('-created_at')  # новіші зверху
    user = request.user
    roles = []

    # суперкористувач бачить все
    if user.is_superuser:
        roles = ["orders", "products"]
    else:
        if user.groups.filter(name="OrderManager").exists():
            roles.append("orders")
        if user.groups.filter(name="ProductManager").exists():
            roles.append("products")

    paginator = Paginator(orders, 10)  # ✅ 10 замовлень на сторінку
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "dashboard/order_list-dashboard.html",
        {"page_obj": page_obj, "orders": page_obj, "roles": roles}
    )



def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, "dashboard/order_detail-dashboard.html", {"order": order})


def order_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return redirect("dashboard:orders")
    else:
        form = OrderForm(instance=order)
    return render(request, "dashboard/order_form.html", {"form": form, "order": order})


def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        order.delete()
        messages.success(request, f"Замовлення №{pk} успішно видалено")
        return redirect("dashboard:orders")
    return redirect("dashboard:orders")

