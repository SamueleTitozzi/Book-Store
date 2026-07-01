from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('products/', views.product_list, name='products'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/update/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('orders/', views.order_list, name='orders'),
    path("books/export/csv/", views.export_books_csv, name="export_books_csv"),
    path("books/export/excel/", views.export_books_excel, name="export_books_excel"),
    path("books/export/pdf/", views.export_books_pdf, name="export_books_pdf"),




    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/update/', views.order_update, name='order_update'),
    path('orders/<int:pk>/delete/', views.order_delete, name='order_delete'),
]
