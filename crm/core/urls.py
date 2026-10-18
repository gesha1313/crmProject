from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('residents/', views.residents, name='residents'),
    path('residents/<int:pk>/checkin/', views.resident_checkin, name='resident-checkin'),
    path('residents/<int:pk>/edit/', views.resident_edit, name='resident-edit'),
    path('rooms/', views.rooms, name='rooms'),
    path('payments/', views.payments, name='payments'),
    path('charges/', views.charges, name='charges'),
    path('charges/<int:pk>/edit/', views.charge_edit, name='charge-edit'),
    path('chat/', views.chat, name='chat'),
    path('requests/<int:pk>/edit/', views.request_edit, name='request-edit'),
    path('caretaker/<int:pk>/edit/', views.caretaker_edit, name='caretaker-edit'),
    path('users/<int:pk>/edit/', views.site_user_edit, name='site-user-edit'),
    path('users/', views.users, name='users'),
    path('login/', auth_views.LoginView.as_view(template_name='crm/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
]
