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

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services import ai_recommend

from rest_framework.permissions import IsAuthenticated

from django.db.models import Count


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
class RankingView(APIView):
    def get(self, request):
        aggregated = (
            Item.objects
            .values("knot_id", "tassel_id", "decoration_id")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        component_ids = set()
        for row in aggregated:
            component_ids.update([row["knot_id"], row["tassel_id"], row["decoration_id"]])
        names = {c.id: c.name for c in Component.objects.filter(id__in=component_ids)}

        result = []
        for i, row in enumerate(aggregated):
            # 이 조합으로 만든 노리개 중 가장 최근 것 하나를 대표 이미지/제작자로 사용
            sample = (
                Item.objects
                .filter(knot_id=row["knot_id"], tassel_id=row["tassel_id"], decoration_id=row["decoration_id"])
                .select_related("user")
                .order_by("-created_at")
                .first()
            )
            result.append({
                "rank": i + 1,
                "knot_id": row["knot_id"],
                "knot_name": names.get(row["knot_id"]),
                "tassel_id": row["tassel_id"],
                "tassel_name": names.get(row["tassel_id"]),
                "decoration_id": row["decoration_id"],
                "decoration_name": names.get(row["decoration_id"]),
                "count": row["count"],
                "image_url": sample.image_url if sample else None,
                "creator": sample.user.username if sample and sample.user else None,
                "title": sample.title if sample else None,
                "description": sample.description if sample else None,
                "image_url": sample.image_url if sample else None,
                "creator": sample.user.username if sample and sample.user else None,
            })
        return Response(result)

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

    def perform_create(self, serializer):
        # TODO: 기획 답변 오면 교체 (사용자 직접 입력 또는 AI 생성으로)
        knot = serializer.validated_data["knot"]
        decoration = serializer.validated_data["decoration"]
        serializer.save(
            title=f"{knot.name} · {decoration.name}",
            description=None,
        )

# TODO: 로그인 로직 완성되면 추가 수정
class ItemClaimView(APIView):
    permission_classes = [IsAuthenticated]  # 로그인 필수

    def post(self, request, pk):
        try:
            item = Item.objects.get(pk=pk)
        except Item.DoesNotExist:
            return Response({"detail": "노리개를 찾을 수 없습니다."}, status=404)

        if item.user is not None:
            return Response({"detail": "이미 다른 계정에 연결된 노리개입니다."}, status=400)

        item.user = request.user
        item.save()
        return Response(ItemSerializer(item).data)

# =========== MAKE_01 ==============
# ------------ AI 연동 ------------
class RecommendView(APIView):
    def post(self, request):
        keyword = request.data.get("keyword") # 요청 body에서 keyword 꺼내기

        # keyword가 비어있으면 400 에러
        # (기능명세서의 "최대 글자수 제한, 공백 입력 시 에러 메시지" 예외사항 중 일부 처리)
        if not keyword:
            return Response({"keyword": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        exclude_combinations = request.data.get("exclude_combinations", [])

        # 3번 제한: 처음 추천(0개 제외) + 다시 받기 최대 2번 = exclude_combinations가 2개 넘으면 거절
        # (다시 받기 자체를 3번까지 허용하고 싶으면 아래 숫자를 3으로 바꾸기)
        if len(exclude_combinations) >= 3:
            return Response(
                {"detail": "추천은 최대 3번까지만 가능합니다."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            result = ai_recommend.recommend_components(keyword, exclude_combinations)
        except Exception:
            # OpenAI 호출 실패, 타임아웃, AI가 이상한 값을 줘서 검증에 걸린 경우 등
            # 일단 다 503(서비스 이용 불가)으로 처리
            return Response(
                {"detail": "추천 생성에 실패했습니다. 다시 시도해주세요."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(result)


class ProductRecommendView(APIView):
    def get(self, request, pk):
        try:
            # AI가 노리개랑 어울리는 상품 id 목록만 골라줌
            product_ids = ai_recommend.recommend_products(pk)
        except Exception:
            return Response(
                {"detail": "상품 추천에 실패했습니다."}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        products = Product.objects.filter(id__in=product_ids)
        # filter(id__in=...)는 순서를 안 지켜주므로 AI가 정한 순서대로 다시 정렬
        products_by_id = {p.id: p for p in products}
        ordered = [products_by_id[pid] for pid in product_ids if pid in products_by_id]
        return Response(ProductSerializer(ordered, many=True).data)