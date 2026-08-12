from django.urls import path

from . import views

app_name = "maker"

urlpatterns = [
    path("season/current/", views.CurrentSeasonView.as_view(), name="season-current"),
    path("rankings/", views.RankingView.as_view(), name="rankings"),
    path("components/", views.ComponentListView.as_view(), name="component-list"),
    path("products/<int:pk>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("items/", views.ItemCreateView.as_view(), name="item-create"),
]