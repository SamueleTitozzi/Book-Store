from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/reset/', views.ResetCartView.as_view(), name='cart-reset'),
    path('cart/decrease/<int:pk>/', views.DecreaseQuantityView.as_view(), name='cart-decrease'),
    path('cart/add/<int:pk>/', views.AddQuantityView.as_view(), name='cart-addquantity'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('create-payment/', views.CreatePaymentView.as_view(), name='create_payment'),
    path('stripe/webhook/', views.StripeWebhookView.as_view(), name='stripe_webhook'),
    path('history/', views.OrderHistoryView.as_view(), name='order_history'),
    path('add-to-cart/<int:pk>/', views.AddToCartView.as_view(), name='add_to_cart'),
    path('confirmation/<int:pk>/', views.OrderConfirmationView.as_view(), name='confirmation'),
    path('check-status/<int:pk>/', views.CheckOrderStatusView.as_view(), name='check_status'),
    path('confirm-payment/<int:pk>/', views.ConfirmPaymentView.as_view(), name='confirm_payment'),
    path('detail/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('order/<int:pk>/cancel/', views.CancelOrderView.as_view(), name='cancel_order')
]
