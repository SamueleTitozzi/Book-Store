from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.contrib import messages
from django.template.context_processors import csrf
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import AuthenticationForm
from django.template.context_processors import csrf
from dashboard.services.services import get_user_roles
from dashboard.decorators import admin_required
from dashboard.forms import BookForm
from mysite.mixins import AutoTemplateNameMixin
from mysite.models import Book



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
    roles = get_user_roles(request.user)

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

# ==========================================================