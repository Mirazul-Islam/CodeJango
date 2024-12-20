from django.contrib.auth import views as auth_views
from django.urls import path, include
from challenges.views import home_view
from django.contrib import admin
from challenges.views import register

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),  # Base URL
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
     path('accounts/register/', register, name='register'),
    path('challenges/', include('challenges.urls')),  # Challenges URLs
]
