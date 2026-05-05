from django.urls import path
from .views import BookListView, CategoryListView, UserLoginView, RegisterView, UserLogoutView, SingleCategoryView, \
    SingleBookInfoView, SearchView, \
    LiveSearchView

from django.conf import settings
from django.conf.urls.static import static


app_name = 'mysite'

urlpatterns = [
    path('', BookListView.as_view(), name='index'),
    path('category/', CategoryListView.as_view(), name='category'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', UserLogoutView.as_view(next_page='mysite:index'), name='logout'),
    path('category/<int:pk>/', SingleCategoryView.as_view(), name='single_category'),
    path('book/<int:pk>/', SingleBookInfoView.as_view(), name='book-detail'),
    # path('add-to-cart/<int:pk>/', AddToCartView.as_view(), name='add_to_cart'),
    # path('cart/', CartView.as_view(), name='cart'),
    # path('cart/reset/', ResetCartView.as_view(), name='cart-reset'),
    # path('cart/decrease/<int:pk>/', DecreaseQuantityView.as_view(), name='cart-decrease'),
    # path('cart/AddQuantity/<int:pk>/', AddQuantityView.as_view(), name='cart-addquantity'),
    path('search/', SearchView.as_view(), name='search'),
    path('live-search/', LiveSearchView.as_view(), name='live-search'),
    # path('create-payment/', CreatePaymentView.as_view(), name='create_payment'),
    # path('checkout/', CheckoutView.as_view(), name='checkout'),
    # path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),
    # path('orders/history/', OrderHistoryView.as_view(), name='order_history'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)