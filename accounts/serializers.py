import re

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

# 영문 + 숫자 + 특수문자 포함 8자 이상 (SIGNUP_01 명세)
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>]).{8,}$"
)


class SignupSerializer(serializers.ModelSerializer):
    """회원가입 - 이메일/비번/비번확인/닉네임 + 약관동의"""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    agreed_terms = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "nickname", "password", "password_confirm", "agreed_terms"]

    def validate_email(self, value):
        # 이메일 중복 시 가입 불가
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("이미 가입된 이메일입니다.")
        return value.lower()

    def validate_nickname(self, value):
        if User.objects.filter(nickname=value).exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        return value

    def validate_password(self, value):
        # 영문/숫자/특수문자 포함 8자 이상
        if not PASSWORD_PATTERN.match(value):
            raise serializers.ValidationError(
                "비밀번호는 영문, 숫자, 특수문자를 포함해 8자 이상이어야 합니다."
            )
        return value

    def validate_agreed_terms(self, value):
        # 필수 약관 미동의 시 가입 불가
        if not value:
            raise serializers.ValidationError("필수 약관에 동의해야 합니다.")
        return value

    def validate(self, attrs):
        # 비밀번호 확인 불일치 시 가입 불가
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
    """프로필 조회/응답용"""

    provider = serializers.CharField(source="get_provider_display", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "nickname", "provider", "created_at"]

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

class NicknameUpdateSerializer(serializers.ModelSerializer):
    """MYPAGE_01(2) - 닉네임 수정"""

    class Meta:
        model = User
        fields = ["nickname"]

    def validate_nickname(self, value):
        if User.objects.filter(nickname=value).exclude(pk=self.instance.pk).exists():
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