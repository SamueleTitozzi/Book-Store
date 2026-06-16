"""
URL configuration for base project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from mysite.views import UserLoginView, RegisterView, UserLogoutView
from dashboard.views import AdminLoginView
from django.contrib.auth.decorators import user_passes_test

def is_admin_user(user):
    return (user.is_superuser or user.groups.filter(name__in=["ProductManager", "OrderManager"]).exists())

urlpatterns = [
    path('admin/', admin.site.urls),

    # застосунки
    path('', include('mysite.urls', namespace='mysite')),
    path('orders/', include('orders.urls', namespace='orders')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),

    # авторизація
    path('login/', UserLoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', UserLogoutView.as_view(next_page='mysite:index'), name='logout'),

    # адмінка
    path('admin-login/', AdminLoginView.as_view(), name='admin-login'),
]
