from django.db import models

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)


class UserManager(BaseUserManager):
    """이메일을 식별자로 사용하는 커스텀 매니저"""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()  # 소셜 가입 유저는 비번 없음
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


# 회원
class User(AbstractBaseUser, PermissionsMixin):
    class Provider(models.TextChoices):
        EMAIL = "email", "이메일"
        KAKAO = "kakao", "카카오"
        NAVER = "naver", "네이버"

    email = models.EmailField(unique=True, help_text="UNIQUE, 로그인 아이디로 사용")
    nickname = models.CharField(max_length=30, unique=True, help_text="UNIQUE")
    provider = models.CharField(
        max_length=10,
        choices=Provider.choices,
        default=Provider.EMAIL,
        help_text="email / kakao / naver",
    )
    social_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="소셜 로그인 시 발급되는 식별자",
    )
    is_active = models.BooleanField(default=True, help_text="탈퇴 시 false 처리")
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nickname"]

    class Meta:
        db_table = "user"
        constraints = [
            # 같은 소셜 계정 중복 가입 방지
            models.UniqueConstraint(
                fields=["provider", "social_id"],
                name="unique_social_account",
                condition=models.Q(social_id__isnull=False),
            )
        ]

    def __str__(self):
        return f"{self.email} ({self.get_provider_display()})"


# 매장
class Store(models.Model):
    # 방문 예약 가능한 오프라인 매장
    name = models.CharField(max_length=100)  # 매장명
    address = models.CharField(max_length=255)  # 주소
    is_active = models.BooleanField(
        default=True, help_text="false면 예약 목록에서 제외"
    )  # 운영 여부

    class Meta:
        db_table = "store"

    def __str__(self):
        return self.name


# 예약
class Reservation(models.Model):
    # 매장 방문 예약. 로그인/비로그인 모두 가능
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "예약완료"
        CHANGED = "changed", "변경됨"
        CANCELED = "canceled", "취소됨"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reservations",
        help_text="USER 참조. 비로그인 예약 시 NULL",
    )  # 회원 참조
    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="reservations",
    )  # 매장 참조
    reserved_at = models.DateTimeField(help_text="예약 가능 날짜·시간만")  # 예약 날짜/시간
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED,
        help_text="confirmed / changed / canceled",
    )  # 예약 상태
    guest_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="비로그인 예약 시 필수",
    )  # 비회원 확인용 아이디
    guest_password = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="비로그인 예약 시 필수, 해시 저장",
    )  # 비회원 확인용 비번
    created_at = models.DateTimeField(auto_now_add=True)  # 생성 일시

    class Meta:
        db_table = "reservation"
        constraints = [
            # 같은 매장 같은 시간 중복 예약 제한
            models.UniqueConstraint(
                fields=["store", "reserved_at"],
                name="unique_store_time",
            )
        ]

    def __str__(self):
        who = self.user.nickname if self.user else (self.guest_id or "guest")
        return f"[{self.get_status_display()}] {self.store.name} - {who}"


# 위시리스트
class Wishlist(models.Model):
    # 관심 등록 노리개 조합 (매듭+장식+술)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlists",
    )  # 회원 참조

    knot = models.ForeignKey(
        "maker.Component",
        on_delete=models.CASCADE,
        related_name="knot_wishlists",
    )  # 매듭 참조
    tassel = models.ForeignKey(
        "maker.Component",
        on_delete=models.CASCADE,
        related_name="tassel_wishlists",
    )  # 술 참조
    decoration = models.ForeignKey(
        "maker.Component",
        on_delete=models.CASCADE,
        related_name="decoration_wishlists",
    )  # 장식 참조

    created_at = models.DateTimeField(auto_now_add=True)  # 등록 일시

    class Meta:
        db_table = "wishlist"
        constraints = [
            # 같은 상품 중복 관심등록 방지
            models.UniqueConstraint(
                fields=["user", "knot", "tassel", "decoration"],
                name="unique_user_product_wish",
            )
        ]

    def __str__(self):
        return f"{self.user.nickname} ♡ {self.knot.name}+{self.tassel.name}+{self.decoration.name}"


# 소유 등록
class Ownership(models.Model):
    # 구매한 참/노리개를 시리얼/주문번호로 등록
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ownerships",
    )  # 회원 참조
    product = models.ForeignKey(
        "maker.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ownerships",
    )  # 상품 참조 (참/노리개)
    serial_no = models.CharField(
        max_length=100,
        unique=True,
        help_text="등록 키, UNIQUE",
    )  # 시리얼/주문번호
    has_production_right = models.BooleanField(
        default=False,
        help_text="일정 금액 이상 구매/협업 시 true",
    )  # 제작권 지급 여부
    created_at = models.DateTimeField(auto_now_add=True)  # 등록 일시

    class Meta:
        db_table = "ownership"

    def __str__(self):
        return f"{self.serial_no} ({self.user.nickname})"
