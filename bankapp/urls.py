# bankapp/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views # Built-in Login/Logout
from . import views

# bankapp/urls.py
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('signup/', views.signup_view, name='signup'),  # Only keep this one
    path('deposit/', views.deposit_view, name='deposit'),
    path('withdraw/', views.withdraw_view, name='withdraw'),
    path('transfer/', views.transfer_view, name='transfer'),
    path('apply-interest/', views.apply_interest, name='apply_interest'),
    path('history/', views.transaction_history, name='history'),
    path('receipt/<int:transaction_id>/', views.transaction_receipt, name='receipt'),
    path('profile/', views.profile_view, name='profile'),
    path('print-statement/', views.print_statement, name='print_statement'),
    path('apply-loan/', views.apply_loan_view, name='apply_loan'),  # Apply for a loan
    path('my-loans/', views.my_loans_view, name='my_loans'),        # View your loans        # User views all their loans
    path("mobile-recharge/", views.mobile_recharge_view, name="mobile_recharge"),
]