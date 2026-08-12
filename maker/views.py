from rest_framework import generics

from .models import Component, Item, Product, Season
from .serializers import (
    ComponentSerializer,
    ItemSerializer,
    ProductSerializer,
    SeasonSerializer,
)


class CurrentSeasonView(generics.RetrieveAPIView):
    serializer_class = SeasonSerializer
    queryset = Season.objects.all()


class RankingView(generics.ListAPIView):
    serializer_class = ItemSerializer
    queryset = Item.objects.none()  # 집계 로직 붙이기 전 임시


class ComponentListView(generics.ListAPIView):
    serializer_class = ComponentSerializer

    def get_queryset(self):
        qs = Component.objects.all()
        component_type = self.request.query_params.get("type")
        if component_type:
            qs = qs.filter(type=component_type)
        return qs


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()


class ItemCreateView(generics.CreateAPIView):
    serializer_class = ItemSerializer
    queryset = Item.objects.all()