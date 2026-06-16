from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.urls import reverse_lazy
from django.views import View
from mysite.forms import LoginForm
from mysite.mixins import AutoTemplateNameMixin
from django.http import HttpResponseNotFound
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator

from mysite.models import Book
from orders.models import Order
from .forms import BookForm


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

    return render(
        request,
        'dashboard/home.html'
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
    books = Book.objects.all()
    return render(request, "dashboard/product_list.html", {"products": books})


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
    orders = Order.objects.all().order_by('-created_at')  # сортуємо новіші зверху
    paginator = Paginator(orders, 10)  # ✅ 10 замовлень на сторінку
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "dashboard/order_list-dashboard.html", {"page_obj": page_obj, "orders": page_obj})

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
    return render(request, "dashboard/order_form.html", {"form": form})

def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        order.delete()
        return redirect("dashboard:orders")
    return render(request, "dashboard/order_confirm_delete.html", {"order": order})

