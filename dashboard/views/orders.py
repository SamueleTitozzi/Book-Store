from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from dashboard.decorators import admin_required
from django.http import HttpResponse
from django.contrib import messages
from django.template.context_processors import csrf
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import AuthenticationForm
from django.template.context_processors import csrf
from dashboard.services.services import get_user_roles, is_admin_user
from orders.models import Order
from dashboard.forms import OrderForm
from mysite.mixins import AutoTemplateNameMixin
from django.core.paginator import Paginator


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
    roles = get_user_roles(request.user)

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