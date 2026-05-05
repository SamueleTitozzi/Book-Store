from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LogoutView
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.templatetags.static import static
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView, TemplateView

from .forms import LoginForm, RegisterForm
from .mixins import AutoTemplateNameMixin
from orders.models import Order, OrderItem
from .models import Category, Book


# section HomePage -----------------------------------------------------------------------------------------------------
class BookListView(ListView):
    model = Book
    context_object_name = 'books'
    template_name = 'mysite/base.html'


class HomeView(AutoTemplateNameMixin, ListView):
    model = Book
    context_object_name = 'books'

    def get_queryset(self):
        return Book.objects.order_by('-id')[:8]


# ----------------------------------------------------------------------------------------------------------------------

# Section User ------------------------------------------------------------------------------------------------------
class UserLoginView(AutoTemplateNameMixin, View):

    def get(self, request):
        form = LoginForm()
        return render(request, self.get_template_names()[0], {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('mysite:index')
            else:
                messages.error(request, 'Невірний логін або пароль')
        return render(request, self.get_template_names()[0], {'form': form})


class RegisterView(AutoTemplateNameMixin, View):

    def get(self, request):
        form = RegisterForm()
        return render(request, self.get_template_names()[0], {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            email = form.cleaned_data['email']

            user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name,
                                            last_name=last_name)

            messages.success(request, 'Реєстрація пройшла успішно!')
            if user is not None:
                login(request, user)
                return redirect('mysite:index')
            else:
                messages.error(request, 'Помилка входу після реєстрації')
        return render(request, self.get_template_names()[0], {'form': form})


class UserLogoutView(LogoutView):
    next_page = 'mysite:index'


# ---------------------------------------------------------------------------------------------------------------------

# section Category -----------------------------------------------------------------------------------------------------
class CategoryListView(AutoTemplateNameMixin, ListView):
    model = Category
    context_object_name = 'categories'


class SingleCategoryView(AutoTemplateNameMixin, ListView):
    model = Book
    context_object_name = 'books'

    def get_queryset(self):
        return Book.objects.filter(category__pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_category = get_object_or_404(Category, pk=self.kwargs['pk'])
        context['category'] = current_category

        # логіка для наступної категорії
        next_category = Category.objects.filter(pk__gt=current_category.pk).order_by('pk').first()

        if not next_category:
            next_category = Category.objects.order_by('pk').first()

        context['next_category'] = next_category
        return context


class SingleBookInfoView(AutoTemplateNameMixin, DetailView):
    model = Book
    context_object_name = 'book'


# ---------------------------------------------------------------------------------------------------------------------

# # section basket ------------------------------------------------------------------------------------------------------
# class AddToCartView(LoginRequiredMixin, View):
#
#     def post(self, request, *args, **kwargs):
#         book_id = kwargs.get('pk')
#         book = get_object_or_404(Book, pk=book_id)
#
#         order, _ = Order.objects.get_or_create(user=request.user, is_paid=False)
#
#         order_item, created = OrderItem.objects.get_or_create(order=order, book=book)
#
#         if not created:
#             order_item.quantity += 1
#             order_item.save()
#
#         return redirect('mysite:book-detail', pk=book_id)
#
#
# class CartView(AutoTemplateNameMixin, LoginRequiredMixin, TemplateView):
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         order = Order.objects.filter(user=self.request.user, is_paid=False).first()
#         context['order'] = order
#         return context
#
#
# class ResetCartView(LoginRequiredMixin, View):
#
#     def post(self, request):
#         order = Order.objects.filter(user=self.request.user, is_paid=False).first()
#
#         if order:
#             order.delete()
#
#         return redirect('mysite:cart')
#
#
# class DecreaseQuantityView(LoginRequiredMixin, View):
#
#     def post(self, request, *args, **kwargs):
#         item_id = kwargs.get('pk')
#
#         order_item = get_object_or_404(OrderItem, pk=item_id, order__user=request.user, order__is_paid=False)
#
#         if order_item.quantity > 1:
#             order_item.quantity -= 1
#             order_item.save()
#         else:
#             order_item.delete()
#         return redirect('mysite:cart')
#
#
# class AddQuantityView(LoginRequiredMixin, View):
#
#     def post(self, request, *args, **kwargs):
#         item_id = kwargs.get('pk')
#
#         order_item = get_object_or_404(OrderItem, pk=item_id, order__user=request.user, order__is_paid=False)
#
#         order_item.quantity += 1
#         order_item.save()
#         return redirect('mysite:cart')
#
#
# class OrderHistoryView(AutoTemplateNameMixin, LoginRequiredMixin, ListView):
#     model = Order
#     context_object_name = 'orders'
#
#     def get_queryset(self):
#         return Order.objects.filter(user=self.request.user, is_paid=True).order_by('-id')
#
#
# # ---------------------------------------------------------------------------------------------------------------------

# section Search ------------------------------------------------------------------------------------------------------
class SearchView(AutoTemplateNameMixin, ListView):
    model = Book
    context_object_name = 'books'

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()

        if query:
            return Book.objects.filter(Q(title__icontains=query) | Q(author__icontains=query))
        return Book.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        return context


class LiveSearchView(View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'results': []})

        books = Book.objects.filter(title__icontains=query).only('id', 'title', 'image_path')[:5]

        results = []

        for book in books:
            results.append({
                'title': book.title,
                'image': static(f'{book.image_path}') if book.image_path else '',
                'id': book.pk,
            })

        return JsonResponse({'results': results})


# ---------------------------------------------------------------------------------------------------------------------


# section Payment ------------------------------------------------------------------------------------------------------
# class CreatePaymentView(LoginRequiredMixin, View):
#
#     def post(self, request, *args, **kwargs):
#         try:
#             order = Order.objects.get(user=request.user, is_paid=False)
#             if not order.items.exists():
#                 return JsonResponse({'error': 'Cart is empty'}, status=400)
#         except Order.DoesNotExist:
#             return JsonResponse({'error': 'Cart is empty'}, status=400)
#         total = order.get_total_price()
#         if total <= 0:
#             return JsonResponse({'error': 'Value is 0'}, status=400)
#         cents = int(total * Decimal('100'))
#         stripe.api_key = settings.STRIPE_SECRET_KEY
#         try:
#             intent = stripe.PaymentIntent.create(amount=cents, currency='usd', metadata={
#                 'order_id': order.pk,
#                 'user_id': request.user.id,
#             })
#             order.stripe_payment_intent = intent.id
#             order.save()
#         except stripe.error.StripeError as e:
#             return JsonResponse({'error': str(e)}, status=400)
#         return JsonResponse({'client_secret': intent.client_secret})
#
#
# class CheckoutView(LoginRequiredMixin, View):
#
#     def get(self, request):
#         return render(request, 'mysite/checkout.html', {
#             'stripe_public_key': settings.STRIPE_PUBLIC_KEY
#         })
#
#
# @method_decorator(csrf_exempt, name='dispatch')
# class StripeWebhookView(View):
#     def post(self, request, *args, **kwargs):
#         payload = request.body
#         sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
#
#         try:
#             event = stripe.Webhook.construct_event(
#                 payload,
#                 sig_header,
#                 settings.STRIPE_WEBHOOK_SECRET
#             )
#         except stripe.error.SignatureVerificationError:
#             return HttpResponse(status=400)
#
#         if event['type'] == 'payment_intent.succeeded':
#             intent = event['data']['object']
#             metadata = intent.get('metadata', {})
#             order_id = metadata.get('order_id')
#
#             print("Webhook event type:", event['type'])
#             print("Webhook metadata:", metadata)
#             print("Order ID from Stripe:", order_id)
#
#             if not order_id:
#                 return HttpResponse(status=200)
#
#             try:
#                 order = Order.objects.get(id=order_id)
#
#                 if order.is_paid:
#                     print(f"Order {order_id} is already paid")
#                     return HttpResponse(status=200)
#
#                 if not order.is_paid:
#                     order.is_paid = True
#                     order.save()
#                     print(f"Order {order_id} marked as paid")
#
#
#             except Order.DoesNotExist:
#                 print(f"Order {order_id} does not exist")
#                 return HttpResponse(status=200)
#
#         return HttpResponse(status=200)

# ---------------------------------------------------------------------------------------------------------------------
