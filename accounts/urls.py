from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, SignupView, SocialLoginView
from .views import ProfileView, NicknameUpdateView, LogoutView, WithdrawView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("social/<str:provider>/", SocialLoginView.as_view(), name="social-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", ProfileView.as_view(), name="profile"),
    path("me/nickname/", NicknameUpdateView.as_view(), name="nickname-update"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("withdraw/", WithdrawView.as_view(), name="withdraw"),
]