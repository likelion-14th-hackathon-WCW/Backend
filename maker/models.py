from django.db import models
from django.conf import settings

# 시즌 한정
class Season(models.Model):
    # 시즌 한정 COMPONENT
    name = models.CharField(max_length=50, help_text='2026 여름') # 시즌 이름
    start_date = models.DateField() # 시즌 시작일
    end_date = models.DateField() # 시즌 종료일

    class Meta:
        db_table = 'season'

    def __str__(self):
        return self.name

# 노리개 구성요소
class Component(models.Model):
    # 매듭/술/장식(주체) 선택지
    class ComponentType(models.TextChoices):
        KNOT = "knot", "매듭"
        TASSEL = "tassel", "술"
        DECORATION = "decoration", " 장식"

    type = models.CharField(max_length=20, choices=ComponentType.choices) # 매듭/술/장식 중 하나
    name = models.CharField(max_length=50) # 구성요소 이름
    color = models.CharField(max_length=20, null = True, blank = True, help_text="기본 대표 색상") # 색상 코드
    meaning = models.TextField(null=True, blank=True, help_text="전통 상징 의미-AI 추천/설명 근거 데이터") # 전통 상징 의미
    season = models.ForeignKey(
        Season,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="components",
        help_text="시즌 한정이면 연결, 상시 판매면 NULL",
    )
    # TODO: 프론트 답변 오면 추가 예정: image_url = models.CharField(max_length=255, null=True, blank=True)


    class Meta:
        db_table = 'component'

    def __str__(self):
        return f"[{self.get_type_display()}] {self.name}"

# 노리개
class Item(models.Model):
    # 사용자가 완성한 노리개

    # TODO: 추후 ERD 확인 한 번 더
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="items",
        help_text="팀원의 User 모델 참조. 비로그인 임시저장 시 NULL",
    )
    wish_keyword = models.CharField(max_length=100, help_text="입력한 바람/키워드") # 입력한 바람/키워드
    symbol_reason = models.TextField(null=True, blank=True, help_text="AI가 준 상징 추천 이유 (최초 생성 후 고정, 재갱신 안 됨)") # 상징 추천 이유 (AI)
    knot = models.ForeignKey(Component, on_delete=models.PROTECT, related_name="knot_items") # 매듭 참조
    tassel = models.ForeignKey(Component, on_delete=models.PROTECT, related_name="tassel_items") # 술 참조
    decoration = models.ForeignKey(Component, on_delete=models.PROTECT, related_name="decoration_items") # 장식 참조
    color = models.CharField(max_length=20, null=True, blank=True, help_text="사용자가 고른 전체 색상") # 선택한 색상
    image_url = models.CharField(max_length=255, null=True, blank=True, help_text="저장된 이미지 경로") # 저장 이미지 경로
    created_at = models.DateTimeField(auto_now_add=True) # 생성 일시

    class Meta:
        db_table = "item"

    def __str__(self):
        return f"Item #{self.pk} ({self.wish_keyword})"


# 상품
class Product(models.Model):
    # AI 상품 추천 / 상품 상세 / 관심상품 대상

    name = models.CharField(max_length=100) # 상품명
    price = models.IntegerField(help_text="가격(원)") # 상품 가격
    image_url = models.CharField(max_length=255, null=True, blank=True) # 상품 이미지 경로
    mcm_link = models.CharField(max_length=255, null=True, blank=True) # MCM 제품 이미지 경로
    # TODO: 관심상품/즐겨찾기는 팀원 User 모델 나온 뒤 별도 M:N 테이블(FavoriteProduct)로 추가 예정

    class Meta:
        db_table = "product"

    def __str__(self):
        return self.name
