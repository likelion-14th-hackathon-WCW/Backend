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