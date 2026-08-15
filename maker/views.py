from django.utils import timezone

from django.http import Http404
from rest_framework import generics

from .models import Component, Item, Product, Season
from .serializers import (
    ComponentSerializer,
    ItemSerializer,
    ProductSerializer,
    SeasonSerializer,
)


# ============ HOME_01 ==============
# 시즌 상징 조회
class CurrentSeasonView(generics.RetrieveAPIView):
    serializer_class = SeasonSerializer

    def get_object(self):
        today = timezone.now().date()
        # 오늘 날짜가 start_date~end_date 범위 안에 드는 시즌 찾기
        season = Season.objects.filter(
            start_date__lte=today, end_date__gte=today
        ).first()
        if season is None:
            raise Http404("현재 진행 중인 시즌이 없습니다.")
        return season


# 인기 조합 랭킹
# TODO: Item을 knot/tassel/decoration 조합 기준으로 집계해서 반환하도록 구현 필요
class RankingView(generics.ListAPIView):
    serializer_class = ItemSerializer
    queryset = Item.objects.none()  # TODO: 집계 로직 붙이기 전까지의 임시 빈 쿼리셋

# =========== MAKE_02 ==============

class ComponentListView(generics.ListAPIView):
    serializer_class = ComponentSerializer

    def get_queryset(self):
        qs = Component.objects.all()
        component_type = self.request.query_params.get("type")
        season_id = self.request.query_params.get("season")

        if component_type:
            qs = qs.filter(type=component_type)
        if season_id:
            qs = qs.filter(season=season_id)
        return qs


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

# ------------ 노리개 저장 ------------
class ItemCreateView(generics.CreateAPIView):
    serializer_class = ItemSerializer
    queryset = Item.objects.all()

# =========== MAKE_01 ==============
# ------------ AI 연동 ------------
# TODO: services/ai_recommend.py 의 로직을 호출하는 APIView 추가 예정