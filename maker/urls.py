from django.urls import path

from . import views

app_name = "maker"

urlpatterns = [
    path("season/current/", views.CurrentSeasonView.as_view(), name="season-current"),
    path("rankings/", views.RankingView.as_view(), name="rankings"),
    path("components/", views.ComponentListView.as_view(), name="component-list"),
    path("products/<int:pk>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("items/", views.ItemListCreateView.as_view(), name="item-create"),
    path("items/<int:pk>/", views.ItemDetailView.as_view(), name="item-detail"),
    path("recommend/", views.RecommendView.as_view(), name="recommend"), # AI 노리개 추천 
    path("items/<int:pk>/recommend-products/", views.ProductRecommendView.as_view(), name="item-recommend-products"), # AI MCM 상품 추천
]