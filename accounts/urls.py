from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, SignupView, SocialLoginView
from .views import ProfileView, NicknameUpdateView, LogoutView, WithdrawView
from .views import (
    ProfileView, NicknameUpdateView, LogoutView, WithdrawView,
    MyReservationListView, ReservationDetailView,
    MyItemListView, MyItemDetailView,
    OwnershipListCreateView,
    WishlistListCreateView, WishlistDeleteView,
)
from .views import PasswordChangeView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("social/<str:provider>/", SocialLoginView.as_view(), name="social-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", ProfileView.as_view(), name="profile"),
    path("me/nickname/", NicknameUpdateView.as_view(), name="nickname-update"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("withdraw/", WithdrawView.as_view(), name="withdraw"),
    path("me/reservations/", MyReservationListView.as_view(), name="my-reservations"),
    path("me/reservations/<int:pk>/", ReservationDetailView.as_view(), name="reservation-detail"),
    path("me/items/", MyItemListView.as_view(), name="my-items"),
    path("me/items/<int:pk>/", MyItemDetailView.as_view(), name="my-item-detail"),
    path("me/ownerships/", OwnershipListCreateView.as_view(), name="ownerships"),
    path("me/wishlist/", WishlistListCreateView.as_view(), name="wishlist"),
    path("me/wishlist/<int:pk>/", WishlistDeleteView.as_view(), name="wishlist-delete"),
    path("me/password/", PasswordChangeView.as_view(), name="password-change"),
]