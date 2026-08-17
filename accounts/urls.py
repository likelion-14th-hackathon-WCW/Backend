from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, SignupView, SocialLoginView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("social/<str:provider>/", SocialLoginView.as_view(), name="social-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]