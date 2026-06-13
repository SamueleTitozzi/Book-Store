from django.urls import path

from django.conf import settings
from django.conf.urls.static import static

from .views import (
    BookListView,
    CategoryListView,
    LiveSearchView,
    RegisterView,
    SearchView,
    SingleBookInfoView,
    SingleCategoryView,
    UserLoginView,
    UserLogoutView,
)

app_name = 'mysite'

urlpatterns = [
    path('', BookListView.as_view(), name='index'),
    path('category/', CategoryListView.as_view(), name='category'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', UserLogoutView.as_view(next_page='mysite:index'), name='logout'),
    path('category/<int:pk>/', SingleCategoryView.as_view(), name='single_category'),
    path('book/<int:pk>/', SingleBookInfoView.as_view(), name='book-detail'),
    path('search/', SearchView.as_view(), name='search'),
    path('live-search/', LiveSearchView.as_view(), name='live-search'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
