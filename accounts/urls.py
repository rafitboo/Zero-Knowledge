from django.urls import path
from .views import RegisterView, UserProfileView, VerifyOTPView, LoginView, VerifyEmailChangeView, LoginVerifyView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('login/verify/', LoginVerifyView.as_view(), name='login_verify'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('verify-email-change/', VerifyEmailChangeView.as_view(), name='verify-email-change'),
]