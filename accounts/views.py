import requests
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import SignupSerializer, UserSerializer

User = get_user_model()


def issue_tokens(user):
    """JWT access/refresh 발급"""
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class SignupView(APIView):
    """SIGNUP_01 - 회원가입"""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # 회원가입 성공 시에만 홈 이동 → 프론트가 판단하도록 토큰까지 응답
        return Response(
            {"user": UserSerializer(user).data, "token": issue_tokens(user)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """LOGIN_01 - 이메일 로그인. 미일치 시 메시지 출력"""

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").lower()
        password = request.data.get("password", "")

        user = User.objects.filter(email=email).first()
        # 계정 존재 여부 노출 방지 위해 통합 메시지
        if user is None or not user.check_password(password):
            return Response(
                {"detail": "이메일 또는 비밀번호가 일치하지 않습니다."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {"user": UserSerializer(user).data, "token": issue_tokens(user)},
            status=status.HTTP_200_OK,
        )


class SocialLoginView(APIView):
    """
    LOGIN_01 - 소셜 로그인 (카카오/네이버)
    프론트에서 받은 access_token을 검증해 로그인/자동가입.
    URL: /auth/social/<provider>/   body: { "access_token": "..." }
    """

    permission_classes = [AllowAny]

    def post(self, request, provider):
        access_token = request.data.get("access_token")
        if not access_token:
            return Response(
                {"detail": "access_token이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if provider == User.Provider.KAKAO:
            profile = self._get_kakao_profile(access_token)
        elif provider == User.Provider.NAVER:
            profile = self._get_naver_profile(access_token)
        else:
            return Response(
                {"detail": "지원하지 않는 소셜 로그인입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if profile is None:
            return Response(
                {"detail": "소셜 인증에 실패했습니다."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user, created = self._get_or_create_social_user(provider, profile)
        return Response(
            {
                "user": UserSerializer(user).data,
                "token": issue_tokens(user),
                "created": created,  # 신규 가입 여부 (온보딩 분기용)
            },
            status=status.HTTP_200_OK,
        )

    # --- provider별 프로필 조회 ---

    def _get_kakao_profile(self, access_token):
        resp = requests.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        account = data.get("kakao_account", {})
        return {
            "social_id": str(data["id"]),
            "email": account.get("email"),
            "nickname": account.get("profile", {}).get("nickname"),
        }

    def _get_naver_profile(self, access_token):
        resp = requests.get(
            "https://openapi.naver.com/v1/nid/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json().get("response", {})
        if not data:
            return None
        return {
            "social_id": str(data["id"]),
            "email": data.get("email"),
            "nickname": data.get("nickname"),
        }

    # --- 로그인 or 자동가입 ---

    def _get_or_create_social_user(self, provider, profile):
        user = User.objects.filter(
            provider=provider, social_id=profile["social_id"]
        ).first()
        if user:
            return user, False

        base = profile.get("nickname") or f"{provider}_user"
        nickname = self._unique_nickname(base)
        user = User.objects.create_user(
            email=profile.get("email") or f"{profile['social_id']}@{provider}.social",
            nickname=nickname,
            provider=provider,
            social_id=profile["social_id"],
            password=None,  # 소셜 유저는 unusable password
        )
        return user, True

    def _unique_nickname(self, base):
        nickname, idx = base, 1
        while User.objects.filter(nickname=nickname).exists():
            nickname = f"{base}_{idx}"
            idx += 1
        return nickname