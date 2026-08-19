import re

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

# 영문 + 숫자 + 특수문자 포함 8자 이상 (SIGNUP_01 명세)
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>]).{8,}$"
)


class SignupSerializer(serializers.ModelSerializer):
    """SIGNUP_01 - 이메일 회원가입. 성명/전화번호/이메일/비번 + 약관"""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    agreed_terms = serializers.BooleanField(write_only=True)  # 필수 약관 전체 동의 여부

    class Meta:
        model = User
        fields = ["email", "name", "phone", "password", "password_confirm", "agreed_terms"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("이미 가입된 이메일입니다.")
        return value.lower()

    def validate_password(self, value):
        if not PASSWORD_PATTERN.match(value):
            raise serializers.ValidationError(
                "비밀번호는 영문, 숫자, 특수문자를 포함해 8자 이상이어야 합니다."
            )
        return value

    def validate_agreed_terms(self, value):
        if not value:
            raise serializers.ValidationError("필수 약관에 동의해야 합니다.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "비밀번호가 일치하지 않습니다."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        validated_data.pop("agreed_terms")
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

class UserSerializer(serializers.ModelSerializer):
    provider = serializers.CharField(source="get_provider_display", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "name", "phone", "nickname", "provider", "created_at"]

# ─────────────────────────────────────────────
# RESERVATION_01 - 매장 방문 연계
# ─────────────────────────────────────────────
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from .models import Store, Reservation


class StoreSerializer(serializers.ModelSerializer):
    """RESERVATION_01(1) - 매장 선택. 운영 중인 매장만 노출"""

    class Meta:
        model = Store
        fields = ["id", "name", "address"]


class ReservationSerializer(serializers.ModelSerializer):
    """예약 응답용"""

    store_name = serializers.CharField(source="store.name", read_only=True)
    status = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Reservation
        fields = ["id", "store", "store_name", "reserved_at", "status", "created_at"]


class ReservationCreateSerializer(serializers.ModelSerializer):
    """
    RESERVATION_01(3) - 예약 완료.
    로그인: user 자동 연결 / 비로그인: guest_id·guest_password 필수
    """

    guest_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Reservation
        fields = ["store", "reserved_at", "guest_id", "guest_password"]

    def validate_store(self, value):
        # 운영 종료 매장은 예약 불가
        if not value.is_active:
            raise serializers.ValidationError("현재 예약할 수 없는 매장입니다.")
        return value

    def validate_reserved_at(self, value):
        # 지난 시간 예약 불가
        if value < timezone.now():
            raise serializers.ValidationError("지난 시간은 예약할 수 없습니다.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        # 비로그인 예약이면 guest 정보 필수
        if not request.user.is_authenticated:
            if not attrs.get("guest_id") or not attrs.get("guest_password"):
                raise serializers.ValidationError(
                    "비로그인 예약은 아이디와 비밀번호가 필요합니다."
                )
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        raw_password = validated_data.pop("guest_password", None)

        if request.user.is_authenticated:
            validated_data["user"] = request.user
        else:
            # 비회원 비밀번호는 해시 저장
            validated_data["guest_password"] = make_password(raw_password)

        return Reservation.objects.create(**validated_data)

# ─────────────────────────────────────────────
# MYPAGE_01 - 프로필/계정관리
# ─────────────────────────────────────────────

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """MYPAGE_01(2) - 프로필 수정. 닉네임/성명/전화번호/사진"""

    class Meta:
        model = User
        fields = ["nickname", "name", "phone", "profile_image"]   # 추가

    def validate_nickname(self, value):
        if value and User.objects.filter(nickname=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        return value

class WithdrawSerializer(serializers.Serializer):
    """MYPAGE_01(8) - 회원탈퇴. 비밀번호 일치 시에만 탈퇴 가능"""

    password = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        user = self.context["request"].user
        # 소셜 로그인 유저는 비번이 없으니(unusable password) 검증 스킵
        if user.has_usable_password():
            if not attrs.get("password") or not user.check_password(attrs["password"]):
                raise serializers.ValidationError({"password": "비밀번호가 일치하지 않습니다."})
        return attrs

# ─────────────────────────────────────────────
# MYPAGE_01(3) - 예약 내역
# ─────────────────────────────────────────────
class ReservationUpdateSerializer(serializers.ModelSerializer):
    """MYPAGE_01(3.2) - 예약 변경. 날짜/시간 수정"""

    class Meta:
        model = Reservation
        fields = ["reserved_at"]

    def validate_reserved_at(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("지난 시간으로는 변경할 수 없습니다.")
        return value


# ─────────────────────────────────────────────
# MYPAGE_01(4) - 저장 작품 / 노리개 디자인
# ─────────────────────────────────────────────
from maker.models import Item, Product


class ItemListSerializer(serializers.ModelSerializer):
    """MYPAGE_01(4.1) - 저장 작품 목록/상세. 구성 조합 포함"""

    knot_name = serializers.CharField(source="knot.name", read_only=True)
    tassel_name = serializers.CharField(source="tassel.name", read_only=True)
    decoration_name = serializers.CharField(source="decoration.name", read_only=True)

    class Meta:
        model = Item
        fields = [
            "id", "title", "description", "wish_keyword", "symbol_reason",
            "knot", "knot_name", "tassel", "tassel_name",
            "decoration", "decoration_name",
            "color", "image_url", "created_at",
        ]


# ─────────────────────────────────────────────
# MYPAGE_01(5) - 소유 등록
# ─────────────────────────────────────────────
from .models import Ownership


class OwnershipSerializer(serializers.ModelSerializer):
    """MYPAGE_01(5.1) - 소유 등록 응답용(소유권 증명서)"""

    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Ownership
        fields = [
            "id", "product", "product_name", "serial_no",
            "has_production_right", "created_at",
        ]


class OwnershipCreateSerializer(serializers.ModelSerializer):
    """MYPAGE_01(5.1) - 소유 등록. 시리얼/주문번호로 등록"""

    class Meta:
        model = Ownership
        fields = ["product", "serial_no"]

    def validate_serial_no(self, value):
        # 이미 등록된 시리얼이면 불가 (unique지만 친절한 메시지)
        if Ownership.objects.filter(serial_no=value).exists():
            raise serializers.ValidationError("이미 등록된 시리얼/주문번호입니다.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        return Ownership.objects.create(user=user, **validated_data)


# ─────────────────────────────────────────────
# MYPAGE_01(6) - 관심상품(위시리스트)
# ─────────────────────────────────────────────
from .models import Wishlist


class WishlistSerializer(serializers.ModelSerializer):
    """MYPAGE_01(6) - 관심 등록 노리개 조합 조회"""

    knot_name = serializers.CharField(source="knot.name", read_only=True)
    tassel_name = serializers.CharField(source="tassel.name", read_only=True)
    decoration_name = serializers.CharField(source="decoration.name", read_only=True)

    class Meta:
        model = Wishlist
        fields = [
            "id", "knot", "knot_name", "tassel", "tassel_name",
            "decoration", "decoration_name", "created_at",
        ]


class WishlistCreateSerializer(serializers.ModelSerializer):
    """MYPAGE_01(6) - 관심 조합 등록"""

    class Meta:
        model = Wishlist
        fields = ["knot", "tassel", "decoration"]

    def validate(self, attrs):
        user = self.context["request"].user
        # 같은 조합 중복 등록 방지
        if Wishlist.objects.filter(
                user=user,
                knot=attrs["knot"],
                tassel=attrs["tassel"],
                decoration=attrs["decoration"],
        ).exists():
            raise serializers.ValidationError("이미 관심 등록한 조합입니다.")
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return Wishlist.objects.create(user=user, **validated_data)


class PasswordChangeSerializer(serializers.Serializer):
    """MYPAGE - 비밀번호 변경. 이메일 가입자만"""

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        if not PASSWORD_PATTERN.match(value):
            raise serializers.ValidationError(
                "비밀번호는 영문, 숫자, 특수문자를 포함해 8자 이상이어야 합니다."
            )
        return value

    def validate(self, attrs):
        user = self.context["request"].user

        # 소셜 유저는 비번 변경 불가
        if user.provider != User.Provider.EMAIL:
            raise serializers.ValidationError("소셜 계정은 비밀번호를 변경할 수 없습니다.")

        # 현재 비번 확인
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "현재 비밀번호가 일치하지 않습니다."}
            )

        # 새 비번 일치 확인
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "새 비밀번호가 일치하지 않습니다."}
            )

        # 현재와 같은 비번이면 막기
        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "현재 비밀번호와 다른 비밀번호를 사용해주세요."}
            )
        return attrs

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user